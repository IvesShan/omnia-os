#!/bin/bash
# ============================================================
# Omnia 商业版构建脚本
# 功能：代码混淆 + Nuitka 打包 + 签名
# ============================================================

set -e

echo "============================================"
echo "  Omnia Commercial Build v4.0"
echo "============================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查依赖
check_dep() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}❌ 缺少依赖: $1${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ $1 已安装${NC}"
}

echo "📋 检查构建依赖..."
check_dep python3
check_dep pip3

# 检查 PyArmor（可选，用于代码混淆）
HAS_PYARMOR=false
if command -v pyarmor &> /dev/null; then
    HAS_PYARMOR=true
    echo -e "${GREEN}✅ PyArmor 已安装 - 将启用代码加密${NC}"
else
    echo -e "${YELLOW}⚠️  PyArmor 未安装 - 跳过代码加密${NC}"
    echo "   安装命令: pip install pyarmor"
fi

# 检查 Nuitka
HAS NUITKA=false
if python3 -c "import nuitka" 2>/dev/null; then
    HAS NUITKA=true
    echo -e "${GREEN}✅ Nuitka 已安装${NC}"
else
    echo -e "${YELLOW}⚠️  Nuitka 未安装 - 将使用 PyInstaller${NC}"
fi

echo ""
echo "============================================"

# 步骤 1: 生成完整性签名
echo ""
echo "🔐 步骤 1: 生成代码完整性签名..."
python3 src/omnia/integrity.py sign
echo -e "${GREEN}✅ 签名生成完成${NC}"

# 步骤 2: 代码混淆（如果 PyArmor 可用）
if [ "$HAS_PYARMOR" = true ]; then
    echo ""
    echo "🔒 步骤 2: PyArmor 代码加密..."
    echo "   加密 src/omnia/ 核心模块..."
    pyarmor gen \
        --output dist/protected \
        --obf-code 2 \
        --obf-mod 2 \
        --exclude "web" \
        --exclude "templates" \
        --exclude "seeds" \
        --exclude "tools" \
        --exclude "__pycache__" \
        --restrict 1 \
        src/omnia/
    echo -e "${GREEN}✅ 代码加密完成${NC}"
    PROTECTED_SRC="dist/protected"
else
    echo ""
    echo "⏭️  步骤 2: 跳过代码加密（PyArmor 未安装）"
    PROTECTED_SRC="src"
fi

# 步骤 3: 打包（Nuitka 或 PyInstaller）
echo ""
echo "📦 步骤 3: 打包可执行文件..."

if [ "$HAS NUITKA" = true ]; then
    echo "   使用 Nuitka 打包..."
    python3 -m nuitka \
        --standalone \
        --onefile \
        --output-filename=omnia \
        --include-package=src.omnia \
        --include-package=fastapi \
        --include-package=uvicorn \
        --include-package=pydantic \
        --include-package=jinja2 \
        --include-data-dir=web=web \
        --include-data-dir=seeds=seeds \
        --include-data-dir=templates=templates \
        --noinclude-default-mode=disable \
        --assume-yes-for-downloads \
        --company-name="Omnia AI" \
        --product-name="Omnia AIOS" \
        --file-version="4.0.0" \
        --copyright="Copyright 2026 Omnia AI" \
        --windows-icon-from-ico=src-tauri/icons/icon.ico \
        backend/standalone_main.py
else
    echo "   使用 PyInstaller 打包..."
    pyinstaller \
        --onefile \
        --name omnia \
        --add-data "web:web" \
        --add-data "seeds:seeds" \
        --add-data "src/omnia:src/omnia" \
        --hidden-import fastapi \
        --hidden-import uvicorn \
        --hidden-import pydantic \
        --hidden-import jinja2 \
        --noconfirm \
        --clean \
        backend/standalone_main.py
fi

echo -e "${GREEN}✅ 打包完成${NC}"

# 步骤 4: 生成版本信息
echo ""
echo "📝 步骤 4: 生成版本信息..."
VERSION="4.0.0"
BUILD_TIME=$(date "+%Y-%m-%d %H:%M:%S")
cat > dist/VERSION << EOF
$VERSION
$BUILD_TIME
EOF
echo "   版本: $VERSION"
echo "   构建时间: $BUILD_TIME"
echo -e "${GREEN}✅ 版本信息已生成${NC}"

# 步骤 5: 汇总结果
echo ""
echo "============================================"
echo "  构建完成！"
echo "============================================"
echo ""
echo "📁 产物目录: dist/"
echo ""

if [ -f "dist/omnia" ]; then
    echo "📦 可执行文件:"
    ls -lh dist/omnia
elif [ -f "dist/omnia.exe" ]; then
    echo "📦 可执行文件:"
    ls -lh dist/omnia.exe
fi

echo ""
echo "🔑 记得在构建后执行完整性签名："
echo "   python3 src/omnia/integrity.py sign"
echo ""
echo "🚀 部署激活服务器："
echo "   cd server && python3 activation_server.py"
echo ""
