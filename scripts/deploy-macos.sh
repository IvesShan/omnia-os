#!/bin/bash
# ============================================================
# Omnia 一键部署脚本 (macOS)
# 用法: curl -sL <url>/deploy-macos.sh | bash
# 或者: chmod +x deploy-macos.sh && ./deploy-macos.sh
# ============================================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║        Omnia 一键部署 (macOS)            ║"
echo "║        AI Operating System               ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# 1. 检查环境
# ============================================================
echo -e "${YELLOW}[1/7] 检查环境...${NC}"

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "  ✅ Python: $PYTHON_VERSION"
else
    echo -e "  ❌ Python3 未安装"
    echo -e "  ${YELLOW}正在安装 Python3...${NC}"
    if command -v brew &> /dev/null; then
        brew install python3
    else
        echo -e "  ${RED}请先安装 Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
        exit 1
    fi
fi

# 检查 pip
if command -v pip3 &> /dev/null; then
    echo -e "  ✅ pip3: $(pip3 --version 2>&1 | head -1)"
else
    echo -e "  ❌ pip3 未安装，正在安装..."
    python3 -m ensurepip --upgrade
fi

# 检查 git
if command -v git &> /dev/null; then
    echo -e "  ✅ Git: $(git --version)"
else
    echo -e "  ❌ Git 未安装"
    exit 1
fi

# ============================================================
# 2. 克隆仓库
# ============================================================
INSTALL_DIR="$HOME/omnia-os"
echo -e "\n${YELLOW}[2/7] 克隆 Omnia 仓库到 ${INSTALL_DIR}...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "  ⚠️  目录已存在，更新中..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || echo "  ⚠️  git pull 失败，使用现有代码"
else
    git clone https://github.com/shan/omnia-os.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo -e "  ✅ 仓库就绪: $INSTALL_DIR"

# ============================================================
# 3. 创建虚拟环境
# ============================================================
echo -e "\n${YELLOW}[3/7] 创建 Python 虚拟环境...${NC}"

if [ -d "venv" ]; then
    echo -e "  ⚠️  虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo -e "  ✅ 虚拟环境已创建"
fi

source venv/bin/activate
echo -e "  ✅ 已激活虚拟环境"

# ============================================================
# 4. 安装依赖
# ============================================================
echo -e "\n${YELLOW}[4/7] 安装依赖...${NC}"

pip install --upgrade pip -q
pip install -r requirements.txt -q 2>/dev/null || {
    echo -e "  ⚠️  requirements.txt 安装失败，尝试手动安装核心依赖..."
    pip install flask flask-cors flask-socketio \
        openai anthropic httpx \
        chromadb sentence-transformers \
        numpy scikit-learn \
        python-dotenv pyyaml \
        psutil -q
}

echo -e "  ✅ 依赖安装完成"

# ============================================================
# 5. 配置环境变量
# ============================================================
echo -e "\n${YELLOW}[5/7] 配置环境变量...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || {
        cat > .env << 'ENVEOF'
# Omnia 环境变量配置
# 请填入你的 API Key

# DeepSeek (默认)
# DEEPSEEK_API_KEY=your-key-here

# 小米 MiMo Token Plan
# MIMO_API_KEY=tp-your-key-here

# Kimi (Moonshot)
# KIMI_API_KEY=your-key-here

# OpenAI
# OPENAI_API_KEY=your-key-here

# Anthropic
# ANTHROPIC_API_KEY=your-key-here

# WebUI 端口
OMNIA_WEBUI_PORT=5001
ENVEOF
    }
    echo -e "  ✅ .env 已创建，请编辑填入 API Key"
else
    echo -e "  ⚠️  .env 已存在，跳过"
fi

# ============================================================
# 6. 创建日志目录
# ============================================================
echo -e "\n${YELLOW}[6/7] 创建必要目录...${NC}"
mkdir -p logs memory data
echo -e "  ✅ 目录创建完成"

# ============================================================
# 7. 启动 Omnia
# ============================================================
echo -e "\n${YELLOW}[7/7] 启动 Omnia...${NC}"

# 检查端口是否被占用
if lsof -i :5001 &> /dev/null; then
    echo -e "  ⚠️  端口 5001 已被占用，正在释放..."
    kill $(lsof -t -i :5001) 2>/dev/null || true
    sleep 1
fi

echo -e "  ✅ 启动 WebUI 服务..."
echo ""

# ============================================================
# 完成
# ============================================================
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════╗"
echo "║        ✅ Omnia 部署完成！               ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  📁 安装目录: ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "  ${YELLOW}下一步:${NC}"
echo -e "  1. 编辑 .env 文件，填入 API Key:"
echo -e "     ${CYAN}nano $INSTALL_DIR/.env${NC}"
echo ""
echo -e "  2. 启动 Omnia:"
echo -e "     ${CYAN}cd $INSTALL_DIR && source venv/bin/activate && python -m src.omnia.web_server${NC}"
echo ""
echo -e "  3. 打开浏览器访问:"
echo -e "     ${CYAN}http://localhost:5001${NC}"
echo ""
echo -e "  ${YELLOW}后台运行:${NC}"
echo -e "  ${CYAN}cd $INSTALL_DIR && source venv/bin/activate && nohup python -m src.omnia.web_server > logs/omnia.log 2>&1 &${NC}"
echo ""
