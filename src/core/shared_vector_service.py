"""Shared Vector Service for Omnia.

A singleton service that provides vector embeddings for:
- Memory Palace (facts, habits, timeline)
- Neural Graph (nodes)

This ensures:
1. Single model loaded in memory (saves ~90MB)
2. Consistent embeddings across systems
3. Cross-system semantic search capability
"""

from __future__ import annotations

import os
import threading
import time
from typing import List, Optional, Tuple

import numpy as np

# Force CPU-only mode (avoid CUDA issues)
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# Use HuggingFace mirror for China (if needed)
# Set HF_ENDPOINT environment variable to use mirror
# Example: export HF_ENDPOINT=https://hf-mirror.com
if 'HF_ENDPOINT' not in os.environ:
    # Auto-detect if we need mirror (try to connect to huggingface.co)
    import socket
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('huggingface.co', 443))
        # Connection OK, use default
    except:
        # Connection failed, use mirror
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        print("[SharedVectorService] Using HuggingFace mirror: hf-mirror.com")


class SharedVectorService:
    """Singleton vector service using sentence-transformers or hash fallback."""
    
    _instance: Optional['SharedVectorService'] = None
    _lock = threading.Lock()
    
    def __new__(cls, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, auto_enable_semantic: bool = False):
        if self._initialized:
            return
        
        # Use shorter model name (without organization prefix for mirror compatibility)
        self.model_name = "all-MiniLM-L6-v2"
        self.full_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embedding_dim = 384
        self._model = None
        self._use_fallback = True
        self._model_loading = False
        self._load_error = None
        self._initialized = True
        
        # Don't auto-load model in __init__ to avoid blocking
        # Instead, load on first use or explicitly call enable_semantic()
        if auto_enable_semantic:
            # Start background loading
            self._start_background_load()
        else:
            print(f"[SharedVectorService] Initialized (lazy mode, will load model on demand)")
    
    def _start_background_load(self):
        """Start loading model in background thread."""
        if self._model_loading or self._model is not None:
            return
        
        def _load():
            self._model_loading = True
            try:
                self.enable_semantic()
            finally:
                self._model_loading = False
        
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
    
    def enable_semantic(self, timeout: float = 120.0) -> bool:
        """Enable semantic embeddings (loads model).
        
        Args:
            timeout: Maximum time to wait for model loading (seconds)
            
        Returns:
            True if semantic mode enabled, False if using fallback
        """
        if self._model is not None:
            return True
        
        if self._model_loading:
            # Wait for background loading
            start = time.time()
            while self._model_loading and (time.time() - start) < timeout:
                time.sleep(0.5)
            return self._model is not None
        
        try:
            import torch
            torch.set_num_threads(4)
            
            from sentence_transformers import SentenceTransformer
            
            hf_endpoint = os.environ.get('HF_ENDPOINT', 'https://huggingface.co')
            print(f"[SharedVectorService] Loading semantic model: {self.full_model_name}")
            print(f"[SharedVectorService] HF endpoint: {hf_endpoint}")
            
            # Try to load model
            start_time = time.time()
            
            # Try different model name formats for mirror compatibility
            model_names_to_try = [
                self.full_model_name,  # sentence-transformers/all-MiniLM-L6-v2
                self.model_name,       # all-MiniLM-L6-v2
            ]
            
            last_error = None
            for model_name in model_names_to_try:
                try:
                    self._model = SentenceTransformer(
                        model_name, 
                        device='cpu',
                        cache_folder=os.path.expanduser('~/.cache/huggingface/hub')
                    )
                    break
                except Exception as e:
                    last_error = e
                    print(f"[SharedVectorService] Failed to load '{model_name}': {e}")
                    continue
            
            if self._model is None:
                raise last_error or Exception("Failed to load model")
            
            load_time = time.time() - start_time
            
            self._use_fallback = False
            print(f"[SharedVectorService] ✓ Semantic model loaded in {load_time:.1f}s (384-dim embeddings)")
            return True
            
        except ImportError as e:
            self._load_error = str(e)
            print(f"[SharedVectorService] ⚠ PyTorch/sentence-transformers not available: {e}")
            print(f"[SharedVectorService] Using hash-based vectors (fallback mode)")
            return False
        except Exception as e:
            self._load_error = str(e)
            print(f"[SharedVectorService] ⚠ Failed to load semantic model: {e}")
            print(f"[SharedVectorService] Using hash-based vectors (fallback mode)")
            return False
    
    def _hash_vector(self, text: str) -> np.ndarray:
        """Generate a deterministic hash-based vector (fallback mode)."""
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(self.embedding_dim).astype(np.float32)
        return vec / np.linalg.norm(vec)
    
    def encode(self, text: str) -> np.ndarray:
        """Encode a single text to a 384-dim vector.
        
        Args:
            text: Input text to encode
            
        Returns:
            Normalized numpy array of shape (384,)
        """
        if not text or not text.strip():
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        if self._use_fallback:
            return self._hash_vector(text)
        
        # Use actual model
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts to vectors (alias for encode_batch).
        
        Args:
            texts: List of texts to encode
            
        Returns:
            Numpy array of shape (len(texts), 384)
        """
        if not texts:
            return np.array([])
        
        if self._use_fallback:
            return np.array([self._hash_vector(t) for t in texts])
        
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float32)
    
    def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Encode multiple texts to vectors."""
        if not texts:
            return []
        
        if self._use_fallback:
            return [self._hash_vector(t) for t in texts]
        
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [e.astype(np.float32) for e in embeddings]
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def is_semantic_enabled(self) -> bool:
        """Check if semantic mode is enabled."""
        return not self._use_fallback and self._model is not None
    
    def get_status(self) -> dict:
        """Get service status."""
        return {
            "semantic_enabled": self.is_semantic_enabled(),
            "model_loading": self._model_loading,
            "model_name": self.full_model_name if self._model else None,
            "embedding_dim": self.embedding_dim,
            "mode": "semantic" if self.is_semantic_enabled() else "hash-based",
            "load_error": self._load_error,
            "hf_endpoint": os.environ.get('HF_ENDPOINT', 'https://huggingface.co'),
        }


# Global instance (lazy initialization)
_global_service: Optional[SharedVectorService] = None


def get_vector_service() -> SharedVectorService:
    """Get or create the global vector service instance."""
    global _global_service
    if _global_service is None:
        _global_service = SharedVectorService()
    return _global_service
