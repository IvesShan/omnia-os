#!/usr/bin/env bash
# Omnia 一键安装脚本
# 用法: curl -fsSL <url>/install.sh | bash   或   ./install.sh
# 目标: 检测环境 → 装依赖 → 生成配置 → 自检，换电脑 5 分钟跑起来

set -euo pipefail

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}ℹ${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $*"; }
fail()  { echo -e "${RED}❌${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}"
echo "  ___  __  __ _   _ ___    _    "
echo " / _ \|  \/  | \ | |_ _|  / \   "
echo "| | | | |\/| |  \| || |  / _ \  "
echo "| |_| | |  | | |\  || | / ___ \ "
echo " \___/|_|  |_|_| \_|___/_/   \_"
echo -e "${NC}"
echo "Omnia AIOS 一键安装"
echo "========================================"

# ---- 1. 检测操作系统 ----
info "检测操作系统..."
OS="$(uname -s)"
case "$OS" in
  Linux)  PLATFORM="linux";;
  Darwin) PLATFORM="macos";;
  *)      fail "暂不支持 $OS（Windows 请用 WSL2 或 Docker）"; exit 1;;
esac
ok "平台: $PLATFORM"

# ---- 2. 检测 Python ----
info "检测 Python >= 3.10..."
if command -v python3 >/dev/null 2>&1; then
  PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  PYMAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
  PYMINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
  if [ "$PYMAJOR" -ge 3 ] && [ "$PYMINOR" -ge 10 ]; then
    ok "Python $PYVER"
    PYTHON=python3
  else
    fail "Python $PYVER 过旧，需要 >= 3.10"
    exit 1
  fi
else
  fail "未找到 python3"
  info "安装方法: Ubuntu/Debian: sudo apt install python3 python3-venv | macOS: brew install python@3.12"
  exit 1
fi

# ---- 3. 创建虚拟环境 ----
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  info "创建虚拟环境 .venv ..."
  $PYTHON -m venv "$VENV_DIR" || { fail "venv 创建失败（Ubuntu 可能需要: sudo apt install python3-venv）"; exit 1; }
  ok "虚拟环境已创建"
else
  ok "虚拟环境已存在"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ---- 4. 安装依赖 ----
if [ -f "requirements.txt" ]; then
  info "安装 Python 依赖（使用国内镜像加速）..."
  pip install --upgrade pip -q
  pip install -r requirements.txt -q -i https://mirrors.aliyun.com/pypi/simple/ || \
    pip install -r requirements.txt -q
  ok "依赖安装完成"
else
  warn "未找到 requirements.txt，跳过依赖安装"
fi

# ---- 4.5 预热 MCP server 依赖（避免首次启动联网下载）----
info "预热 MCP server 依赖..."
# 确保 ~/.local/bin 在 PATH（uv/uvx 默认装在这里）
export PATH="$HOME/.local/bin:$PATH"

# uv/uvx (Python MCP servers: mcp-server-git / mcp-server-fetch)
if ! command -v uv >/dev/null 2>&1; then
  info "安装 uv（Python 包管理器，用于 MCP server）..."
  pip install uv -q -i https://mirrors.aliyun.com/pypi/simple/ 2>/dev/null || pip install uv -q || true
fi

if command -v uv >/dev/null 2>&1; then
  # 用 uv tool install 明确下载并缓存，立即返回（不会像 uvx 启动 stdio server 那样阻塞）
  timeout 90 uv tool install mcp-server-git --quiet >/dev/null 2>&1 && \
    ok "mcp-server-git 已缓存" || warn "mcp-server-git 预热失败（不影响核心功能）"
  timeout 90 uv tool install mcp-server-fetch --quiet >/dev/null 2>&1 && \
    ok "mcp-server-fetch 已缓存" || warn "mcp-server-fetch 预热失败（不影响核心功能）"
else
  warn "uv 安装失败，git/fetch MCP server 首次启动时会联网下载（不影响核心功能）"
fi

# npx (Node MCP servers: filesystem / puppeteer)
if command -v npx >/dev/null 2>&1; then
  # filesystem server 不响应 CLI 参数，但 npx 下载后即进缓存；timeout 防卡住
  timeout 60 npx -y @modelcontextprotocol/server-filesystem --version >/dev/null 2>&1 && \
    ok "filesystem MCP 已缓存" || ok "filesystem MCP 已下载（退出码非0属正常）"
else
  warn "未找到 npx，filesystem/puppeteer MCP server 不可用（不影响核心功能）"
fi

# ---- 5. 生成配置文件 ----
info "准备配置文件..."
if [ ! -f "$HOME/.omnia/omnia.yaml" ]; then
  mkdir -p "$HOME/.omnia"
  if [ -f "omnia.yaml.example" ]; then
    cp omnia.yaml.example "$HOME/.omnia/omnia.yaml"
    ok "已生成 $HOME/.omnia/omnia.yaml"
  fi
else
  ok "配置文件已存在: $HOME/.omnia/omnia.yaml"
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  ok "已从 .env.example 生成 .env（请编辑填入你的 API key）"
fi

# ---- 6. 安装 omnia 命令到 PATH ----
info "配置 omnia 命令..."
LINK_DIR="$HOME/.local/bin"
mkdir -p "$LINK_DIR"
cat > "$LINK_DIR/omnia" <<EOF
#!/usr/bin/env bash
cd "$SCRIPT_DIR"
source "$VENV_DIR/bin/activate"
export PYTHONPATH="$SCRIPT_DIR/src:\${PYTHONPATH}"
exec python -m omnia "\$@"
EOF
chmod +x "$LINK_DIR/omnia"
if echo "$PATH" | grep -q "$LINK_DIR"; then
  ok "omnia 命令已安装到 $LINK_DIR"
else
  warn "请将 $LINK_DIR 加入 PATH（添加到 ~/.bashrc 或 ~/.zshrc）:"
  echo "    export PATH=\"$LINK_DIR:\$PATH\""
fi

# ---- 7. 自检 ----
echo ""
echo "========================================"
info "运行 omnia doctor 自检..."
echo "========================================"
export PYTHONPATH="$SCRIPT_DIR/src:${PYTHONPATH:-}"
python -m omnia doctor || true

echo ""
echo "========================================"
ok "安装完成！"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 编辑 API key:  nano .env   （或 nano ~/.omnia/omnia.yaml）"
echo "  2. 验证配置:      omnia doctor"
echo "  3. 启动服务:      omnia serve  (或参见 README)"
echo "  4. 开始对话:      omnia chat \"你好\""
echo ""
echo "Docker 方式（推荐生产部署）:"
echo "  docker compose up -d"
echo ""
