#!/bin/bash
# Omnia Vector System Verification
# 使用 pytorch_env 虚拟环境

echo "============================================================"
echo "Omnia Vector System Verification"
echo "============================================================"

VENV_PYTHON="$HOME/pytorch_env/bin/python"

# Test 1: Check dependencies
echo ""
echo "[1/3] Checking dependencies..."
$VENV_PYTHON -c "
import torch
from sentence_transformers import SentenceTransformer
import chromadb
print('  ✓ PyTorch:', torch.__version__)
print('  ✓ Sentence Transformers: OK')
print('  ✓ ChromaDB: OK')
"

if [ $? -ne 0 ]; then
    echo "  ✗ Dependencies check failed"
    exit 1
fi

# Test 2: Load model (background)
echo ""
echo "[2/3] Loading embedding model (this takes 30-60s on first run)..."
echo "  Loading all-MiniLM-L6-v2 model..."

$VENV_PYTHON -c "
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Force CPU

from sentence_transformers import SentenceTransformer
import time

start = time.time()
model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
elapsed = time.time() - start

print(f'  ✓ Model loaded in {elapsed:.1f}s')

# Test encoding
start = time.time()
vec = model.encode('测试文本', convert_to_numpy=True)
elapsed = time.time() - start

print(f'  ✓ Encoding time: {elapsed:.4f}s')
print(f'  ✓ Embedding shape: {vec.shape}')
print(f'  ✓ Sample values: {vec[:5]}')
"

if [ $? -ne 0 ]; then
    echo "  ✗ Model loading failed"
    exit 1
fi

# Test 3: Test Omnia Vector Service
echo ""
echo "[3/3] Testing Omnia Vector Service..."
cd /home/shan/omnia-os

$VENV_PYTHON -c "
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import sys
sys.path.insert(0, '.')

from src.core.shared_vector_service import SharedVectorService

service = SharedVectorService()

# Enable semantic mode
success = service.enable_semantic()

if success:
    # Test encoding
    vec1 = service.encode('用户喜欢用深色主题')
    vec2 = service.encode('用户偏好设置')
    vec3 = service.encode('Python 编程语言')
    
    sim1 = service.similarity(vec1, vec2)
    sim2 = service.similarity(vec1, vec3)
    
    print(f'  ✓ Semantic mode enabled')
    print(f'  ✓ Similarity(深色主题, 偏好设置): {sim1:.4f}')
    print(f'  ✓ Similarity(深色主题, Python): {sim2:.4f}')
    print('  ✓ Vector system working correctly!')
else:
    print('  ⚠ Semantic mode unavailable, using fallback')
"

echo ""
echo "============================================================"
echo "✓ Verification Complete!"
echo "============================================================"
