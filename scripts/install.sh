#!/bin/bash
# Omnia 一键安装脚本

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

# 脚本所在目录（发布包目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Omnia AIOS 安装程序           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
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
    echo "正在卸载旧版本..."
    rm -rf "$INSTALL_DIR"
fi

# 创建目录结构
echo ""
echo -e "${YELLOW}[1/5]${NC} 创建目录结构..."
mkdir -p "$INSTALL_DIR"/{app,backend,config,data/{memory,logs},agents}
mkdir -p "$BIN_DIR"
mkdir -p "$HOME/.local/share/applications"
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_success "目录创建完成"

# 复制应用程序
echo ""
echo -e "${YELLOW}[2/5]${NC} 复制应用程序..."

# 复制 AppImage
APPIMAGE_FILE=$(find "$SCRIPT_DIR" -name "*.AppImage" 2>/dev/null | head -n 1)
if [ -n "$APPIMAGE_FILE" ]; then
    cp "$APPIMAGE_FILE" "$INSTALL_DIR/app/Omnia.AppImage"
    chmod +x "$INSTALL_DIR/app/Omnia.AppImage"
    print_success "AppImage 已复制"
else
    echo -e "${RED}✗ 未找到 AppImage 文件${NC}"
    exit 1
fi

# 复制图标
ICON_FILE=$(find "$SCRIPT_DIR" -name "icon.png" 2>/dev/null | head -n 1)
if [ -n "$ICON_FILE" ]; then
    cp "$ICON_FILE" "$INSTALL_DIR/app/icon.png"
    print_success "图标已复制"
else
    # 尝试从 src-tauri/icons 复制
    if [ -f "$SCRIPT_DIR/../src-tauri/icons/icon.png" ]; then
        cp "$SCRIPT_DIR/../src-tauri/icons/icon.png" "$INSTALL_DIR/app/icon.png"
        print_success "图标已复制 (从源码目录)"
    else
        echo -e "${YELLOW}! 未找到图标文件，将使用默认图标${NC}"
    fi
fi

# 复制后端
BACKEND_FILE=$(find "$SCRIPT_DIR" -name "omnia-backend" -o -name "omnia-backend.exe" 2>/dev/null | head -n 1)
if [ -n "$BACKEND_FILE" ]; then
    cp "$BACKEND_FILE" "$INSTALL_DIR/backend/omnia-backend"
    chmod +x "$INSTALL_DIR/backend/omnia-backend"
    print_success "后端已复制"
else
    echo -e "${YELLOW}! 未找到独立后端，将使用 Python 运行${NC}"
fi

# 复制配置
if [ -d "$SCRIPT_DIR/config" ]; then
    cp -r "$SCRIPT_DIR/config/"* "$INSTALL_DIR/config/" 2>/dev/null || true
    print_success "配置文件已复制"
fi

# 创建默认配置
echo ""
echo -e "${YELLOW}[3/5]${NC} 创建配置文件..."

# 创建 settings.json
if [ ! -f "$INSTALL_DIR/config/settings.json" ]; then
    cat > "$INSTALL_DIR/config/settings.json" << 'EOF'
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
    print_success "settings.json 已创建"
fi

# 创建 API 密钥文件
if [ ! -f "$INSTALL_DIR/config/api_keys.json" ]; then
    cat > "$INSTALL_DIR/config/api_keys.json" << 'EOF'
{
  "kimi": "",
  "baidu": "",
  "openai": ""
}
EOF
    print_success "api_keys.json 已创建"
fi

# 创建启动脚本
echo ""
echo -e "${YELLOW}[4/5]${NC} 创建启动脚本..."

cat > "$INSTALL_DIR/app/start.sh" << 'EOF'
#!/bin/bash
# Omnia 启动脚本

OMNIA_DIR="$HOME/.omnia"

# 启动后端
if [ -f "$OMNIA_DIR/backend/omnia-backend" ]; then
    "$OMNIA_DIR/backend/omnia-backend" &
else
    # 使用 Python 运行
    if command -v python3 &> /dev/null; then
        python3 "$OMNIA_DIR/backend/standalone_main.py" &
    fi
fi

# 启动前端
"$OMNIA_DIR/app/Omnia.AppImage" "$@"
EOF

chmod +x "$INSTALL_DIR/app/start.sh"
print_success "启动脚本已创建"

# 创建桌面快捷方式
DESKTOP_FILE="$HOME/.local/share/applications/omnia.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Omnia AIOS
Comment=AI Operating System
Exec=$INSTALL_DIR/app/start.sh
Icon=$INSTALL_DIR/app/icon.png
Terminal=false
Type=Application
Categories=Development;Utility;
StartupNotify=true
EOF

print_success "桌面快捷方式已创建"

# 更新桌面数据库
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    print_success "桌面数据库已更新"
fi

# 创建命令行入口
ln -sf "$INSTALL_DIR/app/start.sh" "$BIN_DIR/omnia"
print_success "命令行入口已创建: omnia"

# 添加到 PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo -e "${YELLOW}提示: $BIN_DIR 不在 PATH 中${NC}"
    echo "请运行以下命令添加到 PATH:"
    echo ""
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "  source ~/.bashrc"
    echo ""
fi

# 完成
echo ""
echo -e "${YELLOW}[5/5]${NC} 验证安装..."

# 验证
if [ -f "$INSTALL_DIR/app/Omnia.AppImage" ]; then
    print_success "应用程序已安装"
fi

if [ -f "$INSTALL_DIR/app/icon.png" ]; then
    print_success "图标已安装"
fi

if [ -f "$INSTALL_DIR/backend/omnia-backend" ]; then
    print_success "后端服务已安装"
fi

if [ -f "$INSTALL_DIR/config/settings.json" ]; then
    print_success "配置文件已创建"
fi

if [ -f "$DESKTOP_FILE" ]; then
    print_success "桌面快捷方式已创建"
fi

# 完成
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          安装完成！                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "安装位置: $INSTALL_DIR"
echo ""
echo "启动方式:"
echo "  1. 桌面快捷方式: 在应用菜单中找到 'Omnia AIOS'"
echo "  2. 命令行: omnia"
echo "  3. 直接运行: $INSTALL_DIR/app/start.sh"
echo ""
echo "配置文件位置: $INSTALL_DIR/config/"
echo "数据文件位置: $INSTALL_DIR/data/"
echo ""
echo "首次使用请先配置 API 密钥:"
echo "  编辑 $INSTALL_DIR/config/api_keys.json"
echo ""
