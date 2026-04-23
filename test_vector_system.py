#!/usr/bin/env python3
"""Test Vector System - Verify semantic embeddings work."""

import sys
import time

print("=" * 60)
print("Omnia Vector System Test")
print("=" * 60)

# Test 1: PyTorch
print("\n[Test 1] PyTorch Installation")
try:
    import torch
    print(f"  ✓ PyTorch version: {torch.__version__}")
    print(f"  ✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  ✓ CUDA version: {torch.version.cuda}")
        print(f"  ✓ GPU: {torch.cuda.get_device_name(0)}")
except ImportError as e:
    print(f"  ✗ PyTorch not found: {e}")
    sys.exit(1)

# Test 2: Sentence Transformers
print("\n[Test 2] Sentence Transformers")
try:
    from sentence_transformers import SentenceTransformer
    print("  ✓ sentence-transformers installed")
except ImportError as e:
    print(f"  ✗ sentence-transformers not found: {e}")
    print("  → Install with: pip install sentence-transformers")
    sys.exit(1)

# Test 3: Load Embedding Model
print("\n[Test 3] Load Embedding Model")
model_name = "sentence-transformers/all-MiniLM-L6-v2"
try:
    start = time.time()
    model = SentenceTransformer(model_name, device='cpu')
    load_time = time.time() - start
    print(f"  ✓ Model loaded: {model_name}")
    print(f"  ✓ Load time: {load_time:.2f}s")
    print(f"  ✓ Embedding dimension: {model.get_sentence_embedding_dimension()}")
except Exception as e:
    print(f"  ✗ Failed to load model: {e}")
    sys.exit(1)

# Test 4: Generate Embeddings
print("\n[Test 4] Generate Embeddings")
test_texts = [
    "用户喜欢用深色主题",
    "Omnia 是一个 AI 操作系统",
    "记忆系统使用向量搜索",
]

try:
    start = time.time()
    embeddings = model.encode(test_texts, convert_to_numpy=True)
    encode_time = time.time() - start
    
    print(f"  ✓ Generated {len(embeddings)} embeddings")
    print(f"  ✓ Encoding time: {encode_time:.4f}s ({encode_time/len(test_texts):.4f}s per text)")
    print(f"  ✓ Shape: {embeddings.shape}")
    
    # Show first embedding
    print(f"  ✓ First embedding (first 5 dims): {embeddings[0][:5]}")
except Exception as e:
    print(f"  ✗ Failed to generate embeddings: {e}")
    sys.exit(1)

# Test 5: Semantic Similarity
print("\n[Test 5] Semantic Similarity")
from numpy import dot
from numpy.linalg import norm

def cosine_similarity(a, b):
    return dot(a, b) / (norm(a) * norm(b))

# Similar texts should have high similarity
sim_1_2 = cosine_similarity(embeddings[0], embeddings[1])
sim_1_3 = cosine_similarity(embeddings[0], embeddings[2])

print(f"  Similarity('用户喜欢用深色主题', 'Omnia 是一个 AI 操作系统'): {sim_1_2:.4f}")
print(f"  Similarity('用户喜欢用深色主题', '记忆系统使用向量搜索'): {sim_1_3:.4f}")

# Test 6: ChromaDB
print("\n[Test 6] ChromaDB Vector Store")
try:
    import chromadb
    from chromadb.config import Settings
    
    # Create temp client
    client = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="/tmp/test_chroma"
    ))
    
    collection = client.create_collection("test_collection")
    
    # Add documents
    collection.add(
        documents=test_texts,
        ids=["doc1", "doc2", "doc3"],
        embeddings=embeddings.tolist()
    )
    
    print(f"  ✓ ChromaDB collection created")
    print(f"  ✓ Added {len(test_texts)} documents")
    
    # Query
    query_embedding = model.encode("用户偏好设置", convert_to_numpy=True)
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=2
    )
    
    print(f"  ✓ Query: '用户偏好设置'")
    print(f"  ✓ Top result: '{results['documents'][0][0]}'")
    print(f"  ✓ Distance: {results['distances'][0][0]:.4f}")
    
except Exception as e:
    print(f"  ✗ ChromaDB test failed: {e}")
    print("  → Install with: pip install chromadb")

# Test 7: Omnia SharedVectorService
print("\n[Test 7] Omnia SharedVectorService")
try:
    sys.path.insert(0, '/home/shan//home/shan/omnia-os/omnia-os')
    from src.core.shared_vector_service import SharedVectorService
    
    service = SharedVectorService()
    
    # Enable semantic mode
    success = service.enable_semantic()
    
    if success:
        print("  ✓ Semantic mode enabled")
        
        # Test encoding
        vec = service.encode("测试文本")
        print(f"  ✓ Encoded text: shape={vec.shape}, dtype={vec.dtype}")
        
        # Test similarity
        vec2 = service.encode("测试文本")
        sim = service.similarity(vec, vec2)
        print(f"  ✓ Self-similarity: {sim:.4f}")
    else:
        print("  ⚠ Semantic mode failed, using fallback (hash-based)")
        
except Exception as e:
    print(f"  ✗ SharedVectorService test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✓ All tests completed!")
print("=" * 60)
