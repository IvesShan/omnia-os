#!/bin/bash
# Omnia 一键安装脚本
# 支持 Linux (deb/rpm/AppImage), macOS, Windows

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 Omnia 安装程序                             ║"
echo "║            永不遗忘的 AI 操作系统                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检测操作系统
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux*)     OS_TYPE="linux" ;;
    Darwin*)    OS_TYPE="macos" ;;
    CYGWIN*|MINGW*|MSYS*)    OS_TYPE="windows" ;;
    *)          echo "不支持的操作系统: $OS"; exit 1 ;;
esac

echo "检测到系统: $OS_TYPE ($ARCH)"

# 设置安装目录
if [ "$OS_TYPE" = "macos" ]; then
    INSTALL_DIR="$HOME/Applications/Omnia"
elif [ "$OS_TYPE" = "windows" ]; then
    INSTALL_DIR="$HOME/AppData/Local/Omnia"
else
    INSTALL_DIR="$HOME/.local/share/omnia"
fi

DATA_DIR="$HOME/.omnia"

echo "安装目录: $INSTALL_DIR"
echo "数据目录: $DATA_DIR"
echo ""

# 创建目录
mkdir -p "$INSTALL_DIR"
mkdir -p "$DATA_DIR/config"
mkdir -p "$DATA_DIR/data/memory"
mkdir -p "$DATA_DIR/data/agents"
mkdir -p "$DATA_DIR/logs"

# 复制文件
echo "正在复制文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 复制 AppImage (Linux)
if [ "$OS_TYPE" = "linux" ]; then
    if [ -f "$SCRIPT_DIR/Omnia_0.1.0_amd64.AppImage" ]; then
        cp "$SCRIPT_DIR/Omnia_0.1.0_amd64.AppImage" "$INSTALL_DIR/Omnia"
        chmod +x "$INSTALL_DIR/Omnia"
        echo "✓ 前端应用已安装"
    else
        echo "⚠ 未找到 AppImage 文件"
    fi
fi

# 复制后端
if [ -f "$SCRIPT_DIR/backend/omnia-backend" ]; then
    cp "$SCRIPT_DIR/backend/omnia-backend" "$INSTALL_DIR/backend"
    chmod +x "$INSTALL_DIR/backend"
    echo "✓ 后端服务已安装"
elif [ -d "$SCRIPT_DIR/backend" ]; then
    # 开发环境：复制 Python 源码
    cp -r "$SCRIPT_DIR/backend" "$INSTALL_DIR/backend-src"
    echo "✓ 后端源码已复制（需要 Python 环境）"
fi

# 创建默认配置
if [ ! -f "$DATA_DIR/config/settings.json" ]; then
    cat > "$DATA_DIR/config/settings.json" << 'JSONEOF'
{
  "api_provider": "kimi",
  "api_key": "",
  "model_name": "moonshot-v1-8k",
  "backend_port": 5001,
  "log_level": "info",
  "auto_start_backend": true
}
JSONEOF
    echo "✓ 默认配置已创建"
fi

# 创建桌面快捷方式 (Linux)
if [ "$OS_TYPE" = "linux" ]; then
    DESKTOP_FILE="$HOME/.local/share/applications/omnia.desktop"
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    cat > "$DESKTOP_FILE" << DESKTOPEOF
[Desktop Entry]
Name=Omnia
Comment=永不遗忘的 AI 操作系统
Exec="$INSTALL_DIR/Omnia"
Icon=omnia
Terminal=false
Type=Application
Categories=Utility;AI;
DESKTOPEOF
    echo "✓ 桌面快捷方式已创建"
fi

# 创建卸载脚本
cat > "$INSTALL_DIR/uninstall.sh" << 'UNINSTALLEOF'
#!/bin/bash
echo "正在卸载 Omnia..."
rm -rf "$HOME/.local/share/omnia"
rm -rf "$HOME/Applications/Omnia"
rm -f "$HOME/.local/share/applications/omnia.desktop"
echo "卸载完成。数据目录 ~/.omnia 已保留。"
UNINSTALLEOF
chmod +x "$INSTALL_DIR/uninstall.sh"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    安装完成！                              ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  启动方式:                                                 ║"
echo "║    Linux:   $INSTALL_DIR/Omnia"
echo "║    或从应用菜单搜索 'Omnia'                                 ║"
echo "║                                                            ║"
echo "║  配置文件: $DATA_DIR/config/settings.json"
echo "║  日志目录: $DATA_DIR/logs"
echo "║                                                            ║"
echo "║  卸载:     $INSTALL_DIR/uninstall.sh"
echo "╚════════════════════════════════════════════════════════════╝"
