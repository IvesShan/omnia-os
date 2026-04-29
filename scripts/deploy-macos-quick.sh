#!/bin/bash
# Omnia macOS 一键部署 — 在目标 Mac 上直接运行
# 用法: bash deploy.sh [API_KEY]
# 例如: bash deploy.sh tp-你的小米key

set -e
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_KEY="${1:-}"

echo -e "${CYAN}🚀 Omnia 部署开始...${NC}"

# 1. 检查 Python3
if ! command -v python3 &>/dev/null; then
    echo "❌ 需要 Python3，请先安装: brew install python3"
    exit 1
fi
echo -e "✅ Python: $(python3 --version)"

# 2. 克隆仓库
DIR="$HOME/omnia-os"
if [ -d "$DIR" ]; then
    cd "$DIR" && git pull 2>/dev/null || true
else
    git clone https://github.com/shan/omnia-os.git "$DIR"
    cd "$DIR"
fi

# 3. 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install --upgrade pip -q
pip install flask flask-cors flask-socketio openai anthropic httpx chromadb sentence-transformers numpy scikit-learn python-dotenv pyyaml psutil -q 2>/dev/null || true

# 5. 配置
mkdir -p logs memory data
[ ! -f .env ] && cp .env.example .env 2>/dev/null || true

# 写入 API Key
if [ -n "$API_KEY" ]; then
    if grep -q "MIMO_API_KEY" .env 2>/dev/null; then
        sed -i '' "s/# MIMO_API_KEY=.*/MIMO_API_KEY=$API_KEY/" .env
    else
        echo "MIMO_API_KEY=$API_KEY" >> .env
    fi
    echo -e "✅ API Key 已配置"
fi

# 6. 启动
echo -e "${GREEN}✅ 部署完成！正在启动 Omnia...${NC}"
echo -e "🌐 访问: ${CYAN}http://localhost:5001${NC}"
echo ""

python -m src.omnia.web_server
