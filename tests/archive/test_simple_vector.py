#!/usr/bin/env python3
"""Simple Vector Test - Quick check"""

import sys
print("Testing vector dependencies...")

# Test 1: PyTorch
print("\n[1/4] PyTorch...")
try:
    import torch
    print(f"  ✓ PyTorch {torch.__version__}")
    print(f"  ✓ CUDA: {torch.cuda.is_available()}")
except Exception as e:
    print(f"  ✗ {e}")
    sys.exit(1)

# Test 2: Sentence Transformers
print("\n[2/4] Sentence Transformers...")
try:
    from sentence_transformers import SentenceTransformer
    print("  ✓ sentence-transformers installed")
except Exception as e:
    print(f"  ✗ {e}")
    sys.exit(1)

# Test 3: ChromaDB
print("\n[3/4] ChromaDB...")
try:
    import chromadb
    print("  ✓ chromadb installed")
except Exception as e:
    print(f"  ✗ {e}")
    sys.exit(1)

# Test 4: Quick embedding test
print("\n[4/4] Quick embedding test...")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    vec = model.encode("测试文本", convert_to_numpy=True)
    print(f"  ✓ Model loaded, embedding shape: {vec.shape}")
    print(f"  ✓ First 5 values: {vec[:5]}")
except Exception as e:
    print(f"  ✗ {e}")
    sys.exit(1)

print("\n✓ All tests passed!")
