# Omnia AIOS

> 智能操作系统 · 让 AI 真正为你工作

[![Docker Build](https://github.com/IvesShan/omnia-os/actions/workflows/docker.yml/badge.svg)](https://github.com/IvesShan/omnia-os/actions/workflows/docker.yml)
[![ghcr.io](https://img.shields.io/badge/ghcr.io-ivesshan%2Fomnia-blue)](https://github.com/IvesShan/omnia-os/pkgs/container/omnia)

## 🚀 功能特性

- 🤖 AI Agent 引擎（多 LLM 切换：Kimi / OpenAI / Anthropic）
- 💾 结构化记忆系统（Memory Palace）
- 🧠 神经知识图谱（Neural Graph）
- 🛠️ 工具调用（文件/Shell/浏览器/数据库）
- 📊 自检与健康监控（omnia doctor）
- 🔌 MCP 服务器扩展

## 📦 快速开始（全平台）

### 方式零：pip 一行安装（推荐）⭐

**跨平台原生支持**：Windows / macOS / Linux，无需 Docker。

```bash
# 安装最新版
pip install git+https://github.com/IvesShan/omnia-os.git

# 或指定版本
pip install git+https://github.com/IvesShan/omnia-os.git@v0.1.0

# 推荐使用 pipx（隔离环境，更干净）
pipx install git+https://github.com/IvesShan/omnia-os.git

# 验证
omnia --help
omnia doctor
```

### 方式一：Docker（适合服务器部署）

**支持 Linux / macOS (Intel + Apple Silicon) / Windows**

```bash
# 拉取镜像（自动选择 amd64 或 arm64）
docker pull ghcr.io/ivesshan/omnia:latest

# 启动（暴露 8765 端口）
docker run -d \
  --name omnia \
  -p 8765:8765 \
  -v omnia-data:/app/data \
  -e OMNIA_LLM_API_KEY=你的API密钥 \
  ghcr.io/ivesshan/omnia:latest

# 验证
curl http://localhost:8765/health
# 期望返回：{"status": "ok", "ts": ...}
```

**前置要求**：安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Mac/Windows）或 Docker Engine（Linux）。

### 方式二：Docker Compose

```bash
git clone https://github.com/IvesShan/omnia-os.git
cd omnia-os
cp .env.example .env  # 填入你的 API 密钥
docker compose up -d
```

### 方式三：源码运行（开发者）

**前置**：Python 3.11+

```bash
git clone https://github.com/IvesShan/omnia-os.git
cd omnia-os

# 安装依赖
pip install -e .

# 自检（验证配置/网络/数据目录）
omnia doctor

# 启动后端
omnia serve
```

### 方式四：Linux 一键安装（含 systemd 自启）

```bash
git clone https://github.com/IvesShan/omnia-os.git
cd omnia-os
./install.sh
```

会自动配置 systemd 用户服务，开机自启。

## 🔧 常用命令

```bash
omnia doctor          # 全链路自检
omnia serve           # 启动后端服务
omnia status          # 查看运行状态
omnia version         # 版本信息
```

## 🐳 多架构支持

Docker 镜像同时构建 `linux/amd64` 和 `linux/arm64`，以下环境开箱即用：

| 平台 | 架构 | 状态 |
|------|------|------|
| Windows (x64) | amd64 | ✅ |
| Windows (ARM) | arm64 | ✅ |
| macOS (Intel) | amd64 | ✅ |
| macOS (M1/M2/M3) | arm64 | ✅ |
| Linux (x86_64) | amd64 | ✅ |
| Linux (ARM64 / 树莓派 4+) | arm64 | ✅ |

## 🌐 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OMNIA_LLM_API_KEY` | LLM API 密钥 | 必填 |
| `OMNIA_LLM_PROVIDER` | LLM 提供商（`kimi`/`openai`/`anthropic`） | `kimi` |
| `OMNIA_LLM_MODEL` | 模型名 | `kimi-for-coding` |
| `OMNIA_PORT` | 服务端口 | `8765` |
| `OMNIA_DATA_DIR` | 数据目录 | `~/.omnia` |

配置通过 `~/.omnia/omnia.yaml` 管理（首次运行自动创建），或通过环境变量覆盖。

## 📁 项目结构

```
omnia-os/
├── backend/             # FastAPI 后端
│   └── omnia_backend.py
├── src/omnia/           # 核心模块
│   ├── doctor.py        # 自检
│   ├── config_manager.py # 配置管理
│   └── ...
├── scripts/
│   ├── start_daemon.py  # 守护进程
│   └── ...
├── personas/            # Persona 配置
├── Dockerfile           # 多架构镜像定义
├── docker-compose.yml
├── install.sh           # Linux 一键安装
└── .env.example         # 环境变量模板
```

## 🔄 持续集成

每次 push 到 `main` 自动构建并推送 Docker 镜像到 `ghcr.io/ivesshan/omnia:latest`。

构建状态：https://github.com/IvesShan/omnia-os/actions

## 📖 文档

- [功能列表](FEATURES.md)
- [部署指南](DEPLOYMENT.md)
- [用户手册](README_FOR_USER.md)

## 🛡️ 安全提醒

- 不要把 `OMNIA_LLM_API_KEY` 提交到 git
- 不要把镜像设为 public 如果你不想让别人拉取（在 GitHub Packages 设置里改）
- 定期轮换 API 密钥和 GitHub PAT

## 📄 许可证

商业授权 · 保留所有权利

---

**作者**：[@IvesShan](https://github.com/IvesShan)
**主仓库**：https://github.com/IvesShan/omnia-os
**镜像**：https://github.com/IvesShan/omnia-os/pkgs/container/omnia
