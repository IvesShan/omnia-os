#!/bin/bash
# Omnia 一键安装脚本 (Mac + Linux)
# 使用方法: curl -fsSL https://your-domain/install.sh | bash

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 安装目录
INSTALL_DIR="$HOME/.omnia"
BIN_DIR="$HOME/.local/bin"

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# 打印函数
print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║      Omnia AIOS 一键安装程序              ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}[$1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 安装依赖 (Mac)
install_deps_macos() {
    print_step "1/6" "检查 macOS 依赖..."
    
    # 检查 Homebrew
    if ! command_exists brew; then
        print_step "1/6" "安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        print_success "Homebrew 已安装"
    else
        print_success "Homebrew 已存在"
    fi
    
    # 安装必要工具
    local deps=("python3" "node" "git")
    for dep in "${deps[@]}"; do
        if ! command_exists "$dep"; then
            print_step "1/6" "安装 $dep..."
            brew install "$dep" 2>/dev/null || brew install "$(echo $dep | sed 's/3//')"
        fi
    done
    
    print_success "macOS 依赖已就绪"
}

# 安装依赖 (Debian/Ubuntu)
install_deps_debian() {
    print_step "1/6" "检查 Debian/Ubuntu 依赖..."
    
    sudo apt update -qq
    
    local deps=("python3" "python3-pip" "nodejs" "npm" "git" "curl" "build-essential")
    for dep in "${deps[@]}"; do
        if ! command_exists "$dep"; then
            print_step "1/6" "安装 $dep..."
            sudo apt install -y "$dep"
        fi
    done
    
    print_success "Debian/Ubuntu 依赖已就绪"
}

# 安装依赖 (RedHat/CentOS)
install_deps_redhat() {
    print_step "1/6" "检查 RedHat/CentOS 依赖..."
    
    sudo yum update -y -q
    
    local deps=("python3" "python3-pip" "nodejs" "npm" "git" "curl" "gcc" "make")
    for dep in "${deps[@]}"; do
        if ! command_exists "$dep"; then
            print_step "1/6" "安装 $dep..."
            sudo yum install -y "$dep"
        fi
    done
    
    print_success "RedHat/CentOS 依赖已就绪"
}

# 安装 Python 依赖
install_python_deps() {
    print_step "2/6" "安装 Python 依赖..."
    
    # 安装 uvx (用于 MCP 服务器)
    pip3 install --user uvx 2>/dev/null || pip install --user uvx
    
    # 安装其他 Python 依赖
    pip3 install --user fastapi uvicorn pydantic 2>/dev/null || pip install --user fastapi uvicorn pydantic
    
    print_success "Python 依赖已安装"
}

# 安装 Node.js 依赖
install_node_deps() {
    print_step "3/6" "安装 Node.js 依赖..."
    
    # 安装 npx (通常随 npm 自动安装)
    if ! command_exists npx; then
        npm install -g npx
    fi
    
    print_success "Node.js 依赖已安装"
}

# 创建目录结构
create_directories() {
    print_step "4/6" "创建目录结构..."
    
    mkdir -p "$INSTALL_DIR"/{app,backend,config,data/{memory,logs},agents}
    mkdir -p "$BIN_DIR"
    mkdir -p "$HOME/.local/share/applications"
    
    print_success "目录创建完成"
}

# 下载 Omnia (从 GitHub 或本地)
download_omnia() {
    print_step "5/6" "下载 Omnia..."
    
    # 检测系统架构
    ARCH=$(uname -m)
    OS=$(detect_os)
    
    # GitHub Release URL (需要替换为实际地址)
    GITHUB_REPO="njuosun/omnia-os"
    RELEASE_URL="https://github.com/$GITHUB_REPO/releases/latest/download"
    
    # 根据系统选择下载文件
    if [[ "$OS" == "macos" ]]; then
        if [[ "$ARCH" == "arm64" ]]; then
            PACKAGE="Omnia_aarch64.dmg"
        else
            PACKAGE="Omnia_x64.dmg"
        fi
    else
        PACKAGE="Omnia_amd64.deb"
    fi
    
    # 尝试从 GitHub 下载
    if curl -fsSL "$RELEASE_URL/$PACKAGE" -o "/tmp/$PACKAGE" 2>/dev/null; then
        print_success "从 GitHub 下载成功"
        
        # 安装包
        if [[ "$OS" == "macos" ]]; then
            # macOS: 挂载 DMG 并复制
            hdiutil attach "/tmp/$PACKAGE" -quiet
            cp -R /Volumes/Omnia*/Omnia.app /Applications/ 2>/dev/null || true
            hdiutil detach /Volumes/Omnia* -quiet
        else
            # Linux: 安装 deb
            sudo dpkg -i "/tmp/$PACKAGE" || sudo apt install -f -y
        fi
    else
        print_error "无法从 GitHub 下载"
        echo ""
        echo -e "${YELLOW}请手动下载:${NC}"
        echo "  https://github.com/$GITHUB_REPO/releases"
        echo ""
        echo -e "${YELLOW}或从源码构建:${NC}"
        echo "  git clone https://github.com/$GITHUB_REPO.git"
        echo "  cd omnia-os && ./scripts/build-release.sh"
        exit 1
    fi
}

# 创建默认配置
create_default_config() {
    print_step "6/6" "创建默认配置..."
    
    # MCP 服务器配置
    cat > "$INSTALL_DIR/config/mcp_servers.json" << 'EOF'
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
    
    # 用户配置
    cat > "$INSTALL_DIR/config/user.yaml" << 'EOF'
# Omnia 用户配置
user:
  name: ""
  timezone: "Asia/Shanghai"
  
persona:
  default: "omnia"
  
memory:
  auto_save: true
  retention_days: 365
  
mcp:
  auto_start: true
  servers: ["filesystem", "git", "fetch"]
EOF
    
    print_success "配置文件已创建"
}

# 创建启动脚本
create_launcher() {
    print_step "6/6" "创建启动脚本..."
    
    cat > "$BIN_DIR/omnia" << 'EOF'
#!/bin/bash
# Omnia 启动脚本

INSTALL_DIR="$HOME/.omnia"

# 启动守护进程
if [ -f "$INSTALL_DIR/backend/daemon.py" ]; then
    python3 "$INSTALL_DIR/backend/daemon.py" &
fi

# 启动桌面应用
if [ -f "/Applications/Omnia.app/Contents/MacOS/Omnia" ]; then
    # macOS
    open -a Omnia
elif [ -f "/usr/bin/omnia-desktop" ]; then
    # Linux
    omnia-desktop &
else
    echo "Omnia 未安装或路径不正确"
    exit 1
fi
EOF
    
    chmod +x "$BIN_DIR/omnia"
    
    # 添加到 PATH
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        echo "" >> "$HOME/.bashrc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        echo "" >> "$HOME/.zshrc" 2>/dev/null || true
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    fi
    
    print_success "启动脚本已创建"
}

# 创建桌面快捷方式 (Linux)
create_desktop_entry() {
    if [[ "$(detect_os)" != "macos" ]]; then
        cat > "$HOME/.local/share/applications/omnia.desktop" << 'EOF'
[Desktop Entry]
Name=Omnia
Comment=AI Operating System
Exec=omnia
Icon=/home/user/.omnia/app/icon.png
Terminal=false
Type=Application
Categories=Development;Utility;
EOF
        print_success "桌面快捷方式已创建"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          安装完成！                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}安装目录:${NC} $INSTALL_DIR"
    echo -e "${BLUE}配置文件:${NC} $INSTALL_DIR/config/"
    echo ""
    echo -e "${YELLOW}启动方式:${NC}"
    echo "  1. 重启终端后运行: omnia"
    echo "  2. 或立即启动: source ~/.bashrc && omnia"
    echo ""
    echo -e "${YELLOW}首次配置:${NC}"
    echo "  编辑 $INSTALL_DIR/config/user.yaml"
    echo "  设置你的名字、时区等"
    echo ""
    echo -e "${BLUE}文档:${NC} https://github.com/njuosun/omnia-os"
    echo ""
}

# 主函数
main() {
    print_header
    
    # 检测操作系统
    OS=$(detect_os)
    echo -e "${BLUE}检测到系统:${NC} $OS"
    echo ""
    
    # 检查是否已安装
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}检测到已有安装${NC}"
        read -p "是否覆盖安装？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "安装已取消"
            exit 0
        fi
        print_step "0/6" "卸载旧版本..."
        rm -rf "$INSTALL_DIR"
    fi
    
    # 安装依赖
    case "$OS" in
        macos)
            install_deps_macos
            ;;
        debian)
            install_deps_debian
            ;;
        redhat)
            install_deps_redhat
            ;;
        *)
            print_error "不支持的系统: $OS"
            echo "请手动安装依赖: Python 3.10+, Node.js 18+, Git"
            exit 1
            ;;
    esac
    
    # 安装其他依赖
    install_python_deps
    install_node_deps
    
    # 创建目录
    create_directories
    
    # 下载 Omnia
    download_omnia
    
    # 创建配置
    create_default_config
    
    # 创建启动脚本
    create_launcher
    create_desktop_entry
    
    # 完成
    show_completion
}

# 运行主函数
main
