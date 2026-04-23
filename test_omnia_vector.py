#!/usr/bin/env python3
"""Test Omnia Vector Service"""

import sys
import os

# Force CPU mode
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

print("=" * 60)
print("Omnia Vector Service Test")
print("=" * 60)

# Test SharedVectorService
print("\n[1] Importing SharedVectorService...")
sys.path.insert(0, '/home/shan//home/shan/omnia-os/omnia-os')

try:
    from src.core.shared_vector_service import SharedVectorService
    print("  ✓ Imported")
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Create service
print("\n[2] Creating service instance...")
try:
    service = SharedVectorService()
    print(f"  ✓ Created (fallback mode: {service._use_fallback})")
except Exception as e:
    print(f"  ✗ Creation failed: {e}")
    sys.exit(1)

# Test fallback mode first
print("\n[3] Testing fallback mode...")
try:
    vec = service.encode("测试文本")
    print(f"  ✓ Fallback encoding works: shape={vec.shape}")
    print(f"  ✓ First 5 values: {vec[:5]}")
except Exception as e:
    print(f"  ✗ Fallback failed: {e}")
    sys.exit(1)

# Try to enable semantic mode
print("\n[4] Enabling semantic mode (this may take 30-60s)...")
print("  Loading sentence-transformers model...")

try:
    import time
    start = time.time()
    success = service.enable_semantic()
    elapsed = time.time() - start
    
    if success:
        print(f"  ✓ Semantic mode enabled in {elapsed:.1f}s")
        
        # Test semantic encoding
        print("\n[5] Testing semantic encoding...")
        start = time.time()
        vec = service.encode("用户喜欢用深色主题")
        elapsed = time.time() - start
        
        print(f"  ✓ Encoded in {elapsed:.4f}s")
        print(f"  ✓ Shape: {vec.shape}")
        print(f"  ✓ First 5 values: {vec[:5]}")
        
        # Test similarity
        print("\n[6] Testing semantic similarity...")
        vec2 = service.encode("用户偏好设置")
        sim = service.similarity(vec, vec2)
        print(f"  ✓ Similarity('用户喜欢用深色主题', '用户偏好设置'): {sim:.4f}")
        
        # Test with different text
        vec3 = service.encode("Python 编程语言")
        sim2 = service.similarity(vec, vec3)
        print(f"  ✓ Similarity('用户喜欢用深色主题', 'Python 编程语言'): {sim2:.4f}")
        
        print("\n" + "=" * 60)
        print("✓ Vector system is fully functional!")
        print("=" * 60)
    else:
        print(f"  ⚠ Semantic mode failed after {elapsed:.1f}s")
        print("  Continuing with fallback (hash-based) mode")
        print("\n" + "=" * 60)
        print("⚠ Vector system works in fallback mode")
        print("  (Hash-based vectors, no semantic understanding)")
        print("=" * 60)
        
except Exception as e:
    print(f"  ✗ Semantic mode failed: {e}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 60)
    print("⚠ Vector system in fallback mode")
    print("=" * 60)
