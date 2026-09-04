#!/usr/bin/env python3
"""聊天记录预处理工具（零第三方依赖，平台无关）。

用法：
  python3 chat_parser.py --file 聊天.json [--sample 12] [--output 报告.md]

输入格式：
- JSON：任意聊天导出。自动探测常见字段名——
        时间：t / time / timestamp / date / datetime（支持多种格式与 epoch）
        内容：content / text / message / msg
        发送者：sender / from / user / name / talker / speaker / role
        消息数组：messages / msgs / items / list / data（顶层为数组亦可）
        「我 / 对方」识别：顶层 me|self|owner|my_name 等标记 >
        is_me 布尔字段 > wechat-parse 元数据（wxid/talker）。
        均无法识别时按说话人分列统计，不强行锚定。
- TXT：每行聊天导出，支持 "[2024-01-01 12:00:00] 名字: 内容" 等常见格式（尽力解析）
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime

GAP_NEW_SESSION = 4 * 3600          # 间隔超过 4 小时视为新会话
REPLY_WINDOW = 30 * 60              # 30 分钟内的说话人切换才算回复

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F0FF\U00002600-\U000026FF\U0001F900-\U0001F9FF]"
)

# 语气词/风格词表可经 --patterns JSON 覆盖（适配其他语言与平台）
DEFAULT_PATTERNS = {
    "tone_words": ["哈哈哈", "哈哈", "笑死", "绝了", "无语", "好的", "嗯嗯", "哦哦",
                   "666", "拜拜", "晚安", "早安", "宝贝", "亲爱", "想你", "爱你", "么么"],
}

TIME_KEYS = ("t", "time", "timestamp", "date", "datetime", "send_time", "created_at")
CONTENT_KEYS = ("content", "text", "message", "msg", "body")
SENDER_KEYS = ("sender", "from", "user", "name", "talker", "speaker", "author")
MSG_LIST_KEYS = ("messages", "msgs", "items", "list", "data", "records")
TYPE_KEYS = ("type", "msg_type", "message_type", "kind")
ME_KEYS = ("me", "self", "owner", "my_name", "my_wxid", "self_wxid", "my", "self_name")

TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S", "%Y年%m月%d日 %H:%M:%S", "%Y年%m月%d日 %H:%M",
)


def _parse_dt(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if v > 1e12:
            v = v / 1000
        try:
            return datetime.fromtimestamp(v)
        except (OSError, ValueError, OverflowError):
            return None
    s = str(v).strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _first(m, keys):
    for k in keys:
        if m.get(k) not in (None, ""):
            return m[k]
    return None


def load_patterns(path):
    """加载 --patterns JSON，浅合并覆盖默认词表。"""
    patterns = {k: list(v) for k, v in DEFAULT_PATTERNS.items()}
    if not path:
        return patterns
    with open(path, encoding="utf-8") as f:
        for k, v in json.load(f).items():
            if isinstance(v, list):
                patterns[k] = [str(x) for x in v]
    return patterns


# ---------------------------------------------------------------- 聊天解析

def parse_chat(path):
    """返回 (msgs, meta)。msgs: [{dt, sender, type, content}] 按时间升序。"""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return parse_chat_json(text)
        except json.JSONDecodeError:
            pass  # 以 [ 开头的纯文本聊天导出，回落到文本解析
    return parse_plain_text(text)


def parse_chat_json(text):
    """解析任意平台聊天导出 JSON。字段名自动探测，wechat-parse 导出完全兼容。"""
    data = json.loads(text)
    if isinstance(data, list):
        raw_msgs, meta_src = data, {}
    else:
        raw_msgs = None
        for k in MSG_LIST_KEYS:
            if isinstance(data.get(k), list):
                raw_msgs = data[k]
                break
        if raw_msgs is None:
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    raw_msgs = v
                    break
        meta_src = data if isinstance(data, dict) else {}
    if raw_msgs is None:
        raise SystemExit(
            "JSON 中未找到消息数组（支持 messages/msgs/items/list/data 键，或顶层数组）"
        )

    msgs = []
    for m in raw_msgs:
        if not isinstance(m, dict):
            continue
        dt = _parse_dt(_first(m, TIME_KEYS))
        if dt is None:
            continue
        msgs.append({
            "dt": dt,
            "sender": str(_first(m, SENDER_KEYS) or "未知").strip(),
            "type": str(_first(m, TYPE_KEYS) or "文本"),
            "content": str(_first(m, CONTENT_KEYS) or "").strip(),
            "_is_me": m.get("is_me", m.get("is_self", m.get("from_me"))),
        })
    msgs.sort(key=lambda x: x["dt"])
    senders = [s for s, _ in Counter(m["sender"] for m in msgs).most_common()]

    # 「我 / 对方」识别：显式标记 > is_me 字段 > wechat-parse 元数据；都不行则不锚定
    me, peer = None, None
    for k in ME_KEYS:
        v = meta_src.get(k)
        if isinstance(v, str) and v:
            me = v
            break
    if me is None:
        me = next((m["sender"] for m in msgs if m.pop("_is_me", None) is True), None)
    else:
        for m in msgs:
            m.pop("_is_me", None)

    wxid = meta_src.get("wxid")
    if me:
        peer = next((s for s in senders if s != me), None)
    elif wxid:
        # wechat-parse：wxid 即对方，消息里 sender 为 wxid；匹配上的显示为对方昵称
        peer = meta_src.get("talker") or wxid
        for m in msgs:
            if m["sender"] == wxid:
                m["sender"] = peer
    if peer is None:
        peer = None  # 不锚定：报告按说话人分列，由使用者代入

    return msgs, {"peer": peer, "me": me}


def parse_plain_text(text):
    """尽力解析常见纯文本聊天导出格式。"""
    line_re = re.compile(
        r"^\[?(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*([^:：]{1,32})[:：]\s?(.*)$"
    )
    msgs = []
    for line in text.splitlines():
        m = line_re.match(line.strip())
        if not m:
            continue
        date_s, time_s, sender, content = m.groups()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(f"{date_s.replace('/', '-')} {time_s}", fmt)
                break
            except ValueError:
                dt = None
        if dt is None:
            continue
        msgs.append({"dt": dt, "sender": sender.strip(), "type": "文本", "content": content.strip()})
    msgs.sort(key=lambda x: x["dt"])
    senders = Counter(m["sender"] for m in msgs)
    peer = senders.most_common(1)[0][0] if senders else "对方"
    return msgs, {"peer": peer, "me_hint": "另一个说话人"}


# ---------------------------------------------------------------- 统计分析

def _clean_display(content, limit=90):
    """截断并标记乱码内容（微信引用消息中常见不可读字节）。"""
    printable = sum(1 for ch in content if ch.isprintable())
    if content and printable / max(1, len(content)) < 0.6:
        return "<不可读内容（引用卡片/特殊消息）>"
    return content.replace("|", "\\|").replace("\n", " ")[:limit]


def analyze_chat(msgs, meta, sample_n, patterns=None):
    patterns = patterns or DEFAULT_PATTERNS
    out = []
    n = len(msgs)
    if n == 0:
        return "未解析到任何消息。", []
    span = f"{msgs[0]['dt']:%Y-%m-%d %H:%M} → {msgs[-1]['dt']:%Y-%m-%d %H:%M}"
    senders = Counter(m["sender"] for m in msgs)
    chars = Counter()
    for m in msgs:
        chars[m["sender"]] += len(m["content"])

    peer = meta.get("peer")
    out.append(f"## 聊天总览\n")
    out.append(f"- 消息总数：{n} 条，时间跨度：{span}")
    if peer is None:
        out.append("- 注意：未能自动识别「我 / 对方」（缺少 me/self 标记或 wechat-parse 元数据），"
                   "以下统计按说话人分列，请自行代入双方身份")
    out.append(f"- 说话人分布：" + "；".join(
        f"**{s}** {c} 条（{c / n:.0%}，{chars[s]} 字）" for s, c in senders.most_common(6)))

    type_dist = Counter(m["type"] for m in msgs)
    out.append(f"- 消息类型：" + "；".join(f"{t} {c}" for t, c in type_dist.most_common(8)))

    # 小时分布
    hour_all = Counter(m["dt"].hour for m in msgs)
    late_all = sum(v for h, v in hour_all.items() if h < 6)
    late_line = f"- 深夜消息（0-6 点）：全部 {late_all} 条"
    if peer:
        hour_peer = Counter(m["dt"].hour for m in msgs if m["sender"] == peer)
        late_peer = sum(v for h, v in hour_peer.items() if h < 6)
        late_line += f"；{peer} {late_peer} 条" + (
            f"（占其消息 {late_peer / max(1, senders[peer]):.0%}）" if senders[peer] else "")
    else:
        for s, _ in senders.most_common(2):
            hour_s = Counter(m["dt"].hour for m in msgs if m["sender"] == s)
            late_s = sum(v for h, v in hour_s.items() if h < 6)
            late_line += f"；{s} {late_s} 条（占其消息 {late_s / max(1, senders[s]):.0%}）"
    out.append(late_line)

    # 会话发起
    sessions, cur = [], [msgs[0]]
    for prev, m in zip(msgs, msgs[1:]):
        if (m["dt"] - prev["dt"]).total_seconds() > GAP_NEW_SESSION:
            sessions.append(cur)
            cur = [m]
        else:
            cur.append(m)
    sessions.append(cur)
    initiators = Counter(s[0]["sender"] for s in sessions if len(s) >= 3)
    n_long = max(1, len([s for s in sessions if len(s) >= 3]))
    out.append(f"- 长会话（≥3 条）{n_long} 个，发起者：" +
               "；".join(f"{s} {c} 次（{c / n_long:.0%}）"
                         for s, c in initiators.most_common(4))
               + "　← 主动发起是好感的重要信号")

    # 回复延迟
    delays = {s: [] for s in senders}
    for prev, m in zip(msgs, msgs[1:]):
        if prev["sender"] != m["sender"]:
            d = (m["dt"] - prev["dt"]).total_seconds()
            if 0 < d <= REPLY_WINDOW:
                delays[m["sender"]].append(d)
    out.append(f"- 回复速度（≤30 分钟内的接话，中位数）：")
    for s, c in senders.most_common(4):
        ds = sorted(delays[s])
        if ds:
            med = ds[len(ds) // 2]
            quick = sum(1 for d in ds if d <= 60) / len(ds)
            out.append(f"  - {s}：{med / 60:.1f} 分钟；1 分钟内秒回占比 {quick:.0%}")
        else:
            out.append(f"  - {s}：样本不足")

    # 表情与语气词
    emoji = Counter()
    tones = Counter()
    for m in msgs:
        emoji.update(EMOJI_RE.findall(m["content"]))
        for tw in patterns.get("tone_words", []):
            if tw in m["content"]:
                tones[tw] += m["content"].count(tw)
    if emoji:
        out.append(f"- 常用表情：" + "；".join(f"{e}×{c}" for e, c in emoji.most_common(10)))
    if tones:
        out.append(f"- 高频语气词：" + "；".join(f"「{w}」×{c}" for w, c in tones.most_common(8)))

    # 高频 n-gram（口头禅候选）
    per_sender_gram = {}
    for s in [x[0] for x in senders.most_common(2)]:
        grams = Counter()
        for m in msgs:
            if m["sender"] != s or m["type"] != "文本":
                continue
            clean = re.sub(r"[^\u4e00-\u9fffA-Za-z]", " ", m["content"])
            for w in clean.split():
                for size in (2, 3):
                    for i in range(len(w) - size + 1):
                        grams[w[i:i + size]] += 1
        # 过滤被更长 gram 覆盖的
        top = [g for g, _ in grams.most_common(60)]
        filtered = [g for g in top if not any(g != g2 and g in g2 and grams[g2] >= grams[g] * 0.8 for g2 in top)]
        per_sender_gram[s] = filtered[:12]
    for s, gs in per_sender_gram.items():
        if gs:
            out.append(f"- {s} 高频用词（口头禅候选）：" + "；".join(f"「{g}」" for g in gs))

    # 对话采样
    samples = _sample(msgs, sample_n)
    out.append(f"\n## 代表性对话采样（{len(samples)} 段）\n")
    out.append("> 以下是均匀抽样的对话片段，用于感受双方真实的说话风格。深度分析时优先读这些片段。\n")
    for i, seg in enumerate(samples, 1):
        out.append(f"### 片段 {i}（{seg[0]['dt']:%Y-%m-%d %H:%M} 起）\n")
        for m in seg:
            c = _clean_display(m["content"]).replace("\n", " ")
            out.append(f"- [{m['dt']:%m-%d %H:%M}] {m['sender']}：{c or f'<{m["type"]}>'}")
        out.append("")
    return "\n".join(out), samples


def _sample(msgs, n, window=18):
    """均匀抽样 n 段对话。优先选文本密集的段落。"""
    if not msgs:
        return []
    sessions, cur = [], [msgs[0]]
    for prev, m in zip(msgs, msgs[1:]):
        if (m["dt"] - prev["dt"]).total_seconds() > GAP_NEW_SESSION:
            sessions.append(cur)
            cur = [m]
        else:
            cur.append(m)
    sessions.append(cur)
    rich = [s for s in sessions if len(s) >= window]
    if not rich:
        rich = [s for s in sessions if len(s) >= 5] or sessions
    rich.sort(key=len, reverse=True)
    picked = []
    if len(rich) <= n:
        picked = rich
    else:
        step = len(rich) / n
        picked = [rich[int(i * step)] for i in range(n)]
    segs = []
    for s in picked:
        start = max(0, (len(s) - window) // 2)
        seg = s[start:start + window]
        # 补全到时间上下文连贯
        segs.append(seg)
    segs.sort(key=lambda seg: seg[0]["dt"])
    return segs


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="聊天记录预处理（平台无关）")
    ap.add_argument("--file", help="聊天记录文件（任意平台导出的 JSON 或 txt）")
    ap.add_argument("--patterns", help="词表覆盖 JSON（tone_words 等），适配其他语言/平台")
    ap.add_argument("--sample", type=int, default=12, help="对话采样段数（默认 12）")
    ap.add_argument("--output", help="报告输出路径（默认 stdout）")
    args = ap.parse_args()

    if not args.file:
        ap.error("需要提供 --file")

    patterns = load_patterns(args.patterns)
    msgs, meta = parse_chat(args.file)
    report, _ = analyze_chat(msgs, meta, args.sample, patterns)
    title = meta.get("peer") or "（未识别双方身份）"
    result = f"# 聊天记录分析报告：{title}\n\n{report}"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"报告已写入 {args.output}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(result)


if __name__ == "__main__":
    main()
