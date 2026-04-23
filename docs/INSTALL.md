# Omnia 安装指南

## 🚀 一键安装（推荐新手）

### Mac / Linux

```bash
# 从 GitHub 下载并安装
curl -fsSL https://raw.githubusercontent.com/njuosun/omnia-os/main/scripts/quick-install.sh | bash
```

这个脚本会：
- ✅ 自动检测系统（Mac/Debian/RedHat）
- ✅ 安装所有依赖（Python、Node.js、Git）
- ✅ 下载最新版本的 Omnia
- ✅ 创建默认配置
- ✅ 创建启动命令 `omnia`

---

## 🛠️ 从源码安装（开发者）

### 方式 1：快速配置脚本

```bash
# 克隆仓库
git clone https://github.com/njuosun/omnia-os.git
cd omnia-os

# 运行配置脚本
chmod +x scripts/dev-setup.sh
./scripts/dev-setup.sh

# 启动
python scripts/start_daemon.py  # 后端
npm run tauri dev              # 前端
```

### 方式 2：手动配置

#### 1. 安装依赖

**macOS:**
```bash
brew install python3 node git
```

**Debian/Ubuntu:**
```bash
sudo apt install python3 python3-pip nodejs npm git build-essential
```

**RedHat/CentOS:**
```bash
sudo yum install python3 python3-pip nodejs npm git gcc make
```

#### 2. 安装 Python 依赖

```bash
pip3 install --user uvx fastapi uvicorn pydantic
```

#### 3. 安装 Node.js 依赖

```bash
npm install
```

#### 4. 创建配置文件

```bash
# 复制示例配置
cp config/mcp_servers.json.example config/mcp_servers.json
cp config/user.yaml.example config/user.yaml

# 编辑配置
nano config/user.yaml
```

#### 5. 启动

```bash
# 启动后端守护进程
python scripts/start_daemon.py

# 启动前端（新终端）
npm run tauri dev
```

---

## 📦 打包发布

### 构建发布包

```bash
# 构建所有平台
./scripts/build-release.sh

# 或单独构建
./scripts/build_all.sh
```

输出文件在 `release/` 目录：
- `Omnia_amd64.deb` - Debian/Ubuntu
- `Omnia_aarch64.dmg` - macOS ARM
- `Omnia_x64.dmg` - macOS Intel
- `Omnia_amd64.AppImage` - Linux 通用

---

## ⚙️ 配置说明

### MCP 服务器配置

编辑 `config/mcp_servers.json`：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home"],
      "env": {}
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"],
      "env": {}
    }
  }
}
```

### 用户配置

编辑 `config/user.yaml`：

```yaml
user:
  name: "你的名字"
  timezone: "Asia/Shanghai"
  
persona:
  default: "omnia"  # 或 "infinite"
  
memory:
  auto_save: true
  retention_days: 365
```

---

## 🐛 常见问题

### 1. `npx: command not found`

```bash
npm install -g npx
```

### 2. `uvx: command not found`

```bash
pip3 install --user uvx
```

### 3. 权限问题

```bash
chmod +x scripts/*.sh
```

### 4. Tauri 构建失败

```bash
# 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 安装系统依赖（Linux）
sudo apt install libwebkit2gtk-4.0-dev libgtk-3-dev libssl-dev
```

---

## 📚 更多文档

- [开发指南](./DEVELOPMENT.md)
- [架构说明](./ARCHITECTURE.md)
- [API 文档](./API.md)
- [贡献指南](../CONTRIBUTING.md)

---

## 💬 需要帮助？

- GitHub Issues: https://github.com/njuosun/omnia-os/issues
- 微信: NJ_UOSUN_UAV
