#!/bin/bash
# 打包 Omnia 为 U 盘可拷贝的发布包
# 包含所有功能 + 基础配置 + 首次启动引导

set -e

VERSION=${1:-"1.0"}
PACKAGE_NAME="omnia-os-v${VERSION}"
ARCHIVE_NAME="${PACKAGE_NAME}.tar.gz"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📦 Omnia 发布包打包工具"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 步骤 1: 清理旧的构建
echo "🧹 [1/5] 清理旧构建..."
rm -rf "$PACKAGE_NAME"
rm -f "$ARCHIVE_NAME"
echo "   ✓ 清理完成"
echo ""

# 步骤 2: 复制核心文件（排除个人配置）
echo "📦 [2/5] 复制核心文件..."
mkdir -p "$PACKAGE_NAME"

rsync -a --progress \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='.omnia' \
    --exclude='.pids' \
    --exclude='.tmp_forge' \
    --exclude='.tmp_skills' \
    --exclude='logs' \
    --exclude='data' \
    --exclude='*.log' \
    --exclude='*.deb' \
    --exclude='feishu_debug.log' \
    --exclude='config/feishu.json' \
    --exclude='config/feishu.json.omnia.bak' \
    --exclude='config/feishu_config.json' \
    --exclude='config/mcp_servers.json' \
    --exclude='.env' \
    --exclude='.env.omnia.bak' \
    --exclude='.git' \
    --exclude='omnia-os-release' \
    --exclude='*.tar.gz' \
    ./ "$PACKAGE_NAME/"

echo "   ✓ 文件复制完成"
echo ""

# 步骤 3: 创建基础配置模板
echo "📝 [3/5] 创建基础配置模板..."

mkdir -p "$PACKAGE_NAME/config"

# MCP 基础配置
cat > "$PACKAGE_NAME/config/mcp_servers.json" << 'EOF'
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "mcp_server_memory"],
      "env": {}
    }
  }
}
EOF

# .env 模板
cat > "$PACKAGE_NAME/.env" << 'EOF'
# Omnia 环境配置
# 请在首次启动时填写你的 API Keys

# LLM API（必填）
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 飞书配置（可选）
FEISHU_APP_ID=
FEISHU_APP_SECRET=

# 其他配置
LOG_LEVEL=INFO
EOF

echo "   ✓ 配置模板已创建"
echo ""

# 步骤 4: 设置权限
echo "🔐 [4/5] 设置执行权限..."
chmod +x "$PACKAGE_NAME/scripts/first-run-wizard.sh"
chmod +x "$PACKAGE_NAME/scripts/local-install.sh"
chmod +x "$PACKAGE_NAME/start.sh"
chmod +x "$PACKAGE_NAME/start-desktop.sh"
echo "   ✓ 权限设置完成"
echo ""

# 步骤 5: 打包压缩
echo "🗜️  [5/5] 打包压缩..."
tar -czf "$ARCHIVE_NAME" "$PACKAGE_NAME"

# 统计信息
TOTAL_SIZE=$(du -sh "$PACKAGE_NAME" | cut -f1)
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)
FILE_COUNT=$(find "$PACKAGE_NAME" -type f | wc -l)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 打包完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 发布包信息："
echo "   版本:     v${VERSION}"
echo "   文件数:   ${FILE_COUNT}"
echo "   原始大小: ${TOTAL_SIZE}"
echo "   压缩大小: ${ARCHIVE_SIZE}"
echo ""
echo "📦 文件位置："
echo "   文件夹:   ${PACKAGE_NAME}/"
echo "   压缩包:   ${ARCHIVE_NAME}"
echo ""
echo "🚀 使用方法："
echo ""
echo "   1. 复制到 U 盘："
echo "      cp ${ARCHIVE_NAME} /media/usb/"
echo ""
echo "   2. 在其他电脑解压："
echo "      tar -xzf ${ARCHIVE_NAME}"
echo ""
echo "   3. 首次启动："
echo "      cd ${PACKAGE_NAME}"
echo "      ./scripts/first-run-wizard.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
