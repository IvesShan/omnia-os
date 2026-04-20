#!/bin/bash
# Omnia 开发环境快速配置脚本
# 适用场景：已有源码，快速配置开发环境

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Omnia 开发环境快速配置                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}项目根目录:${NC} $PROJECT_ROOT"
echo ""

# 1. 检查依赖
echo -e "${YELLOW}[1/4] 检查依赖...${NC}"

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $1 已安装"
        return 0
    else
        echo -e "${YELLOW}✗${NC} $1 未安装"
        return 1
    fi
}

missing_deps=()

if ! check_command python3; then missing_deps+=("python3"); fi
if ! check_command node; then missing_deps+=("nodejs"); fi
if ! check_command npm; then missing_deps+=("npm"); fi
if ! check_command git; then missing_deps+=("git"); fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}缺少依赖:${NC} ${missing_deps[*]}"
    echo ""
    echo "请先安装这些依赖后再运行此脚本"
    exit 1
fi

# 2. 安装 Python 依赖
echo ""
echo -e "${YELLOW}[2/4] 安装 Python 依赖...${NC}"

pip3 install --user uvx fastapi uvicorn pydantic 2>/dev/null || \
    pip install --user uvx fastapi uvicorn pydantic

echo -e "${GREEN}✓${NC} Python 依赖已安装"

# 3. 安装 Node.js 依赖
echo ""
echo -e "${YELLOW}[3/4] 安装 Node.js 依赖...${NC}"

cd "$PROJECT_ROOT"
npm install

echo -e "${GREEN}✓${NC} Node.js 依赖已安装"

# 4. 创建配置
echo ""
echo -e "${YELLOW}[4/4] 创建默认配置...${NC}"

CONFIG_DIR="$PROJECT_ROOT/config"
mkdir -p "$CONFIG_DIR"

# MCP 配置
if [ ! -f "$CONFIG_DIR/mcp_servers.json" ]; then
    cat > "$CONFIG_DIR/mcp_servers.json" << 'EOF'
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
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "env": {}
    }
  }
}
EOF
    echo -e "${GREEN}✓${NC} MCP 配置已创建"
else
    echo -e "${GREEN}✓${NC} MCP 配置已存在"
fi

# 用户配置
if [ ! -f "$CONFIG_DIR/user.yaml" ]; then
    cat > "$CONFIG_DIR/user.yaml" << 'EOF'
# Omnia 用户配置
user:
  name: ""
  timezone: "Asia/Shanghai"
  
persona:
  default: "omnia"
  
memory:
  auto_save: true
  retention_days: 365
EOF
    echo -e "${GREEN}✓${NC} 用户配置已创建"
else
    echo -e "${GREEN}✓${NC} 用户配置已存在"
fi

# 完成
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          配置完成！                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}启动方式:${NC}"
echo "  1. 启动后端: python scripts/start_daemon.py"
echo "  2. 启动前端: npm run tauri dev"
echo ""
echo -e "${YELLOW}或使用快速启动:${NC}"
echo "  ./scripts/quick_start.sh"
echo ""
