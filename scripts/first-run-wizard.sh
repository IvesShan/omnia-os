#!/bin/bash
# Omnia 首次启动引导向导
# 帮助新用户完成初始配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 欢迎横幅
clear
echo -e "${PURPLE}"
cat << "EOF"
  ____                  _   _           
 / __ \                | | | |          
| |  | |_ __   ___ _ __| |_| | ___ _ __ 
| |  | | '_ \ / _ \ '__| __| |/ _ \ '__|
| |__| | |_) |  __/ |  | |_| |  __/ |   
 \____/| .__/ \___|_|   \__|_|\___|_|   
       | |                              
       |_|   - 你的 AI 操作系统
EOF
echo -e "${NC}"
echo ""
echo -e "${CYAN}欢迎使用 Omnia！${NC}"
echo -e "${CYAN}让我们开始配置你的个人 AI 助手...${NC}"
echo ""
echo "按 Enter 继续..."
read

# 步骤 1: 检测系统环境
echo -e "\n${YELLOW}[步骤 1/5] 检测系统环境...${NC}"
echo ""

OS_TYPE=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="Mac"
    echo -e "  ${GREEN}✓${NC} 检测到 macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="Linux"
    if [ -f /etc/debian_version ]; then
        echo -e "  ${GREEN}✓${NC} 检测到 Debian/Ubuntu"
    elif [ -f /etc/redhat-release ]; then
        echo -e "  ${GREEN}✓${NC} 检测到 RedHat/CentOS"
    fi
else
    echo -e "  ${RED}✗${NC} 不支持的系统: $OSTYPE"
    exit 1
fi

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"
else
    echo -e "  ${RED}✗${NC} 未安装 Python 3"
    echo -e "  ${YELLOW}请先安装 Python 3.8+${NC}"
    exit 1
fi

# 检查 Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "  ${GREEN}✓${NC} Node.js $NODE_VERSION"
else
    echo -e "  ${RED}✗${NC} 未安装 Node.js"
    echo -e "  ${YELLOW}请先安装 Node.js 18+${NC}"
    exit 1
fi

echo ""

# 步骤 2: 配置 API Key
echo -e "${YELLOW}[步骤 2/5] 配置 LLM API Key...${NC}"
echo ""
echo -e "Omnia 需要 LLM API 才能运行。"
echo -e "支持的 API 提供商："
echo -e "  ${CYAN}1.${NC} OpenAI"
echo -e "  ${CYAN}2.${NC} DeepSeek"
echo -e "  ${CYAN}3.${NC} 其他 OpenAI 兼容 API"
echo ""
echo -n "选择 API 提供商 [1-3]: "
read API_CHOICE

case $API_CHOICE in
    1)
        API_NAME="OpenAI"
        DEFAULT_BASE="https://api.openai.com/v1"
        ;;
    2)
        API_NAME="DeepSeek"
        DEFAULT_BASE="https://api.deepseek.com/v1"
        ;;
    3)
        API_NAME="自定义"
        echo -n "请输入 API Base URL: "
        read DEFAULT_BASE
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "配置 ${CYAN}$API_NAME${NC} API..."
echo -n "请输入 API Key: "
read -s API_KEY
echo ""

if [ -z "$API_KEY" ]; then
    echo -e "${RED}API Key 不能为空${NC}"
    exit 1
fi

# 写入 .env 文件
cat > .env << EOF
# Omnia 环境配置
# 自动生成于 $(date)

# LLM API
OPENAI_API_KEY=$API_KEY
OPENAI_BASE_URL=$DEFAULT_BASE

# 飞书配置（可选）
FEISHU_APP_ID=
FEISHU_APP_SECRET=

# 其他配置
LOG_LEVEL=INFO
EOF

echo -e "${GREEN}✓${NC} API 配置已保存"
echo ""

# 步骤 3: 配置用户信息
echo -e "${YELLOW}[步骤 3/5] 配置用户信息...${NC}"
echo ""
echo -n "你的名字是？: "
read USER_NAME

if [ -z "$USER_NAME" ]; then
    USER_NAME="用户"
fi

echo -n "你的职业或兴趣？（可选）: "
read USER_INFO

# 创建用户配置文件
mkdir -p config
cat > config/user_profile.json << EOF
{
  "name": "$USER_NAME",
  "info": "$USER_INFO",
  "created_at": "$(date -Iseconds)",
  "version": "1.0"
}
EOF

echo -e "${GREEN}✓${NC} 用户信息已保存"
echo ""

# 步骤 4: 安装依赖
echo -e "${YELLOW}[步骤 4/5] 安装依赖...${NC}"
echo ""

echo -e "  ${CYAN}→${NC} 安装 Python 依赖..."
if [ -f requirements.txt ]; then
    pip3 install -q -r requirements.txt
    echo -e "  ${GREEN}✓${NC} Python 依赖已安装"
else
    echo -e "  ${YELLOW}⚠${NC} 未找到 requirements.txt"
fi

echo -e "  ${CYAN}→${NC} 安装 Node.js 依赖..."
if [ -f package.json ]; then
    npm install --silent
    echo -e "  ${GREEN}✓${NC} Node.js 依赖已安装"
else
    echo -e "  ${YELLOW}⚠${NC} 未找到 package.json"
fi

echo ""

# 步骤 5: 创建启动命令
echo -e "${YELLOW}[步骤 5/5] 创建启动命令...${NC}"
echo ""

# 创建快捷启动脚本
cat > omnia-start << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
python3 scripts/start_daemon.py
EOF
chmod +x omnia-start

echo -e "${GREEN}✓${NC} 已创建启动命令: ./omnia-start"
echo ""

# 完成
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   🎉 配置完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "现在你可以："
echo ""
echo -e "  ${CYAN}1. 启动 Omnia (命令行模式):${NC}"
echo -e "     ./omnia-start"
echo ""
echo -e "  ${CYAN}2. 启动桌面应用:${NC}"
echo -e "     npm run tauri dev"
echo ""
echo -e "  ${CYAN}3. 查看文档:${NC}"
echo -e "     cat README_FOR_USER.md"
echo ""
echo -e "${PURPLE}Omnia 会记住你的一切。${NC}"
echo -e "${PURPLE}从现在开始，让它陪伴你成长。${NC}"
echo ""
