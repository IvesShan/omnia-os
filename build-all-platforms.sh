#!/bin/bash
# ============================================================
# Omnia 跨平台打包脚本
# 功能：本地测试 + 触发 GitHub Actions 跨平台构建
# ============================================================

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         Omnia 跨平台打包系统                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ -d "venv" ]; then
    echo "✓ 激活虚拟环境..."
    . venv/bin/activate
fi

# 检查依赖
echo "📦 检查依赖..."
pip install pyarmor nuitka ordered-set flask flask-cors --quiet

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤1：PyArmor 代码混淆"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 清理旧的混淆文件
rm -rf dist/obfuscated

# 混淆核心代码
echo "混淆 backend 代码..."
pyarmor gen -O dist/obfuscated -r backend/ 2>&1 | tail -5

echo "混淆 omnia 核心模块..."
pyarmor gen -O dist/obfuscated -r src/omnia/ 2>&1 | tail -5

echo "✓ 代码混淆完成"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤2：Nuitka 编译（Linux版本）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 清理旧的构建
rm -rf dist/nuitka-build
rm -rf dist/nuitka-dist

# 创建输出目录
mkdir -p dist/nuitka-build
mkdir -p dist/nuitka-dist

# Nuitka 编译
echo "开始编译..."
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
    --no-progressbar \
    --assume-yes-for-downloads \
    backend/standalone_main.py

echo "✓ Nuitka 编译完成"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤3：创建发布包"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 创建发布目录
RELEASE_DIR="dist/omnia-linux-x64"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# 复制编译产物
cp dist/nuitka-build/standalone_main.dist/omnia-backend "$RELEASE_DIR/"
chmod +x "$RELEASE_DIR/omnia-backend"

# 复制资源文件
cp -r seeds "$RELEASE_DIR/"
cp -r config "$RELEASE_DIR/"
cp -r web "$RELEASE_DIR/"
cp -r skills "$RELEASE_DIR/"

# 复制授权系统
cp tools/license_system.py "$RELEASE_DIR/"

# 复制文档
cp README.md "$RELEASE_DIR/" 2>/dev/null || true
cp LICENSE.txt "$RELEASE_DIR/" 2>/dev/null || true

# 创建启动脚本
cat > "$RELEASE_DIR/start-omnia.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./omnia-backend --port 5001
EOF
chmod +x "$RELEASE_DIR/start-omnia.sh"

# 创建使用说明
cat > "$RELEASE_DIR/使用说明.txt" << 'MANUALEOF'
╔════════════════════════════════════════════════════════════╗
║                    Omnia AIOS 使用说明                     ║
╚════════════════════════════════════════════════════════════╝

【快速开始】

1. 双击运行 start-omnia.sh
2. 程序将启动在 http://127.0.0.1:5001
3. 首次运行需要激活授权码

【激活授权】

方式一：命令行激活
  ./omnia-backend activate YOUR-LICENSE-KEY

方式二：API激活
  curl -X POST http://127.0.0.1:5001/api/license/activate \
    -H "Content-Type: application/json" \
    -d '{"key": "YOUR-LICENSE-KEY"}'

【查看授权状态】

  curl http://127.0.0.1:5001/api/license/status

【授权类型】

  - trial: 试用版（3天）
  - monthly: 月卡（30天）
  - quarterly: 季卡（90天）
  - yearly: 年卡（365天）
  - perpetual: 终身版（永久）

【购买授权】

请访问官方网站或联系客服购买。

【技术支持】

遇到问题请联系技术支持。

──────────────────────────────────────────────────────────────
Omnia AIOS v1.1.0
Copyright © 2026 All Rights Reserved
──────────────────────────────────────────────────────────────
MANUALEOF

echo "✓ 发布包创建完成"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤4：压缩打包"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd dist
tar -czf omnia-linux-x64-v1.1.0.tar.gz omnia-linux-x64/
echo "✓ 压缩包已创建: dist/omnia-linux-x64-v1.1.0.tar.gz"

cd ..

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 本地打包完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 产物位置: dist/omnia-linux-x64/"
echo "📦 压缩包: dist/omnia-linux-x64-v1.1.0.tar.gz"
echo ""
echo "📊 文件大小:"
du -sh dist/omnia-linux-x64/
du -sh dist/omnia-linux-x64-v1.1.0.tar.gz
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 跨平台打包（Windows/macOS）："
echo "   1. 创建 GitHub 仓库"
echo "   2. 推送代码: git push origin main"
echo "   3. 创建 tag: git tag v1.1.0 && git push --tags"
echo "   4. GitHub Actions 将自动打包三个平台"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
