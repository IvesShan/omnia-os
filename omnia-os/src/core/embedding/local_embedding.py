"""
Omnia 本地向量嵌入系统
使用 transformers 实现轻量级嵌入
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import json
from pathlib import Path


class LocalEmbedding:
    """轻量级本地嵌入系统"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self.cache_path = Path(__file__).parent.parent.parent.parent / "memory" / "embedding_cache.json"
        self.cache = {}
        self._load_cache()
        
    def _load_cache(self):
        """加载缓存"""
        if self.cache_path.exists():
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
    
    def _save_cache(self):
        """保存缓存"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                print(f"✅ 加载嵌入模型: {self.model_name}")
            except ImportError:
                print("⚠️ sentence-transformers 未安装，使用简单哈希嵌入")
                self.model = "hash"
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """编码文本为向量"""
        self._load_model()
        
        if self.model == "hash":
            # 使用简单哈希嵌入作为后备
            return self._hash_encode(texts)
        
        # 使用 sentence-transformers
        vectors = self.model.encode(texts, convert_to_numpy=True)
        return vectors
    
    def _hash_encode(self, texts: List[str]) -> np.ndarray:
        """使用哈希的简单嵌入（后备方案）"""
        vectors = []
        dim = 384  # 与 MiniLM 相同维度
        
        for text in texts:
            # 检查缓存
            if text in self.cache:
                vectors.append(self.cache[text])
                continue
            
            # 使用字符哈希生成伪向量
            np.random.seed(hash(text) % (2**32))
            vector = np.random.randn(dim)
            vector = vector / np.linalg.norm(vector)  # 归一化
            vector_list = vector.tolist()
            
            # 缓存
            self.cache[text] = vector_list
            vectors.append(vector_list)
        
        self._save_cache()
        return np.array(vectors)
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def search(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[int, float, str]]:
        """搜索最相似的文档"""
        # 编码查询
        query_vec = self.encode([query])[0]
        
        # 编码文档
        doc_vecs = self.encode(documents)
        
        # 计算相似度
        similarities = []
        for i, doc_vec in enumerate(doc_vecs):
            sim = self.similarity(query_vec, doc_vec)
            similarities.append((i, sim, documents[i]))
        
        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


class IntentClassifier:
    """本地意图分类器"""
    
    def __init__(self, embedding: LocalEmbedding = None):
        self.embedding = embedding or LocalEmbedding()
        
        # 预定义意图示例
        self.intent_examples = {
            "query_memory": [
                "我之前说过什么",
                "你还记得吗",
                "查一下记忆",
                "我的记忆里有什么",
                "回忆一下",
                "之前讨论过什么"
            ],
            "tool_call": [
                "帮我读文件",
                "执行命令",
                "搜索网页",
                "写一个文件",
                "列出目录",
                "运行脚本"
            ],
            "chat": [
                "你好",
                "今天怎么样",
                "聊聊天",
                "你觉得呢",
                "随便说说"
            ],
            "task": [
                "帮我做",
                "完成任务",
                "下一步",
                "继续",
                "开始工作"
            ],
            "question": [
                "是什么",
                "为什么",
                "怎么用",
                "能不能",
                "如何理解"
            ]
        }
        
        # 预计算意图向量
        self.intent_vectors = {}
        self._precompute_intent_vectors()
    
    def _precompute_intent_vectors(self):
        """预计算意图向量"""
        for intent, examples in self.intent_examples.items():
            vectors = self.embedding.encode(examples)
            self.intent_vectors[intent] = np.mean(vectors, axis=0)
    
    def classify(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """分类用户意图"""
        text_vec = self.embedding.encode([text])[0]
        
        # 计算与各意图的相似度
        similarities = {}
        for intent, intent_vec in self.intent_vectors.items():
            sim = self.embedding.similarity(text_vec, intent_vec)
            similarities[intent] = sim
        
        # 返回最相似的意图
        best_intent = max(similarities, key=similarities.get)
        return best_intent, similarities[best_intent], similarities
    
    def get_intent_description(self, intent: str) -> str:
        """获取意图描述"""
        descriptions = {
            "query_memory": "查询记忆 - 用户想查找之前的信息",
            "tool_call": "工具调用 - 用户想执行具体操作",
            "chat": "闲聊 - 用户想进行日常对话",
            "task": "任务执行 - 用户想推进工作",
            "question": "问答 - 用户有具体问题需要解答"
        }
        return descriptions.get(intent, "未知意图")


class VectorMemoryIndex:
    """向量记忆索引 - 增强 MemoryManagerV2 的检索能力"""
    
    def __init__(self, embedding: LocalEmbedding = None):
        self.embedding = embedding or LocalEmbedding()
        self.index_path = Path(__file__).parent.parent.parent.parent / "memory" / "vector_index.json"
        self.index = {}  # {memory_key: vector}
        self._load_index()
    
    def _load_index(self):
        """加载索引"""
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
    
    def _save_index(self):
        """保存索引"""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def add(self, key: str, content: str):
        """添加记忆到向量索引"""
        vector = self.embedding.encode([content])[0]
        self.index[key] = vector.tolist()
        self._save_index()
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """向量相似度搜索"""
        query_vec = self.embedding.encode([query])[0]
        
        similarities = []
        for key, vec_list in self.index.items():
            vec = np.array(vec_list)
            sim = self.embedding.similarity(query_vec, vec)
            similarities.append((key, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def remove(self, key: str):
        """从索引中移除"""
        if key in self.index:
            del self.index[key]
            self._save_index()
    
    def clear(self):
        """清空索引"""
        self.index = {}
        self._save_index()


# 便捷函数
def create_embedding_system() -> Tuple[LocalEmbedding, IntentClassifier, VectorMemoryIndex]:
    """创建完整的嵌入系统"""
    embedding = LocalEmbedding()
    classifier = IntentClassifier(embedding)
    index = VectorMemoryIndex(embedding)
    return embedding, classifier, index


if __name__ == "__main__":
    # 测试
    print("🧪 测试本地嵌入系统...")
    
    embedding, classifier, index = create_embedding_system()
    
    # 测试意图分类
    test_texts = [
        "你还记得我之前说过什么吗",
        "帮我读一下配置文件",
        "今天天气怎么样",
        "继续下一步工作",
        "这个功能是怎么用的"
    ]
    
    print("\n📊 意图分类测试:")
    for text in test_texts:
        intent, score, all_scores = classifier.classify(text)
        desc = classifier.get_intent_description(intent)
        print(f"  '{text}' → {intent} ({score:.2f})")
    
    # 测试向量搜索
    print("\n📊 向量搜索测试:")
    index.add("test1", "这是一个关于无人机的记忆")
    index.add("test2", "这是一个关于编程的记录")
    index.add("test3", "用户喜欢蓝色")
    
    results = index.search("无人机相关", top_k=3)
    for key, score in results:
        print(f"  {key}: {score:.3f}")
    
    print("\n✅ 测试完成！")
