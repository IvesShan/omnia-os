#!/bin/bash
# Omnia Manager Tauri 应用安装脚本

set -e

echo "======================================"
echo "  Omnia Manager - Tauri 应用安装"
echo "======================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 路径
TAURI_DIR="$HOME//home/shan/omnia-os/omnia-os/tauri-app"
DEB_FILE="$TAURI_DIR/src-tauri/target/release/bundle/deb/Omnia Manager_1.0.0_amd64.deb"
EXEC_FILE="$TAURI_DIR/src-tauri/target/release/omnia-manager"

# 检查构建产物
if [ ! -f "$DEB_FILE" ]; then
    echo -e "${RED}错误: 找不到 DEB 包${NC}"
    echo "请先运行: npm run tauri build"
    exit 1
fi

if [ ! -f "$EXEC_FILE" ]; then
    echo -e "${RED}错误: 找不到可执行文件${NC}"
    echo "请先运行: npm run tauri build"
    exit 1
fi

echo -e "${GREEN}✓ 找到构建产物${NC}"
echo ""

# 选择安装方式
echo "请选择安装方式:"
echo "  1) 安装 DEB 包 (推荐)"
echo "  2) 创建桌面快捷方式 (无需 sudo)"
echo "  3) 两者都做"
echo ""
read -p "请输入选项 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}正在安装 DEB 包...${NC}"
        sudo dpkg -i "$DEB_FILE"
        echo -e "${GREEN}✓ DEB 包安装成功${NC}"
        echo ""
        echo "现在可以:"
        echo "  - 在应用菜单中找到 'Omnia Manager'"
        echo "  - 在终端运行 'omnia-manager'"
        ;;
    2)
        echo ""
        echo -e "${YELLOW}正在创建桌面快捷方式...${NC}"
        
        # 创建 .desktop 文件
        mkdir -p ~/.local/share/applications
        cat > ~/.local/share/applications/omnia-tauri.desktop << EOF
[Desktop Entry]
Name=Omnia Manager (Tauri)
Comment=Omnia Memory Palace Manager - Native Desktop App
Exec=$EXEC_FILE
Icon=omnia
Terminal=false
Type=Application
Categories=System;Utility;
StartupNotify=true
EOF
        
        chmod +x ~/.local/share/applications/omnia-tauri.desktop
        
        echo -e "${GREEN}✓ 桌面快捷方式创建成功${NC}"
        echo ""
        echo "现在可以:"
        echo "  - 按 Super 键，搜索 'Omnia Manager (Tauri)'"
        ;;
    3)
        echo ""
        echo -e "${YELLOW}正在安装 DEB 包...${NC}"
        sudo dpkg -i "$DEB_FILE"
        echo -e "${GREEN}✓ DEB 包安装成功${NC}"
        
        echo ""
        echo -e "${YELLOW}正在创建桌面快捷方式...${NC}"
        mkdir -p ~/.local/share/applications
        cat > ~/.local/share/applications/omnia-tauri.desktop << EOF
[Desktop Entry]
Name=Omnia Manager (Tauri)
Comment=Omnia Memory Palace Manager - Native Desktop App
Exec=$EXEC_FILE
Icon=omnia
Terminal=false
Type=Application
Categories=System;Utility;
StartupNotify=true
EOF
        
        chmod +x ~/.local/share/applications/omnia-tauri.desktop
        echo -e "${GREEN}✓ 桌面快捷方式创建成功${NC}"
        
        echo ""
        echo "安装完成！"
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo -e "${GREEN}  安装成功！${NC}"
echo "======================================"
echo ""
echo "启动方式:"
echo "  1. 应用菜单: 搜索 'Omnia Manager'"
echo "  2. 命令行: omnia-manager"
echo "  3. 直接运行: $EXEC_FILE"
echo ""
