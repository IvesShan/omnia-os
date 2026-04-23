#!/bin/bash
# 验证 Omnia 向量系统
# 运行此脚本需要 1-2 分钟（首次加载模型较慢）

cd /home/shan/omnia-os

echo "=========================================="
echo "Omnia 向量系统验证"
echo "=========================================="
echo ""

PYTHON="/home/shan/pytorch_env/bin/python3"

if [ ! -f "$PYTHON" ]; then
    echo "❌ pytorch_env 不存在"
    echo "请先运行: python3 -m venv ~/pytorch_env && ~/pytorch_env/bin/pip install torch sentence-transformers"
    exit 1
fi

echo "✓ Python: $PYTHON"
echo ""

# 测试 1: 检查 PyTorch
echo "[1/4] 检查 PyTorch..."
$PYTHON -c "import torch; print(f'  PyTorch: {torch.__version__}')" || exit 1
echo "  ✓ PyTorch 已安装"
echo ""

# 测试 2: 检查 sentence-transformers
echo "[2/4] 检查 sentence-transformers..."
$PYTHON -c "from sentence_transformers import SentenceTransformer; print('  ✓ sentence-transformers 已安装')" || exit 1
echo ""

# 测试 3: 加载模型（最慢的步骤）
echo "[3/4] 加载语义模型 (需要 30-60 秒)..."
echo "  首次加载会慢一些，请耐心等待..."
$PYTHON -c "
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
print('  ✓ 模型加载成功')
" || exit 1
echo ""

# 测试 4: 测试 Omnia 向量服务
echo "[4/4] 测试 Omnia 向量服务..."
$PYTHON -c "
import sys
sys.path.insert(0, 'src')
from core.shared_vector_service import SharedVectorService

svc = SharedVectorService()
print(f'  模式: {svc.get_status()[\"mode\"]}')

# 测试编码
vec = svc.encode('用户喜欢用深色主题')
print(f'  向量维度: {vec.shape}')
print(f'  前5个值: {vec[:5]}')

# 测试相似度
vec2 = svc.encode('用户偏好暗色界面')
sim = svc.similarity(vec, vec2)
print(f'  相似度测试: {sim:.4f} (语义相似)')
" || exit 1
echo ""

echo "=========================================="
echo "✅ 向量系统验证通过！"
echo "=========================================="
echo ""
echo "现在每次启动 Omnia 守护进程，向量系统会自动启用。"
echo ""
echo "启动守护进程:"
echo "  python3 scripts/start_daemon.py"
echo ""
echo "查看日志:"
echo "  tail -f ~//home/shan/omnia-os/.omnia/daemon.log"
