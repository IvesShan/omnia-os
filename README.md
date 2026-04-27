![Omnia Logo](web/omnia_logo.svg)

# Omnia — 永不遗忘的 AI 操作系统

**Omnia** 是一个本地化的 AI 操作系统，核心设计理念是 **永不遗忘、持续进化**。

## Architecture

```
L5 · Ethos           → Identity / Narrative / Core Values
L4 · Conscience      → Context Compression / System Journal
L3 · Unconscious     → Skills / Memory Palace / Patchwork / Ambient Context
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
bash scripts/deploy.sh

# 3. 编辑配置文件填入 API Key
vim .env

# 4. 服务自动启动，无需额外操作
```

### 日常管理

```bash
# 查看所有服务状态
bash scripts/manage.sh status

# 实时查看日志
bash scripts/manage.sh logs
bash scripts/manage.sh logs web      # 只看 Web 日志
bash scripts/manage.sh logs daemon   # 只看守护进程日志

# 启动 / 停止 / 重启
bash scripts/manage.sh start
bash scripts/manage.sh stop
bash scripts/manage.sh restart
```

### 开机自启（已配置好）

服务已注册为 systemd 用户服务，开机自动启动。

```bash
systemctl --user status omnia          # 查看 Web 服务状态
systemctl --user status omnia-daemon   # 查看守护进程状态
systemctl --user status omnia-watchdog # 查看看门狗状态
```

## Origin

Omnia was conceived on April 10, 2026, during a late-night conversation between a human and their AI assistant, Wúxiàn. You can read the full story in [`seeds/bond_manifesto.md`](seeds/bond_manifesto.md).

## Status

- **Web Interface** — accessible at `http://localhost:5001`
- **Daemon** — background AI core process
- **Watchdog** — auto-recovery on failure

## Tech Stack

- Python 3.10+ / Flask / WebSocket
- DeepSeek / OpenAI API
- systemd (Linux)
