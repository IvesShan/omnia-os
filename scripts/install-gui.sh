#!/bin/bash
# Omnia GUI 安装脚本
# 创建桌面快捷方式和应用菜单项

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_SCRIPT="$SCRIPT_DIR/omnia-gui.py"

echo "=== Omnia GUI 安装 ==="
echo

# 1. 确保 GUI 脚本可执行
chmod +x "$GUI_SCRIPT"
echo "✓ GUI 脚本已设置为可执行"

# 2. 创建图标（使用 emoji 作为图标）
ICON_DIR="$HOME/.local/share/icons"
mkdir -p "$ICON_DIR"

# 创建一个简单的 SVG 图标
cat > "$ICON_DIR/omnia.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <circle cx="64" cy="64" r="60" fill="#4A90E2"/>
  <text x="64" y="80" font-size="60" text-anchor="middle" fill="white">O</text>
</svg>
EOF
echo "✓ 图标已创建: $ICON_DIR/omnia.svg"

# 3. 创建桌面快捷方式
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/omnia.desktop" << EOF
[Desktop Entry]
Version=1.0
Name=Omnia Manager
Name[zh_CN]=Omnia 管理器
Comment=Manage Omnia AI Operating System
Comment[zh_CN]=管理 Omnia AI 操作系统
Exec=python3 "$GUI_SCRIPT"
Icon=omnia
Terminal=false
Type=Application
Categories=System;Settings;
StartupNotify=true
EOF

echo "✓ 桌面快捷方式已创建: $DESKTOP_DIR/omnia.desktop"

# 4. 更新桌面数据库
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    echo "✓ 桌面数据库已更新"
fi

# 5. 创建快速启动命令
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/omnia-gui" << EOF
#!/bin/bash
python3 "$GUI_SCRIPT" "\$@"
EOF

chmod +x "$BIN_DIR/omnia-gui"
echo "✓ 命令已创建: omnia-gui"

# 6. 检查 PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo
    echo "⚠️  警告: $BIN_DIR 不在 PATH 中"
    echo "请添加以下内容到 ~/.bashrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
    echo "然后运行: source ~/.bashrc"
fi

echo
echo "=== 安装完成 ==="
echo
echo "使用方式:"
echo "  1. 在应用菜单中搜索 'Omnia Manager'"
echo "  2. 或运行命令: omnia-gui"
echo "  3. 或直接运行: python3 $GUI_SCRIPT"
echo
