#!/bin/bash
# Omnia 本地一键安装脚本
# 适用于：已有 deb 包或源码的情况

set -e

echo "╔═══════════════════════════════════════════╗"
echo "║     Omnia 本地一键安装                    ║"
echo "╚═══════════════════════════════════════════╝"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检测系统
OS=$(uname -s)
case $OS in
    Linux*)  MACHINE=Linux ;;
    Darwin*) MACHINE=Mac ;;
    *)       echo "不支持的系统: $OS"; exit 1 ;;
esac

echo -e "${GREEN}[✓] 检测到系统: $MACHINE${NC}"

# 1. 检查依赖
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1/4: 检查依赖..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}[✓] $1 已安装${NC}"
        return 0
    else
        echo -e "${YELLOW}[!] $1 未安装${NC}"
        return 1
    fi
}

MISSING=()
check_command python3 || MISSING+=("python3")
check_command node || MISSING+=("nodejs")
check_command npm || MISSING+=("npm")
check_command git || MISSING+=("git")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "缺少依赖: ${MISSING[*]}"
    echo ""
    
    read -p "是否自动安装？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$MACHINE" = "Mac" ]; then
            # Mac 用 brew
            if ! command -v brew &> /dev/null; then
                echo "请先安装 Homebrew: https://brew.sh"
                exit 1
            fi
            brew install ${MISSING[*]}
        elif [ "$MACHINE" = "Linux" ]; then
            # Linux 用 apt
            sudo apt update
            sudo apt install -y ${MISSING[*]}
        fi
    else
        echo "请手动安装依赖后重试"
        exit 1
    fi
fi

# 2. 安装 Python 依赖
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2/4: 安装 Python 依赖..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v uvx &> /dev/null; then
    echo "安装 uvx..."
    pip3 install uvx --user
fi
echo -e "${GREEN}[✓] uvx 已就绪${NC}"

# 3. 查找并安装 deb 包
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 3/4: 安装 Omnia..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 查找 deb 包
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEB_PATH="$PROJECT_ROOT/src-tauri/target/release/bundle/deb"

# 查找最新的 deb 文件
DEB_FILE=$(find "$DEB_PATH" -name "*.deb" -type f 2>/dev/null | head -n 1)

if [ -z "$DEB_FILE" ]; then
    echo -e "${YELLOW}[!] 未找到 deb 包${NC}"
    echo ""
    echo "请选择："
    echo "  1. 从源码构建（需要 Rust）"
    echo "  2. 手动指定 deb 文件路径"
    echo "  3. 退出"
    echo ""
    read -p "选择 (1/2/3): " choice
    
    case $choice in
        1)
            echo "从源码构建..."
            cd "$PROJECT_ROOT"
            npm install
            npm run tauri build
            DEB_FILE=$(find "$DEB_PATH" -name "*.deb" -type f | head -n 1)
            ;;
        2)
            read -p "请输入 deb 文件路径: " DEB_FILE
            ;;
        3)
            echo "退出安装"
            exit 0
            ;;
        *)
            echo "无效选择"
            exit 1
            ;;
    esac
fi

if [ -f "$DEB_FILE" ]; then
    echo "找到安装包: $DEB_FILE"
    
    if [ "$MACHINE" = "Linux" ]; then
        echo "安装 deb 包..."
        sudo dpkg -i "$DEB_FILE" || sudo apt --fix-broken install -y
        echo -e "${GREEN}[✓] Omnia 已安装${NC}"
    else
        echo -e "${YELLOW}[!] Mac 系统暂不支持 deb 包${NC}"
        echo "请使用开发模式运行: npm run tauri dev"
    fi
else
    echo -e "${YELLOW}[!] 未找到安装包，使用开发模式${NC}"
    echo "运行命令: cd $PROJECT_ROOT && npm run tauri dev"
fi

# 4. 创建配置
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 4/4: 创建配置..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p ~/.omnia/config

# 复制现有配置
if [ -d "$PROJECT_ROOT/config" ]; then
    cp -r "$PROJECT_ROOT/config/"* ~/.omnia/config/ 2>/dev/null || true
    echo -e "${GREEN}[✓] 配置已复制到 ~/.omnia/config/${NC}"
else
    # 创建默认配置
    cat > ~/.omnia/config/mcp_servers.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "/home"]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"]
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}
EOF
    echo -e "${GREEN}[✓] 默认配置已创建${NC}"
fi

# 创建启动命令
if [ "$MACHINE" = "Linux" ]; then
    cat > ~/.local/bin/omnia << 'EOF'
#!/bin/bash
# Omnia 启动脚本

# 启动守护进程
python3 ~/.omnia/scripts/start_daemon.py &

# 启动桌面应用
omnia-desktop
EOF
    chmod +x ~/.local/bin/omnia
    echo -e "${GREEN}[✓] 创建启动命令: omnia${NC}"
fi

# 完成
echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║           🎉 安装完成！                   ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "启动方式："
if [ "$MACHINE" = "Linux" ]; then
    echo "  • 命令行: omnia"
    echo "  • 应用菜单: 搜索 'Omnia'"
else
    echo "  • 开发模式: cd $PROJECT_ROOT && npm run tauri dev"
fi
echo ""
echo "配置目录: ~/.omnia/config/"
echo ""
