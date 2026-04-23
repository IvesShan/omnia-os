#!/bin/bash
# Omnia Linux 快速安装脚本

set -e

DEB_FILE="src-tauri/target/release/bundle/deb/Omnia_1.1.1_amd64.deb"

echo "╔════════════════════════════════════════╗"
echo "║     Omnia AIOS - Linux 安装向导        ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检查是否在项目目录
if [ ! -f "$DEB_FILE" ]; then
    echo "❌ 错误：找不到 deb 包"
    echo "   请确保在 omnia-os 项目根目录运行此脚本"
    echo "   或者先运行: npm run tauri build"
    exit 1
fi

echo "📦 找到安装包: $DEB_FILE"
echo ""

# 检查是否已安装
if dpkg -l | grep -q omnia; then
    echo "⚠️  检测到已安装 Omnia，将进行升级..."
    echo ""
fi

# 安装
echo "🔧 正在安装..."
sudo dpkg -i "$DEB_FILE" || {
    echo ""
    echo "⚠️  依赖问题，正在修复..."
    sudo apt-get install -f -y
}

echo ""
echo "✅ 安装完成！"
echo ""

# 检查用户数据目录
if [ ! -d "$HOME/.omnia" ]; then
    echo "📁 创建用户数据目录..."
    mkdir -p "$HOME/.omnia/"{config,data,logs}
    echo "   ~/.omnia/ 已创建"
    echo ""
fi

echo "🚀 启动方式："
echo "   • 命令行: omnia-desktop"
echo "   • 桌面菜单: 应用程序 → Omnia"
echo ""
echo "⚙️  首次使用请配置 API Key："
echo "   1. 启动 Omnia"
echo "   2. 点击右上角设置图标"
echo "   3. 选择 API 提供商并输入 Key"
echo ""
echo "📖 更多信息: cat INSTALL_LINUX.md"
echo ""
