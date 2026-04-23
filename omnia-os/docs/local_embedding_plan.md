# Omnia 本地向量模型方案

## 目标
减少对 LLM API 的依赖，使用本地向量模型处理大部分场景。

---

## 架构设计

```
用户输入
    ↓
[本地向量模型] 意图分类 + 记忆检索
    ↓
    ├─ 简单任务 (60%) → 规则引擎 (不需要 LLM)
    │   - 查询记忆
    │   - 简单问答
    │   - 工具调用
    │
    └─ 复杂任务 (40%) → LLM API
        - 深度推理
        - 内容生成
        - 多轮对话
```

---

## 推荐模型

### 轻量级 (CPU 可运行)

| 模型 | 大小 | 用途 | 性能 |
|------|------|------|------|
| `all-MiniLM-L6-v2` | 80MB | 英文语义相似度 | ⭐⭐⭐ |
| `paraphrase-multilingual-MiniLM-L12-v2` | 120MB | 多语言支持 | ⭐⭐⭐ |
| `text2vec-chinese` | 200MB | 中文语义 | ⭐⭐⭐⭐ |

### 中等规模 (需要 GPU 或强 CPU)

| 模型 | 大小 | 用途 | 性能 |
|------|------|------|------|
| `bge-small-zh` | 100MB | 中文检索 | ⭐⭐⭐⭐ |
| `bge-base-zh` | 400MB | 中文检索 | ⭐⭐⭐⭐⭐ |
| `m3e-base` | 400MB | 多语言检索 | ⭐⭐⭐⭐⭐ |

---

## 实现步骤

### Phase 1: 本地意图分类 (1-2 天)

```python
# src/core/intent_classifier.py
from sentence_transformers import SentenceTransformer
import numpy as np

class LocalIntentClassifier:
    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)
        
        # 预定义意图向量
        self.intent_examples = {
            "query_memory": [
                "我之前说过什么",
                "你还记得吗",
                "查一下记忆"
            ],
            "tool_call": [
                "帮我读文件",
                "执行命令",
                "搜索网页"
            ],
            "chat": [
                "你好",
                "今天怎么样",
                "聊聊天"
            ]
        }
        
        # 预计算意图向量
        self.intent_vectors = {}
        for intent, examples in self.intent_examples.items():
            vectors = self.model.encode(examples)
            self.intent_vectors[intent] = np.mean(vectors, axis=0)
    
    def classify(self, text: str) -> tuple[str, float]:
        """分类用户意图"""
        text_vector = self.model.encode(text)
        
        # 计算与各意图的相似度
        similarities = {}
        for intent, intent_vector in self.intent_vectors.items():
            similarity = np.dot(text_vector, intent_vector) / (
                np.linalg.norm(text_vector) * np.linalg.norm(intent_vector)
            )
            similarities[intent] = similarity
        
        # 返回最相似的意图
        best_intent = max(similarities, key=similarities.get)
        return best_intent, similarities[best_intent]
```

### Phase 2: 本地记忆检索 (2-3 天)

```python
# src/core/memory/vector_retriever.py
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
import json

class VectorMemoryRetriever:
    def __init__(self, model_name="bge-small-zh"):
        self.model = SentenceTransformer(model_name)
        self.db_path = "memory_vectors.db"
        self._init_db()
    
    def _init_db(self):
        """初始化向量数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_vectors (
                id INTEGER PRIMARY KEY,
                content TEXT,
                vector BLOB,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def store_memory(self, content: str, metadata: dict):
        """存储记忆向量"""
        vector = self.model.encode(content)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO memory_vectors (content, vector, metadata, timestamp) VALUES (?, ?, ?, datetime('now'))",
            (content, vector.tobytes(), json.dumps(metadata))
        )
        conn.commit()
        conn.close()
    
    def retrieve_memories(self, query: str, top_k: int = 5) -> list:
        """检索相关记忆"""
        query_vector = self.model.encode(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT content, vector, metadata FROM memory_vectors")
        
        results = []
        for content, vector_bytes, metadata in cursor:
            stored_vector = np.frombuffer(vector_bytes, dtype=np.float32)
            similarity = np.dot(query_vector, stored_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(stored_vector)
            )
            results.append((content, similarity, json.loads(metadata)))
        
        conn.close()
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
```

### Phase 3: 混合路由 (1 天)

```python
# src/core/hybrid_router.py
from .intent_classifier import LocalIntentClassifier
from .memory.vector_retriever import VectorMemoryRetriever
from .llm_client import LLMClient

class HybridRouter:
    def __init__(self):
        self.intent_classifier = LocalIntentClassifier()
        self.memory_retriever = VectorMemoryRetriever()
        self.llm_client = LLMClient()
        
        # 简单任务处理器 (不需要 LLM)
        self.simple_handlers = {
            "query_memory": self._handle_query_memory,
            "tool_call": self._handle_tool_call,
        }
    
    async def process(self, user_input: str, context: dict):
        """处理用户输入"""
        # 1. 意图分类 (本地)
        intent, confidence = self.intent_classifier.classify(user_input)
        
        # 2. 检索相关记忆 (本地)
        memories = self.memory_retriever.retrieve_memories(user_input)
        
        # 3. 决策：本地处理 vs LLM 处理
        if intent in self.simple_handlers and confidence > 0.8:
            # 简单任务，本地处理
            return await self.simple_handlers[intent](user_input, memories)
        else:
            # 复杂任务，调用 LLM
            return await self._handle_with_llm(user_input, memories, context)
    
    async def _handle_query_memory(self, query: str, memories: list):
        """处理记忆查询 (不需要 LLM)"""
        if not memories:
            return "我没有找到相关的记忆。"
        
        # 直接返回检索结果
        response = "我找到了以下相关记忆：\n\n"
        for content, similarity, metadata in memories[:3]:
            response += f"- {content}\n"
            response += f"  (相似度: {similarity:.2%})\n\n"
        return response
    
    async def _handle_with_llm(self, query: str, memories: list, context: dict):
        """使用 LLM 处理复杂任务"""
        # 构建提示词
        prompt = f"用户说：{query}\n\n"
        if memories:
            prompt += "相关记忆：\n"
            for content, _, _ in memories[:3]:
                prompt += f"- {content}\n"
            prompt += "\n"
        
        # 调用 LLM
        response = await self.llm_client.chat([
            {"role": "user", "content": prompt}
        ])
        
        return response["choices"][0]["message"]["content"]
```

---

## 性能对比

| 方案 | 延迟 | 成本 | 隐私 | 适用场景 |
|------|------|------|------|---------|
| **纯 LLM** | 1-3s | 高 | 低 | 复杂推理 |
| **混合架构** | 100-500ms | 中 | 高 | 大部分场景 |
| **纯本地** | 10-100ms | 无 | 最高 | 简单任务 |

---

## 成本节省估算

假设每天处理 1000 次请求：
- 纯 LLM：1000 × $0.002 = $2/天 = $60/月
- 混合架构：400 × $0.002 = $0.8/天 = $24/月
- **节省 60% 成本**

---

## 下一步

1. 安装依赖：`pip install sentence-transformers`
2. 实现意图分类器
3. 实现向量记忆检索
4. 集成到 Omnia 主流程
5. 测试并优化

---

*创建时间: 2026-04-23*
