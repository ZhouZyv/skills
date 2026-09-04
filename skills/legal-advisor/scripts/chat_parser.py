#!/usr/bin/env python3
"""聊天记录与交易账单预处理工具（零第三方依赖）。

用法：
  # 聊天记录分析（wechat-parse 导出的 JSON，或纯文本导出）
  python3 chat_parser.py --file 聊天.json [--sample 12] [--output 报告.md]

  # 微信支付账单核对（xlsx 或 csv）
  python3 chat_parser.py --bill 账单.xlsx [--output 报告.md]

  # 两者同时分析
  python3 chat_parser.py --file 聊天.json --bill 账单.xlsx

输入格式：
- JSON：wechat-parse 导出格式 {talker, wxid, messages:[{t, sender, type, content}]}
        wxid 字段即对方的 wxid，脚本据此自动区分「对方」和「我」
- TXT：每行聊天导出，支持 "[2024-01-01 12:00:00] 名字: 内容" 等常见格式（尽力解析）
- 账单：微信支付账单导出的 csv，或整理过的 xlsx（列含 交易时间/交易类型/收/支/金额）
"""

import argparse
import csv
import json
import math
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

GAP_NEW_SESSION = 4 * 3600          # 间隔超过 4 小时视为新会话
REPLY_WINDOW = 30 * 60              # 30 分钟内的说话人切换才算回复
LOVE_AMOUNTS = {520, 1314, 5200, 13140, 999, 888, 666, 1666, 1888}

MONEY_STRONG = re.compile(
    r"转账|红包|借款|借我|借点|还钱|还我|还你|还我钱|欠|代付|帮我付|垫付|[¥￥]"
)
MONEY_AMOUNT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:元|块钱|块)(?:钱)?|[¥￥]\s*(\d+(?:\.\d+)?)"
)
SHOP_LINK = re.compile(r"淘宝|天猫|京东|拼多多|m\.tb\.cn|item\.jd|yangkeduo", re.I)

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F0FF\U00002600-\U000026FF\U0001F900-\U0001F9FF]"
)
TONE_WORDS = ["哈哈哈", "哈哈", "笑死", "绝了", "无语", "好的", "嗯嗯", "哦哦",
              "666", "拜拜", "晚安", "早安", "宝贝", "亲爱", "想你", "爱你", "么么"]


# ---------------------------------------------------------------- 聊天解析

def parse_chat(path):
    """返回 (msgs, meta)。msgs: [{dt, sender, type, content}] 按时间升序。"""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return parse_wechat_json(text)
    return parse_plain_text(text)


