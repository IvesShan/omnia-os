"""Vector Store - Semantic search for Neural Graph

Integrates ChromaDB with Neural Graph for semantic memory search.
Uses sentence-transformers for local embedding generation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.config import VECTOR_STORE_DIR

# Lazy imports to avoid startup overhead
_chromadb = None
_embedding_model = None


def _get_chromadb():
    """Lazy load ChromaDB"""
    global _chromadb
    if _chromadb is None:
        import chromadb
        _chromadb = chromadb
    return _chromadb


def _get_embedding_model():
    """Lazy load sentence-transformers model"""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


class SearchResult:
    """A search result from the vector store"""
    memory_id: str
    text: str
    score: float  # Similarity score (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
        }


class VectorStore:
    """
    Semantic search for Memory Palace using ChromaDB.
    
    Features:
    - Local embedding generation (sentence-transformers)
    - Persistent storage (ChromaDB)
    - Hybrid search (vector + metadata filtering)
    - Incremental updates
    """
    
    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: str = "omnia_memories",
    ):
        self.persist_dir = persist_dir or VECTOR_STORE_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        
        # Initialize ChromaDB
        chromadb = _get_chromadb()
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        # Initialize embedding model
        self.embedding_model = _get_embedding_model()
    
    def add_memory(
        self,
        memory_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a memory to the vector store.
        
        Args:
            memory_id: Unique identifier for the memory
            text: The text content to embed
            metadata: Optional metadata (layer, project, tags, etc.)
            
        Returns:
            True if successful
        """
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()
            
            # Add to collection
            self.collection.upsert(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
            )
            
            return True
            
        except Exception as e:
            print(f"[VectorStore] Failed to add memory {memory_id}: {e}")
            return False
    
    def add_memories_batch(
        self,
        memories: List[Tuple[str, str, Dict[str, Any]]],
    ) -> int:
        """
        Add multiple memories at once.
        
        Args:
            memories: List of (memory_id, text, metadata) tuples
            
        Returns:
            Number of successfully added memories
        """
        if not memories:
            return 0
        
        try:
            # Generate embeddings in batch
            texts = [m[1] for m in memories]
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Add to collection
            self.collection.upsert(
                ids=[m[0] for m in memories],
                embeddings=embeddings,
                documents=texts,
                metadatas=[m[2] for m in memories],
            )
            
            return len(memories)
            
        except Exception as e:
            print(f"[VectorStore] Batch add failed: {e}")
            return 0
    
    def search(
        self,
        query: str,
        top_k: int = 3,  # Reduced for better precision
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar memories.
        
        Args:
            query: The search query
            top_k: Number of results to return
            metadata_filter: Optional metadata filters (e.g., {"layer": "habits"})
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=metadata_filter,
            )
            
            # Convert to SearchResult objects
            search_results = []
            if results['ids'] and results['ids'][0]:
                for i, memory_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    # Convert distance to similarity score (cosine distance = 1 - cosine similarity)
                    score = 1 - distance
                    
                    # Only include results above minimum score threshold
                    if score >= 0.3:  # Minimum similarity threshold
                        search_results.append(SearchResult(
                            memory_id=memory_id,
                            text=results['documents'][0][i] if results.get('documents') else "",
                            score=score,
                            metadata=results['metadatas'][0][i] if results.get('metadatas') else {},
                        ))
            
            return search_results
            
        except Exception as e:
            print(f"[VectorStore] Search failed: {e}")
            return []
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID"""
        try:
            results = self.collection.get(ids=[memory_id])
            if results['ids']:
                return {
                    "memory_id": results['ids'][0],
                    "text": results['documents'][0] if results.get('documents') else "",
                    "metadata": results['metadatas'][0] if results.get('metadatas') else {},
                }
        except Exception as e:
            print(f"[VectorStore] Failed to get memory {memory_id}: {e}")
        return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from the store"""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"[VectorStore] Failed to delete memory {memory_id}: {e}")
            return False
    
    def count(self) -> int:
        """Get the number of memories in the store"""
        return self.collection.count()
    
    def clear(self):
        """Clear all memories from the store"""
        # Delete and recreate collection
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    
    def sync_from_memory_palace(self, memory_palace_db: Path) -> int:
        """
        Sync all memories from Memory Palace to vector store.
        
        Args:
            memory_palace_db: Path to memory_palace.db
            
        Returns:
            Number of memories synced
        """
        import sqlite3
        
        if not memory_palace_db.exists():
            print(f"[VectorStore] Memory Palace DB not found: {memory_palace_db}")
            return 0
        
        conn = sqlite3.connect(str(memory_palace_db))
        cursor = conn.cursor()
        
        # Get all memories from all layers
        memories = []
        
        for layer in ['facts', 'relations', 'habits', 'timeline']:
            try:
                cursor.execute(f"SELECT id, content, metadata FROM {layer}")
                for row in cursor.fetchall():
                    memory_id = f"{layer}_{row[0]}"
                    content = row[1]
                    metadata = json.loads(row[2]) if row[2] else {}
                    metadata['layer'] = layer
                    memories.append((memory_id, content, metadata))
            except Exception as e:
                print(f"[VectorStore] Failed to read {layer}: {e}")
        
        conn.close()
        
        # Add to vector store in batches
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(memories), batch_size):
            batch = memories[i:i + batch_size]
            added = self.add_memories_batch(batch)
            total_added += added
            print(f"[VectorStore] Synced batch {i//batch_size + 1}: {added} memories")
        
        return total_added


# ============================================================================
# Convenience Functions
# ============================================================================

def get_vector_store() -> VectorStore:
    """Get the global VectorStore instance"""
    global _vector_store
    if '_vector_store' not in globals():
        _vector_store = VectorStore()
    return _vector_store


def semantic_search(query: str, top_k: int = 3) -> List[SearchResult]:  # Reduced for better precision
    """
    Quick semantic search across all memories.
    
    Args:
        query: The search query
        top_k: Number of results
        
    Returns:
        List of SearchResult objects
    """
    store = get_vector_store()
    return store.search(query, top_k=top_k)
