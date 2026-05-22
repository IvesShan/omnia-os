#!/bin/bash
# ============================================================
# Omnia 完整打包脚本
# 功能：打包 + 代码保护 + 授权系统
# ============================================================

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          Omnia AIOS 商业版打包系统                         ║"
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

# 时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERSION="1.1.0"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 第一步：生成授权码"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p dist/licenses

# 生成各种类型的授权码
echo "生成授权码..."
python tools/license_system.py generate trial --count 10 > dist/licenses/trial_keys.txt
python tools/license_system.py generate monthly --count 50 > dist/licenses/monthly_keys.txt
python tools/license_system.py generate quarterly --count 30 > dist/licenses/quarterly_keys.txt
python tools/license_system.py generate yearly --count 20 > dist/licenses/yearly_keys.txt
python tools/license_system.py generate perpetual --count 10 > dist/licenses/perpetual_keys.txt

echo "✓ 授权码已生成到 dist/licenses/"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 第二步：打包后端"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 清理旧的构建
rm -rf build/pyinstaller-build
rm -rf dist/omnia-commercial

# PyInstaller 打包
pyinstaller \
    --onefile \
    --noconsole \
    --name omnia-backend \
    --distpath "dist/omnia-commercial" \
    --workpath "build/pyinstaller-build" \
    --specpath "build" \
    --add-data "seeds:seeds" \
    --add-data "config:config" \
    --add-data "web:web" \
    --add-data "skills:skills" \
    --hidden-import flask \
    --hidden-import flask_cors \
    --hidden-import json \
    --hidden-import logging \
    --hidden-import sqlite3 \
    backend/standalone_main.py

echo "✓ 后端打包完成"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 第三步：整合资源"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 复制资源文件
cp -r seeds dist/omnia-commercial/
cp -r config dist/omnia-commercial/
cp -r web dist/omnia-commercial/
cp -r skills dist/omnia-commercial/
cp -r docs dist/omnia-commercial/ 2>/dev/null || true
cp README.md dist/omnia-commercial/ 2>/dev/null || true
cp LICENSE.txt dist/omnia-commercial/ 2>/dev/null || true

# 复制授权系统
cp tools/license_system.py dist/omnia-commercial/

# 创建启动脚本
cat > dist/omnia-commercial/start-omnia.sh << 'STARTEOF'
#!/bin/bash
cd "$(dirname "$0")"
./omnia-backend --port 5001
STARTEOF
chmod +x dist/omnia-commercial/start-omnia.sh

# 创建 Windows 启动脚本
cat > dist/omnia-commercial/start-omnia.bat << 'BATEOF'
@echo off
cd /d "%~dp0"
omnia-backend.exe --port 5001
pause
BATEOF

echo "✓ 资源整合完成"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 第四步：创建用户手册"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > dist/omnia-commercial/使用说明.txt << 'MANUALEOF'
╔════════════════════════════════════════════════════════════╗
║                    Omnia AIOS 使用说明                     ║
╚════════════════════════════════════════════════════════════╝

【快速开始】

1. 双击运行 start-omnia.sh (Linux/macOS) 或 start-omnia.bat (Windows)
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

echo "✓ 用户手册已创建"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 第五步：压缩打包"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 创建压缩包
cd dist
tar -czf omnia-commercial-${VERSION}-${TIMESTAMP}.tar.gz omnia-commercial/
zip -r omnia-commercial-${VERSION}-${TIMESTAMP}.zip omnia-commercial/
cd ..

echo "✓ 压缩包已创建"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 打包完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "产物位置:"
echo "  📁 dist/omnia-commercial/"
echo "  📦 dist/omnia-commercial-${VERSION}-${TIMESTAMP}.tar.gz"
echo "  📦 dist/omnia-commercial-${VERSION}-${TIMESTAMP}.zip"
echo ""
echo "授权码位置:"
echo "  🔑 dist/licenses/"
echo ""
echo "文件列表:"
ls -lh dist/omnia-commercial/
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
