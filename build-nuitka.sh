#!/bin/bash
# ============================================================
# Omnia Nuitka 打包脚本
# 使用 Nuitka 编译为 C++，代码保护等级最高
# ============================================================

set -e

echo "🔨 Omnia Nuitka 打包开始..."
echo "============================================"

# 激活虚拟环境
if [ -d "venv" ]; then
    echo "✓ 激活虚拟环境..."
    . venv/bin/activate
fi

# 检查依赖
echo "📦 检查 Nuitka 依赖..."
pip install nuitka ordered-set --quiet

# 清理旧的构建
rm -rf dist/nuitka-build
rm -rf dist/nuitka-dist

# 创建输出目录
mkdir -p dist/nuitka-build
mkdir -p dist/nuitka-dist

echo ""
echo "🔧 开始编译后端（Nuitka）..."
echo "============================================"

# Nuitka 编译
python -m nuitka \
    --standalone \
    --onefile \
    --output-dir=dist/nuitka-build \
    --output-filename=omnia-backend \
    --include-data-dir=seeds=seeds \
    --include-data-dir=config=config \
    --include-data-dir=web=web \
    --include-data-dir=skills=skills \
    --include-package=flask \
    --include-package=flask_cors \
    --no-progressbar \
    --assume-yes-for-downloads \
    --remove-output \
    backend/standalone_main.py

echo ""
echo "✅ Nuitka 编译完成！"
echo ""

# 复制产物到 dist
cp dist/nuitka-build/standalone_main.dist/omnia-backend dist/nuitka-dist/
chmod +x dist/nuitka-dist/omnia-backend

# 复制资源文件
cp -r seeds dist/nuitka-dist/
cp -r config dist/nuitka-dist/
cp -r web dist/nuitka-dist/
cp -r skills dist/nuitka-dist/

# 创建启动脚本
cat > dist/nuitka-dist/start-omnia.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./omnia-backend --port 5001
EOF
chmod +x dist/nuitka-dist/start-omnia.sh

echo "============================================"
echo "📦 打包产物位置: dist/nuitka-dist/"
echo ""
echo "文件列表:"
ls -lh dist/nuitka-dist/
echo ""
echo "============================================"
echo "✅ 打包完成！"
