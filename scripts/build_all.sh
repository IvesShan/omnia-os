#!/bin/bash
# Omnia 完整构建脚本
# 构建前端 + 后端 + Tauri 应用

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "Omnia 完整构建"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${YELLOW}[步骤 $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 步骤 1: 检查依赖
print_step 1 "检查构建依赖..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    print_error "Python3 未安装"
    exit 1
fi
print_success "Python3 已安装: $(python3 --version)"

# 检查 Node.js (Tauri 需要)
if ! command -v node &> /dev/null; then
    print_error "Node.js 未安装"
    exit 1
fi
print_success "Node.js 已安装: $(node --version)"

# 检查 Rust
if ! command -v rustc &> /dev/null; then
    print_error "Rust 未安装"
    exit 1
fi
print_success "Rust 已安装: $(rustc --version)"

# 检查 Tauri CLI
if ! command -v tauri &> /dev/null; then
    print_step 1.1 "安装 Tauri CLI..."
    cargo install tauri-cli
fi
print_success "Tauri CLI 已安装"

echo ""

# 步骤 2: 构建 Python 后端
print_step 2 "构建 Python 后端..."
cd "$PROJECT_ROOT"
if [ -f "scripts/build_backend.py" ]; then
    python3 scripts/build_backend.py
    if [ $? -ne 0 ]; then
        print_error "后端构建失败"
        exit 1
    fi
    print_success "后端构建完成"
else
    print_success "跳过后端构建 (build_backend.py 不存在)"
fi
echo ""

# 步骤 3: 构建 Tauri 应用
print_step 3 "构建 Tauri 应用..."
cd "$PROJECT_ROOT/src-tauri"

# 设置目标平台
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到 Linux 系统"
    # 检查 AppImage 依赖
    if ! command -v appimagetool &> /dev/null; then
        echo "提示: appimagetool 未安装，将只构建 deb 包"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS 系统"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    echo "检测到 Windows 系统"
fi

# 构建
cargo tauri build
if [ $? -ne 0 ]; then
    print_error "Tauri 构建失败"
    exit 1
fi
print_success "Tauri 构建完成"
echo ""

# 步骤 4: 整理发布包
print_step 4 "创建发布包..."
RELEASE_DIR="$PROJECT_ROOT/release"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/config"

# 复制构建产物
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # 复制 AppImage
    APPIMAGE_FILE=$(find "$PROJECT_ROOT/src-tauri/target/release/bundle/appimage" -name "*.AppImage" 2>/dev/null | head -n 1)
    if [ -n "$APPIMAGE_FILE" ]; then
        cp "$APPIMAGE_FILE" "$RELEASE_DIR/"
        print_success "已复制 AppImage"
    fi
    
    # 复制 deb
    DEB_FILE=$(find "$PROJECT_ROOT/src-tauri/target/release/bundle/deb" -name "*.deb" 2>/dev/null | head -n 1)
    if [ -n "$DEB_FILE" ]; then
        cp "$DEB_FILE" "$RELEASE_DIR/"
        print_success "已复制 deb 包"
    fi
fi

# 复制图标到发布包
if [ -f "$PROJECT_ROOT/src-tauri/icons/icon.png" ]; then
    cp "$PROJECT_ROOT/src-tauri/icons/icon.png" "$RELEASE_DIR/"
    print_success "已复制图标"
fi

# 复制安装脚本
cp "$PROJECT_ROOT/scripts/install.sh" "$RELEASE_DIR/"
cp "$PROJECT_ROOT/scripts/uninstall.sh" "$RELEASE_DIR/"
print_success "已复制安装脚本"

# 复制 README
if [ -f "$PROJECT_ROOT/README.md" ]; then
    cp "$PROJECT_ROOT/README.md" "$RELEASE_DIR/"
    print_success "已复制 README"
fi

# 创建默认配置
cat > "$RELEASE_DIR/config/settings.json" << 'EOF'
{
  "backend": {
    "port": 5001,
    "host": "127.0.0.1",
    "auto_start": true
  },
  "api": {
    "provider": "kimi",
    "model": "moonshot-v1-8k"
  },
  "memory": {
    "enabled": true,
    "path": "~/.omnia/data/memory"
  },
  "ui": {
    "theme": "dark",
    "language": "zh-CN"
  }
}
EOF
print_success "已创建默认配置"

# 复制后端（如果存在）
if [ -f "$PROJECT_ROOT/dist/omnia-backend" ]; then
    cp "$PROJECT_ROOT/dist/omnia-backend" "$RELEASE_DIR/"
    print_success "已复制后端"
fi

print_success "发布包创建完成"
echo ""

# 完成
echo "========================================"
echo -e "${GREEN}构建完成！${NC}"
echo "========================================"
echo ""
echo "发布包位置: $RELEASE_DIR"
echo ""
echo "发布包内容:"
ls -la "$RELEASE_DIR"
echo ""
echo "安装方式:"
echo "  1. 将 release 目录复制到目标机器"
echo "  2. 运行 ./install.sh"
echo ""
