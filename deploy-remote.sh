#!/bin/bash
# ============================================================
# Omnia Remote Deployment Script
# For macOS systems
# ============================================================

set -e

echo "🚀 Starting Omnia Deployment..."
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Check system
echo -e "\n${YELLOW}[1/7] Checking system...${NC}"
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This script is for macOS only${NC}"
    exit 1
fi

# Step 2: Install Homebrew if needed
echo -e "\n${YELLOW}[2/7] Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo -e "${GREEN}✓ Homebrew installed${NC}"
fi

# Step 3: Install Python 3.11+
echo -e "\n${YELLOW}[3/7] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    brew install python@3.11
else
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION installed${NC}"
fi

# Step 4: Install Git
echo -e "\n${YELLOW}[4/7] Checking Git...${NC}"
if ! command -v git &> /dev/null; then
    echo "Installing Git..."
    brew install git
else
    echo -e "${GREEN}✓ Git installed${NC}"
fi

# Step 5: Clone Omnia
echo -e "\n${YELLOW}[5/7] Cloning Omnia...${NC}"
INSTALL_DIR="$HOME/omnia-os"
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists. Updating..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning from GitHub..."
    # 如果没有 GitHub 仓库，从本地复制
    # git clone https://github.com/your-repo/omnia-os.git "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Step 6: Create virtual environment and install dependencies
echo -e "\n${YELLOW}[6/7] Installing dependencies...${NC}"
python3 -m venv venv
source venv/bin/activate

# 创建 requirements.txt 如果不存在
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'EOF'
flask>=3.0.0
flask-cors>=4.0.0
openai>=1.0.0
anthropic>=0.18.0
requests>=2.31.0
python-dotenv>=1.0.0
EOF
fi

pip install --upgrade pip
pip install -r requirements.txt

# Step 7: Create .env file
echo -e "\n${YELLOW}[7/7] Creating configuration...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# ===========================================
# Omnia Configuration
# ===========================================

# WebUI Port
OMNIA_WEBUI_PORT=5001

# API Keys (choose one or more)
# DEEPSEEK_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
# MIMO_API_KEY=your_key_here

# Model Mode: cloud or local
OMNIA_MODEL_MODE=cloud

# Memory Settings
OMNIA_MEMORY_PATH=./memory
OMNIA_SESSION_PATH=./sessions

# Logging
OMNIA_LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Create necessary directories
mkdir -p memory sessions logs

# Create start script
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export FLASK_APP=src/omnia/web_server.py
python -m flask run --host=0.0.0.0 --port=${OMNIA_WEBUI_PORT:-5001}
EOF
chmod +x start.sh

# Create systemd-like launch script for macOS
cat > start-daemon.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
nohup python -m flask run --host=0.0.0.0 --port=${OMNIA_WEBUI_PORT:-5001} > logs/omnia.log 2>&1 &
echo $! > omnia.pid
echo "Omnia started. PID: $(cat omnia.pid)"
echo "Logs: tail -f logs/omnia.log"
EOF
chmod +x start-daemon.sh

echo ""
echo "================================"
echo -e "${GREEN}✅ Omnia Deployment Complete!${NC}"
echo "================================"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file and add your API key:"
echo "   nano .env"
echo ""
echo "2. Start Omnia:"
echo "   ./start.sh"
echo ""
echo "3. Open browser:"
echo "   http://localhost:5001"
echo ""
echo "================================"
