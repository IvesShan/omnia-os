#!/bin/bash
# Omnia 卸载脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="$HOME/.omnia"
BIN_DIR="$HOME/.local/bin"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Omnia AIOS 卸载程序           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# 检查是否已安装
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Omnia 未安装${NC}"
    exit 0
fi

# 确认卸载
echo -e "${YELLOW}即将卸载 Omnia AIOS${NC}"
echo "这将删除:"
echo "  - 应用程序: $INSTALL_DIR"
echo "  - 桌面快捷方式"
echo "  - 命令行入口"
echo ""
read -p "是否保留配置和数据文件？(Y/n): " -n 1 -r
echo

KEEP_DATA=true
if [[ $REPLY =~ ^[Nn]$ ]]; then
    KEEP_DATA=false
fi

# 停止后端服务
echo ""
echo -e "${YELLOW}[1/4]${NC} 停止后端服务..."
pkill -f "omnia-backend" 2>/dev/null || true
pkill -f "standalone_main.py" 2>/dev/null || true
echo -e "${GREEN}✓${NC} 后端服务已停止"

# 删除桌面快捷方式
echo ""
echo -e "${YELLOW}[2/4]${NC} 删除桌面快捷方式..."
rm -f "$HOME/.local/share/applications/omnia.desktop"
rm -f "$BIN_DIR/omnia"
echo -e "${GREEN}✓${NC} 快捷方式已删除"

# 删除应用程序
echo ""
echo -e "${YELLOW}[3/4]${NC} 删除应用程序..."
if [ "$KEEP_DATA" = true ]; then
    # 保留配置和数据
    rm -rf "$INSTALL_DIR/app"
    rm -rf "$INSTALL_DIR/backend"
    echo -e "${GREEN}✓${NC} 应用程序已删除（配置和数据已保留）"
else
    # 完全删除
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓${NC} 所有文件已删除"
fi

# 完成
echo ""
echo -e "${YELLOW}[4/4]${NC} 清理完成..."

if [ "$KEEP_DATA" = true ]; then
    echo ""
    echo -e "${GREEN}卸载完成！${NC}"
    echo ""
    echo "配置和数据已保留在: $INSTALL_DIR/config 和 $INSTALL_DIR/data"
    echo "如需完全删除，请运行: rm -rf $INSTALL_DIR"
else
    echo ""
    echo -e "${GREEN}卸载完成！${NC}"
    echo "所有文件已删除"
fi

echo ""
