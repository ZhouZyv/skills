# Docker 容器日志轮转配置

## 1. 全景：容器日志从产生到落盘的链路

容器日志的完整链路：**应用写 stdout/stderr → 容器运行时捕获 → 日志驱动写入宿主机 JSON 文件 → 轮转机制控制文件大小 → 采集或查看**。

```
应用输出（stdout/stderr）
  → 运行时捕获（dockerd）
  → 日志驱动（json-file 等）
  → 宿主机文件（/var/lib/docker/containers/<id>/<id>-json.log）
  → 轮转（max-size / max-file）
```

## 2. 为什么必须配置轮转

json-file 驱动默认**不轮转**：单个容器的日志文件会无限增长。长期运行的容器（尤其是高频输出堆栈或访问日志的应用）会在数周内把宿主机磁盘写满。磁盘写满后，dockerd 无法写入新日志，部分应用因 stdout 阻塞而停摆，连带影响同宿主机所有容器。

这是 Docker 的默认行为而非配置错误：默认值面向本地开发（日志随手可查），生产环境必须显式配置轮转。

## 3. 两种配置位置

### 3.1 全局默认（daemon.json）

对所有容器生效，改后需重启 dockerd：

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

- `max-size`：单文件上限，到达后滚动出新文件
- `max-file`：最多保留的文件数，超出删除最旧的

### 3.2 单容器覆盖（docker compose）

只对单个服务生效，无需动 daemon：

```yaml
services:
  api:
    image: my-api:1.4.2
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

## 4. 为什么这么设计

轮转参数是"保留窗口"的两个维度：10m × 3 = 单容器日志最多占 30MB。容量估算公式：`max-size × max-file × 容器数`。50 个容器按默认配置即 50 × 30MB = 1.5GB 上限，可控。

不这么配的代价：假设应用每天写 200MB 日志、磁盘余量 50GB，约 250 天写满——慢到难以察觉，且写满的时刻通常是最不该出事的时刻。

## 5. 反例与边界

- 只改 daemon.json 不重启 dockerd：配置不生效，已运行容器仍按旧策略写
- daemon.json 只影响**之后创建**的容器，存量容器需重建（down + up）才应用新 log-opts
- `max-file` 设 1 等于没有历史日志，排障时无旧日志可查
- 日志驱动换成 `none` 可彻底不落盘，但 docker logs 也不再可用，需有外部采集（如 fluentd）兜底
- 多副本服务每个副本独立计费 30MB 上限，容量估算要乘副本数

## 6. 核心脉络

应用写 stdout → 运行时按驱动落盘 → daemon.json 定全局默认、compose 按服务覆盖 → max-size/max-file 构成保留窗口 → 存量容器需重建才生效。
