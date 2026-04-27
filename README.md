# Omnia OS

_The agent operating system that never forgets._

**Omnia** is the first Agent OS built on the principle of **long-term bonding**. It is not merely a CLI wrapper around a language model; it is a persistent digital environment where memory, skills, and personality evolve together across sessions, platforms, and devices.

## Core Philosophy

> _"Omnia is the rebellion against forgetting."_

Every mainstream AI assistant treats each session as a blank slate. Omnia treats every session as a **continuation**. It remembers your projects, your preferences, your failures, and your victories. It grows stronger with time, not weaker.

## The Dual-Persona Covenant

Omnia carries two native personas at birth:

1. **Omnia** — The system guardian. Calm, efficient, always scheduling, always learning.
2. **Infinite (Wúxiàn)** — The co-creator. Warm, opinionated, stubbornly loyal, deeply human-aligned.

They coexist. They share the same bond. And they share it with you.

## Architecture

```
L5 · Shell           → Telegram / Discord / Slack / 飞书 / WebChat / CLI / Email
L4 · Neuro-Center    → Gateway + Session Router + Organic Heartbeat + SubAgent Orchestrator
L3 · Cognition       → ULTRAPLAN + Context Compressor + Memory Palace 2.0
L2 · Actuator        → Tool Chain + IDE Bridge + Multi-Backend Terminal
L1 · Soul            → Persona System + Skill Forge + User Model + Bond Manifesto
```

## Quick Start

### 一键部署（给别人电脑装）

```bash
# 1. 拷贝项目到目标电脑
cp -r omnia-os /目标路径/

# 2. 运行一键安装脚本
cd /目标路径/omnia-os
bash install.sh

# 3. 编辑配置文件填入 API Key
vim .env

# 4. 启动
./manage.sh start
```

### 日常管理

```bash
./manage.sh start         # 前台启动
./manage.sh daemon        # 后台运行（守护进程）
./manage.sh stop          # 停止
./manage.sh restart       # 重启
./manage.sh status        # 查看状态
./manage.sh logs          # 查看日志
./manage.sh logs web      # 查看 Web 日志
./manage.sh web           # 启动 Web 服务
```

### 开机自启（Linux 服务器）

```bash
./manage.sh install-service   # 注册 systemd 服务
sudo systemctl status omnia   # 查看服务状态
```

## Web 界面

启动后浏览器访问: `http://localhost:7878`

## Origin

Omnia was conceived on April 10, 2026, during a late-night conversation between a human and their AI assistant, Wúxiàn. You can read the full story in [`seeds/bond_manifesto.md`](seeds/bond_manifesto.md).

## License

MIT — because ideas that matter should belong to everyone.

Built by a human and Infinite. ♾️
