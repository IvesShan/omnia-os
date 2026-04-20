"""Neural Graph - Memory Palace 的索引层"""

from .graph import NeuralGraph, Entity, Relation
from .extractor import EntityExtractor
from .inferencer import RelationInferencer
from .builder import MemoryPalaceGraphBuilder, IdleGraphProcessor, build_neural_graph
from .conversation_processor import ConversationProcessor, process_conversation_history, process_single_turn
from .context_enhancer import NeuralGraphContextEnhancer, GraphContext
from .vector_store import VectorStore, SearchResult, semantic_search, get_vector_store
from .vector_integration import VectorIntegration, integrate_vectors, semantic_node_search

__all__ = [
    "NeuralGraph",
    "Entity",
    "Relation",
    "EntityExtractor",
    "RelationInferencer",
    "MemoryPalaceGraphBuilder",
    "IdleGraphProcessor",
    "build_neural_graph",
    # Conversation Processing (对话 → 图谱)
    "ConversationProcessor",
    "process_conversation_history",
    "process_single_turn",
    # Context Enhancement
    "NeuralGraphContextEnhancer",
    "GraphContext",
    # Vector Store (ChromaDB)
    "VectorStore",
    "SearchResult",
    "semantic_search",
    "get_vector_store",
    # Vector Integration (真正的向量嵌入)
    "VectorIntegration",
    "integrate_vectors",
    "semantic_node_search",
]
