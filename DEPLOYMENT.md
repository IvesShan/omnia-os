# Omnia 部署指南

## 一键部署架构

```
┌─────────────────────────────────────────────┐
│              Tauri 前端应用                  │
│                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 💬 聊天 │ │ ⚙️ 设置 │ │ 📊 日志 │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                                             │
│  • 服务管理器（启动/停止后端）              │
│  • 配置管理（API Key、模型选择）            │
│  • 日志实时查看                            │
└──────────────┬──────────────────────────────┘
               │ HTTP API (localhost:5001)
┌──────────────▼──────────────────────────────┐
│           Python 后端服务                    │
│  • API 代理（百度千帆/Kimi）                 │
│  • Memory Palace                            │
│  • Agent 管理                                │
└─────────────────────────────────────────────┘
```

## 快速开始

### 开发环境

```bash
# 1. 快速启动（后端 + Tauri 开发模式）
./scripts/quick_start.sh

# 2. 或手动启动
# 启动后端
python3 backend/standalone_main.py

# 启动 Tauri 开发模式
cd src-tauri && cargo tauri dev
```

### 生产构建

```bash
# 完整构建（前端 + 后端 + 打包）
./scripts/build_all.sh

# 或分步构建
python3 scripts/build_backend.py  # 打包 Python 后端
cd src-tauri && cargo tauri build # 打包 Tauri 应用
```

## 发布包结构

```
release/
├── Omnia_0.1.0_amd64.AppImage    # Tauri 前端应用
├── omnia-backend                  # PyInstaller 打包的后端
├── install.sh                     # 一键安装
├── uninstall.sh                   # 卸载脚本
├── config/                        # 默认配置
│   └── settings.json
└── README.md
```

## 安装部署

### 一键安装

```bash
# 1. 复制 release 目录到目标机器
scp -r release/ user@target:/tmp/omnia/

# 2. 运行安装脚本
cd /tmp/omnia
./install.sh
```

### 安装后目录

```
~/.omnia/
├── app/                          # 应用程序
│   ├── Omnia.AppImage
│   └── start.sh                  # 启动脚本
├── backend/                      # 后端服务
│   └── omnia-backend
├── config/                       # 用户配置
│   ├── settings.json             # 主配置
│   └── api_keys.json             # API 密钥
├── data/                         # 数据文件
│   ├── memory/                   # Memory Palace
│   └── logs/                     # 日志文件
└── agents/                       # 自定义 Agent
```

### 启动方式

```bash
# 方式 1: 命令行
omnia

# 方式 2: 桌面快捷方式
# 在应用菜单中找到 "Omnia AIOS"

# 方式 3: 直接运行
~/.omnia/app/start.sh
```

## 配置管理

### 主配置 (settings.json)

```json
{
  "backend_port": 5001,
  "api_provider": "kimi",
  "model_name": "moonshot-v1-8k",
  "auto_start_backend": true,
  "log_level": "info"
}
```

### API 密钥配置

**方式 1: 通过设置页面**
- 打开 Omnia
- 点击设置图标
- 在 API 配置中输入密钥

**方式 2: 手动编辑**
```bash
vim ~/.omnia/config/api_keys.json
```

```json
{
  "kimi": "sk-...",
  "baidu": "...",
  "openai": "sk-..."
}
```

## 功能模块

### 1. 服务管理器

- **启动后端**: 自动启动 Python 后端服务
- **停止后端**: 优雅关闭后端进程
- **状态监控**: 实时显示后端运行状态
- **自动重启**: 后端崩溃时自动重启

### 2. 配置中心

- **API 提供商**: Kimi / 百度千帆 / OpenAI
- **模型选择**: moonshot-v1-8k / 32k / 128k
- **端口配置**: 自定义后端端口
- **日志级别**: debug / info / warn / error

### 3. 日志查看器

- **实时日志**: WebSocket 推送
- **日志过滤**: 按级别过滤
- **日志搜索**: 关键词搜索
- **日志导出**: 导出为文件

## 开发指南

### 添加新的 API 提供商

1. 在 `backend/standalone_main.py` 中添加新的路由
2. 在 `web/settings.html` 中添加选项
3. 在 `src-tauri/src/commands.rs` 中更新配置结构

### 添加新的功能模块

1. **后端**: 在 `backend/standalone_main.py` 添加 API 路由
2. **前端**: 在 `web/` 目录添加 HTML 页面
3. **Tauri**: 在 `src-tauri/src/commands.rs` 添加命令

### 调试

```bash
# 查看后端日志
tail -f ~/.omnia/logs/backend.log

# 查看 Tauri 日志
# 在开发者工具中查看 (Ctrl+Shift+I)
```

## 卸载

```bash
./uninstall.sh

# 或手动删除
rm -rf ~/.omnia
rm ~/.local/share/applications/omnia.desktop
rm ~/.local/bin/omnia
```

## 依赖要求

### 运行时
- Linux x86_64
- 无需额外依赖（所有依赖已打包）

### 构建时
- Python 3.8+
- Node.js 18+
- Rust 1.70+
- Tauri CLI

## 故障排除

### 后端无法启动

```bash
# 检查端口是否被占用
lsof -i :5001

# 检查日志
tail -f ~/.omnia/logs/backend.log
```

### API 调用失败

1. 检查 API Key 是否正确
2. 检查网络连接
3. 查看日志中的错误信息

### 应用无法启动

```bash
# 检查权限
chmod +x ~/.omnia/app/Omnia.AppImage
chmod +x ~/.omnia/backend/omnia-backend

# 检查依赖
ldd ~/.omnia/backend/omnia-backend
```

## 更新日志

### v0.1.0 (2024-04-15)
- 初始版本
- 支持一键部署
- 服务管理器
- 配置中心
- 日志查看器
