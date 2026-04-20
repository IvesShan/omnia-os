#!/bin/bash
# 构建干净的发布包（去除个人配置）

set -e

echo "🧹 清理个人配置..."
echo ""

# 定义要排除的文件
EXCLUDE_FILES=(
    "config/feishu.json"
    "config/feishu.json.omnia.bak"
    "config/feishu_config.json"
    "config/mcp_servers.json"
    ".env"
    ".env.omnia.bak"
    ".omnia"
    "logs"
    "data"
    "dist"
    "node_modules"
    ".pids"
    ".tmp_forge"
    ".tmp_skills"
    "*.log"
    "*.deb"
    "feishu_debug.log"
)

# 创建临时目录
RELEASE_DIR="omnia-os-release"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

echo "📦 复制核心文件..."

# 复制所有文件（排除个人配置）
rsync -av --progress \
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
    ./ "$RELEASE_DIR/"

echo ""
echo "📝 创建基础配置模板..."

# 创建基础配置模板
mkdir -p "$RELEASE_DIR/config"

cat > "$RELEASE_DIR/config/mcp_servers.json" << 'EOF'
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

cat > "$RELEASE_DIR/.env" << 'EOF'
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

echo ""
echo "✅ 创建首次启动引导..."
# 引导脚本会在下一步创建

echo ""
echo "📊 发布包统计："
echo "   文件数量: $(find "$RELEASE_DIR" -type f | wc -l)"
echo "   总大小: $(du -sh "$RELEASE_DIR" | cut -f1)"

echo ""
echo "🎉 发布包已构建: $RELEASE_DIR/"
echo ""
echo "下一步："
echo "  1. 测试首次启动引导: cd $RELEASE_DIR && ./scripts/first-run-wizard.sh"
echo "  2. 打包为压缩文件: tar -czf omnia-os-v1.0.tar.gz $RELEASE_DIR"
echo "  3. 复制到 U 盘或上传网盘"
