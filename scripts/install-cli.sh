#!/bin/bash
# 安装 Omnia CLI 到系统

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/omnia-cli"

echo "📦 安装 Omnia CLI..."

# 确保 CLI 可执行
chmod +x "$CLI_SCRIPT"

# 创建符号链接到 ~/.local/bin
mkdir -p ~/.local/bin
ln -sf "$CLI_SCRIPT" ~/.local/bin/omnia

# 检查 ~/.local/bin 是否在 PATH 中
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "⚠️  ~/.local/bin 不在 PATH 中"
    echo ""
    echo "请将以下内容添加到你的 ~/.bashrc 或 ~/.zshrc:"
    echo ""
    echo '    export PATH="$HOME/.local/bin:$PATH"'
    echo ""
    echo "然后运行: source ~/.bashrc"
else
    echo "✓ 已安装到 ~/.local/bin/omnia"
    echo ""
    echo "现在可以使用: omnia status"
fi