def parse_wechat_json(text):
    data = json.loads(text)
    peer_wxid = data.get("wxid", "")
    peer_name = data.get("talker", peer_wxid or "对方")
    msgs = []
    for m in data.get("messages", []):
        try:
            dt = datetime.strptime(m["t"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            continue
        sender_wxid = m.get("sender", "")
        sender = peer_name if sender_wxid == peer_wxid and peer_wxid else (sender_wxid or "未知")
        msgs.append({
            "dt": dt,
            "sender": sender,
            "type": m.get("type", "文本"),
            "content": (m.get("content") or "").strip(),
        })
    msgs.sort(key=lambda x: x["dt"])
    meta = {"peer": peer_name, "me_hint": "另一个说话人"}
    return msgs, meta


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


# ---------------------------------------------------------------- 账单解析

def _excel_serial_to_dt(v):
    try:
        serial = float(v)
        return datetime(1899, 12, 30) + timedelta(days=serial)
    except (TypeError, ValueError):
        return None


def read_xlsx_rows(path):
    """纯标准库读取 xlsx 第一个 sheet，返回 [[cell,...],...]（字符串值）。"""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheet_name = next(n for n in z.namelist() if re.match(r"xl/worksheets/sheet1?\.xml$", n))
        root = ET.fromstring(z.read(sheet_name))
        rows = {}
        for c in root.iter(f"{{{ns['m']}}}c"):
            ref = c.get("r", "")
            m = re.match(r"([A-Z]+)(\d+)", ref)
            if not m:
                continue
            col_s, row_s = m.groups()
            col = 0
            for ch in col_s:
                col = col * 26 + (ord(ch) - 64)
            t = c.get("t")
            v_el = c.find("m:v", ns)
            if t == "s" and v_el is not None:
                val = shared[int(v_el.text)]
            elif t == "inlineStr":
                is_el = c.find("m:is", ns)
                val = "".join(x.text or "" for x in is_el.iter(f"{{{ns['m']}}}t")) if is_el is not None else ""
            else:
                val = (v_el.text if v_el is not None else "")
            rows.setdefault(int(row_s), {})[col] = val
    return [[rows[r].get(c, "") for c in range(1, max(rows[r]) + 1)] for r in sorted(rows)]


def read_bill(path):
    """读取微信支付账单（csv 或 xlsx），返回 (header, rows)。自动探测表头行与编码。"""
    lower = path.lower()
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        all_rows = read_xlsx_rows(path)
    elif lower.endswith(".csv") or lower.endswith(".txt"):
        all_rows = None
        raw = open(path, "rb").read()
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="replace")
        lines = list(csv.reader(text.splitlines()))
        if lines and any("微信支付账单" in c for c in lines[0]):
            lines = lines[16:]  # 微信官方 csv 前有固定说明头，表头通常在第 17 行
        all_rows = lines
    else:
        raise SystemExit(f"不支持的账单格式：{path}（支持 xlsx / csv）")

    header_i = next((i for i, r in enumerate(all_rows)
                     if any("交易时间" in str(c) for c in r)), None)
    if header_i is None:
        raise SystemExit("账单中未找到表头行（需包含「交易时间」列）")
    header = [str(c).strip() for c in all_rows[header_i]]
    rows = []
    for r in all_rows[header_i + 1:]:
        if not any(str(c).strip() for c in r):
            continue
        rows.append([str(c).strip() for c in r])
    return header, rows


# ---------------------------------------------------------------- 统计分析

def money_scan(msgs):
    hits = []
    for m in msgs:
        c = m["content"]
        if not c:
            continue
        tag = None
        if MONEY_STRONG.search(c):
            tag = "强词"
        amounts = [a for pair in MONEY_AMOUNT.findall(c) for a in pair if a]
        if amounts:
            tag = (tag + "+金额") if tag else "金额"
        if SHOP_LINK.search(c):
            tag = (tag + "+网购链接") if tag else "网购链接"
        if tag:
            hits.append({**m, "tag": tag, "amounts": amounts})
    return hits


def _clean_display(content, limit=90):
    """截断并标记乱码内容（微信引用消息中常见不可读字节）。"""
    printable = sum(1 for ch in content if ch.isprintable())
    if content and printable / max(1, len(content)) < 0.6:
        return "<不可读内容（引用卡片/特殊消息）>"
    return content.replace("|", "\\|").replace("\n", " ")[:limit]


def _fmt_money_hits(hits, limit=60):
    lines = ["| 时间 | 说话人 | 类型 | 内容 |", "|---|---|---|---|"]
    shown = 0
    for h in hits:
        if shown >= limit:
            lines.append(f"| … 共 {len(hits)} 条，仅展示前 {limit} 条 | | | |")
            break
        lines.append(f"| {h['dt']:%Y-%m-%d %H:%M} | {h['sender']} | {h['tag']} | {_clean_display(h['content'])} |")
        shown += 1
    return "\n".join(lines)


def _summarize_amounts(hits):
    nums = []
    for h in hits:
        for a in h["amounts"]:
            try:
                v = float(a)
                if 0 < v < 1_000_000:
                    nums.append(v)
            except ValueError:
                pass
    if not nums:
        return "未从文本中识别到具体金额（转账截图等在图片消息中，需结合账单核对）"
    love = [v for v in nums if v in LOVE_AMOUNTS]
    return (f"文本中出现金额 {len(nums)} 次，合计约 {sum(nums):.0f} 元；"
            f"其中示爱数字（520/1314 等）出现 {len(love)} 次。"
            f"注意：这只是聊天文本里提到的金额，实际转账以支付账单为准。")


def analyze_chat(msgs, meta, sample_n):
    out = []
    n = len(msgs)
    if n == 0:
        return "未解析到任何消息。", []
    span = f"{msgs[0]['dt']:%Y-%m-%d %H:%M} → {msgs[-1]['dt']:%Y-%m-%d %H:%M}"
    senders = Counter(m["sender"] for m in msgs)
    chars = Counter()
    for m in msgs:
        chars[m["sender"]] += len(m["content"])

    peer = meta["peer"]
    out.append(f"## 聊天总览\n")
    out.append(f"- 消息总数：{n} 条，时间跨度：{span}")
    out.append(f"- 说话人分布：" + "；".join(
        f"**{s}** {c} 条（{c / n:.0%}，{chars[s]} 字）" for s, c in senders.most_common(6)))

    type_dist = Counter(m["type"] for m in msgs)
    out.append(f"- 消息类型：" + "；".join(f"{t} {c}" for t, c in type_dist.most_common(8)))

    # 小时分布
    hour_all = Counter(m["dt"].hour for m in msgs)
    hour_peer = Counter(m["dt"].hour for m in msgs if m["sender"] == peer)
    late_all = sum(v for h, v in hour_all.items() if h < 6)
    late_peer = sum(v for h, v in hour_peer.items() if h < 6)
    out.append(f"- 深夜消息（0-6 点）：全部 {late_all} 条；{peer} {late_peer} 条"
               + (f"（占其消息 {late_peer / max(1, senders[peer]):.0%}）" if senders[peer] else ""))

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
        for tw in TONE_WORDS:
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

    # 金钱扫描
    hits = money_scan(msgs)
    out.append(f"\n## 金钱语境扫描（{len(hits)} 条命中）\n")
    out.append(_summarize_amounts(hits))
    out.append("")
    if hits:
        out.append(_fmt_money_hits(hits))

    # 对话采样
    samples = _sample(msgs, sample_n)
    out.append(f"\n## 代表性对话采样（{len(samples)} 段）\n")
    out.append("> 以下是均匀抽样的对话片段，用于感受双方真实的说话风格。深度分析时优先读这些片段。\n")
    for i, seg in enumerate(samples, 1):
        out.append(f"### 片段 {i}（{seg[0]['dt']:%Y-%m-%d %H:%M} 起）\n")
        for m in seg:
            c = m["content"].replace("\n", " ")
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


# ---------------------------------------------------------------- 账单汇总

def analyze_bill(header, rows):
    idx = {h.strip(): i for i, h in enumerate(header)}
    col_time = next((k for k in idx if k.startswith("交易时间")), None)
    col_type = next((k for k in idx if k.startswith("交易类型")), None)
    col_counterparty = next((k for k in idx if "交易对方" in k), None)
    col_goods = next((k for k in idx if "商品" in k), None)
    col_dir = next((k for k in idx if "收/支" in k or k == "收支"), None)
    col_amount = next((k for k in idx if "金额" in k), None)
    col_status = next((k for k in idx if "当前状态" in k), None)
    if col_time is None or col_amount is None:
        raise SystemExit(f"账单缺少「交易时间」或「金额」列。表头：{header}")

    recs = []
    for r in rows:
        time_s = r[idx[col_time]] if idx[col_time] < len(r) else ""
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(time_s, fmt)
                break
            except (ValueError, TypeError):
                continue
        if dt is None:
            dt = _excel_serial_to_dt(time_s)
        if dt is None:
            continue
        amount_s = r[idx[col_amount]] if idx[col_amount] < len(r) else "0"
        try:
            amount = float(re.sub(r"[^\d.\-]", "", amount_s) or 0)
        except ValueError:
            amount = 0.0
        direction = r[idx[col_dir]] if col_dir and idx[col_dir] < len(r) else ""
        recs.append({
            "dt": dt,
            "type": r[idx[col_type]] if col_type and idx[col_type] < len(r) else "",
            "counterparty": r[idx[col_counterparty]] if col_counterparty and idx[col_counterparty] < len(r) else "",
            "goods": r[idx[col_goods]] if col_goods and idx[col_goods] < len(r) else "",
            "direction": direction,
            "amount": amount,
            "status": r[idx[col_status]] if col_status and idx[col_status] < len(r) else "",
        })
    if not recs:
        return "账单中未解析到有效交易记录。"

    out_total = sum(r["amount"] for r in recs if "支出" in r["direction"])
    in_total = sum(r["amount"] for r in recs if "收入" in r["direction"])
    love_out = sum(r["amount"] for r in recs if "支出" in r["direction"] and round(r["amount"]) in LOVE_AMOUNTS)
    span = f"{min(r['dt'] for r in recs):%Y-%m-%d} → {max(r['dt'] for r in recs):%Y-%m-%d}"

    out = ["## 交易账单汇总\n",
           f"- 交易笔数：{len(recs)} 笔，时间跨度：{span}",
           f"- 总支出：**{out_total:.2f} 元**；总收入：{in_total:.2f} 元；净付出：**{out_total - in_total:.2f} 元**"]
    if love_out:
        out.append(f"- 其中示爱金额（520/1314/888 等）合计：{love_out:.0f} 元　← 法律定性上有争议空间，单独统计")

    monthly = Counter()
    for r in recs:
        if "支出" in r["direction"]:
            monthly[f"{r['dt']:%Y-%m}"] += r["amount"]
    if monthly:
        out.append("\n### 按月支出\n")
        out.append("| 月份 | 支出(元) |")
        out.append("|---|---|")
        for ym in sorted(monthly):
            out.append(f"| {ym} | {monthly[ym]:.2f} |")

    by_type = Counter()
    for r in recs:
        if "支出" in r["direction"]:
            by_type[r["type"] or "未知"] += r["amount"]
    if by_type:
        out.append("\n### 按类型支出\n")
        out.append("| 交易类型 | 支出(元) | 笔数 |")
        out.append("|---|---|---|")
        for t, v in by_type.most_common():
            cnt = sum(1 for r in recs if "支出" in r["direction"] and (r["type"] or "未知") == t)
            out.append(f"| {t} | {v:.2f} | {cnt} |")

    out.append("\n### 逐笔明细（按时间）\n")
    out.append("| 时间 | 类型 | 收/支 | 金额(元) | 商品/备注 | 状态 |")
    out.append("|---|---|---|---|---|---|")
    for r in sorted(recs, key=lambda x: x["dt"]):
        goods = (r["goods"] or "-").replace("转账备注:", "备注:").replace("|", "，")[:40]
        mark = " ⭐" if r["direction"] and "支出" in r["direction"] and round(r["amount"]) in LOVE_AMOUNTS else ""
        out.append(f"| {r['dt']:%Y-%m-%d %H:%M} | {r['type']} | {r['direction'] or '-'} | "
                   f"{r['amount']:.2f}{mark} | {goods} | {r['status']} |")
    out.append("\n> ⭐ = 示爱金额转账。明细可逐笔与聊天记录的金钱语境对话交叉定位。\n")
    return "\n".join(out)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="聊天记录/交易账单预处理")
    ap.add_argument("--file", help="聊天记录文件（wechat-parse JSON 或 txt）")
    ap.add_argument("--bill", help="微信支付账单（xlsx 或 csv）")
    ap.add_argument("--sample", type=int, default=12, help="对话采样段数（默认 12）")
    ap.add_argument("--output", help="报告输出路径（默认 stdout）")
    args = ap.parse_args()

    if not args.file and not args.bill:
        ap.error("至少提供 --file 或 --bill")

    parts = []
    if args.file:
        msgs, meta = parse_chat(args.file)
        report, _ = analyze_chat(msgs, meta, args.sample)
        parts.append(f"# 聊天记录分析报告：{meta['peer']}\n\n{report}")
    if args.bill:
        header, rows = read_bill(args.bill)
        parts.append(f"# 交易账单分析\n\n{analyze_bill(header, rows)}")

    result = "\n\n---\n\n".join(parts)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"报告已写入 {args.output}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(result)


if __name__ == "__main__":
    main()
