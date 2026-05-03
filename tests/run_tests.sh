#!/bin/bash
# Omnia 测试运行脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================"
echo "  Omnia 测试框架"
echo "================================================"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    exit 1
fi

# 检查 pytest
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}安装 pytest...${NC}"
    pip install pytest pytest-cov
fi

# 解析参数
TEST_TYPE="${1:-all}"
COVERAGE=false

if [[ "$*" == *"--coverage"* ]]; then
    COVERAGE=true
fi

# 运行测试
echo -e "${YELLOW}运行测试...${NC}"
echo ""

if [ "$TEST_TYPE" = "all" ]; then
    if [ "$COVERAGE" = true ]; then
        python3 -m pytest tests/ -v --cov=src/omnia --cov-report=term-missing
    else
        python3 -m pytest tests/ -v
    fi
elif [ "$TEST_TYPE" = "memory" ]; then
    python3 -m pytest tests/test_memory*.py -v
elif [ "$TEST_TYPE" = "api" ]; then
    python3 -m pytest tests/test_web_server.py -v
else
    python3 -m pytest tests/ -k "$TEST_TYPE" -v
fi

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  ✅ 所有测试通过${NC}"
    echo -e "${GREEN}================================================${NC}"
else
    echo ""
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}  ❌ 测试失败${NC}"
    echo -e "${RED}================================================${NC}"
    exit 1
fi
