# 神经图谱（Neural Graph）系统规划 v2.0

> 基于用户反馈优化的版本

---

## 核心定位

**Neural Graph 是 Memory Palace 的索引层，不是替代品**

```
数据流：

MemoryPalace (1043条记忆)
├── facts (事实)
├── relations (关系)  
├── habits (习惯)
└── timeline (时间线)
        │
        │ 空闲时读取
        ▼
NeuralGraph (索引层)
├── nodes (实体节点)
├── edges (关系边)
└── embeddings (向量索引)
        │
        │ 查询时返回
        ▼
MemoryPalace 原始记录
```

---

## 一、技术选型

### 1. 图谱存储：SQLite + 邻接表

**理由**：
- 轻量级，符合 Omnia 风格
- 与现有 Memory Palace 使用相同数据库
- 无需额外依赖

```sql
-- 复用 memory_palace.db，添加图谱表
CREATE TABLE IF NOT EXISTS neural_nodes (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,      -- PERSON/PROJECT/FILE/EVENT/CONCEPT
    entity_name TEXT NOT NULL,
    canonical_name TEXT,             -- 标准化名称
    aliases TEXT,                    -- JSON array
    properties TEXT,                 -- JSON object
    embedding BLOB,                  -- 向量（可选）
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_accessed TEXT,
    access_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS neural_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,     -- BELONGS_TO/RELATED_TO/DEPENDS_ON/...
    weight REAL DEFAULT 0.5,
    evidence TEXT,                   -- 来源 memory_id
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_accessed TEXT,
    access_count INTEGER DEFAULT 0,
    FOREIGN KEY (source_id) REFERENCES neural_nodes(id),
    FOREIGN KEY (target_id) REFERENCES neural_nodes(id)
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON neural_nodes(entity_type);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON neural_nodes(entity_name);
CREATE INDEX IF NOT EXISTS idx_edges_source ON neural_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON neural_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_weight ON neural_edges(weight);
```

### 2. 实体抽取：规则 + LLM 混合方案

**策略**：
- **规则匹配**：快速识别已知实体（项目名、文件名、日期）
- **LLM 补充**：空闲时或复杂文本时调用

```python
class EntityExtractor:
    """混合实体抽取器"""
    
    # 已知实体词典（从 Memory Palace 学习）
    KNOWN_ENTITIES = {
        "PERSON": ["原点", "无限", "李先生", "建筑师"],
        "PROJECT": ["喵修匠", "懂机帝", "Omnia", "Omnia OS", "njuosun.com"],
        "FILE": ["README.md", "config.json", "package.json", ".env"],
        "CONCEPT": ["协作", "记忆", "工具调用", "部署", "API"],
    }
    
    def extract(self, text: str, use_llm: bool = False) -> List[Entity]:
        entities = []
        
        # 1. 规则快速匹配
        entities.extend(self._rule_based_extract(text))
        
        # 2. 日期提取
        entities.extend(self._extract_dates(text))
        
        # 3. 文件路径提取
        entities.extend(self._extract_paths(text))
        
        # 4. LLM 补充（仅在需要时）
        if use_llm and self._needs_llm(text):
            entities.extend(self._llm_extract(text))
        
        return self._deduplicate(entities)
    
    def _rule_based_extract(self, text: str) -> List[Entity]:
        """基于已知词典的快速匹配"""
        entities = []
        
        for entity_type, names in self.KNOWN_ENTITIES.items():
            for name in names:
                if name in text:
                    entities.append(Entity(
                        type=entity_type,
                        name=name,
                        confidence=1.0
                    ))
        
        return entities
    
    def _extract_dates(self, text: str) -> List[Entity]:
        """提取日期"""
        import re
        
        patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}-\d{2}-\d{2}',
            r'今天|昨天|前天|最近',
        ]
        
        entities = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(Entity(type='DATE', name=match))
        
        return entities
    
    def _extract_paths(self, text: str) -> List[Entity]:
        """提取文件路径"""
        import re
        
        # 匹配文件路径和文件名
        patterns = [
            r'/[\w/.-]+\.\w+',           # 绝对路径
            r'[\w-]+\.\w{2,4}',          # 文件名
            r'~\/[\w/.-]+',              # 用户目录
        ]
        
        entities = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(Entity(type='FILE', name=match))
        
        return entities
    
    def _needs_llm(self, text: str) -> bool:
        """判断是否需要 LLM"""
        # 文本较长或包含复杂结构
        return len(text) > 500 or any(
            kw in text for kw in 
            ["意味着", "导致", "因为", "所以", "关系", "影响"]
        )
    
    def _llm_extract(self, text: str) -> List[Entity]:
        """LLM 实体抽取（空闲时调用）"""
        from omnia.chat import _call_model_messages
        
        prompt = f"""从以下文本中提取实体，返回 JSON 格式：

文本：{text}

实体类型：
- PERSON: 人物
- PROJECT: 项目
- FILE: 文件
- EVENT: 事件
- CONCEPT: 概念
- DATE: 日期
- LOCATION: 位置

返回格式：
{{"entities": [{{"type": "PERSON", "name": "xxx"}}]}}
"""
        
        try:
            response = _call_model_messages(
                api_key=self.api_key,
                provider=self.provider,
                messages=[{"role": "user", "content": prompt}],
                tools=None
            )
            
            content = response["choices"][0]["message"]["content"]
            # 解析 JSON
            import json
            data = json.loads(content)
            return [Entity(**e) for e in data.get("entities", [])]
        except:
            return []
```

### 3. 向量嵌入：轻量级方案

**方案 A（推荐）：哈希伪嵌入**
- 无需模型，即时计算
- 足够用于相似度排序

**方案 B（可选）：sentence-transformers**
- 需要下载模型（~100MB）
- 更准确，但有性能开销

```python
import numpy as np
import hashlib

def simple_embedding(text: str, dim: int = 64) -> bytes:
    """
    基于哈希的伪嵌入（方案 A）
    - 快速、无依赖
    - 足够用于相似度计算
    """
    vec = np.zeros(dim, dtype=np.float32)
    
    for i in range(dim):
        # 使用哈希生成伪随机值
        h = hashlib.md5(f"{text}:{i}".encode()).hexdigest()
        vec[i] = int(h[:8], 16) / 0xFFFFFFFF
    
    # 归一化
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    
    return vec.tobytes()

def embedding_similarity(emb1: bytes, emb2: bytes) -> float:
    """计算两个向量的余弦相似度"""
    v1 = np.frombuffer(emb1, dtype=np.float32)
    v2 = np.frombuffer(emb2, dtype=np.float32)
    
    return float(np.dot(v1, v2))
```

### 4. 空闲检测与触发

```python
import time
import psutil

class IdleDetector:
    """空闲检测器"""
    
    IDLE_THRESHOLD = 5 * 60      # 5分钟无交互
    CPU_THRESHOLD = 0.5          # CPU 负载 < 50%
    MAX_BATCH_SIZE = 100         # 每次最多处理 100 条
    
    def __init__(self):
        self.last_interaction = time.time()
    
    def record_interaction(self):
        """记录用户交互"""
        self.last_interaction = time.time()
    
    def is_idle(self) -> bool:
        """是否空闲"""
        return (time.time() - self.last_interaction) > self.IDLE_THRESHOLD
    
    def should_process(self) -> bool:
        """是否应该处理"""
        return (
            self.is_idle() and
            self._cpu_load() < self.CPU_THRESHOLD and
            self._has_unprocessed()
        )
    
    def _cpu_load(self) -> float:
        """获取 CPU 负载"""
        return psutil.cpu_percent(interval=1) / 100
    
    def _has_unprocessed(self) -> bool:
        """是否有未处理的记忆"""
        # 检查是否有新记忆未加入图谱
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM facts 
            WHERE id NOT IN (
                SELECT json_extract(evidence, '$.fact_id') 
                FROM neural_edges
            )
        """)
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
```

---

## 二、实施步骤（调整后）

### Phase 1: 最小可用版本（2-3天）

**目标**：能跑起来，能查询

- [x] SQLite schema（复用 memory_palace.db）
- [ ] 规则实体抽取器
- [ ] 基础图谱构建
- [ ] 简单查询接口

**验收标准**：
```python
# 能执行这些操作
graph.add_node(Entity(type="PROJECT", name="喵修匠"))
graph.add_edge(source="喵修匠", target="原点", relation="WORKED_ON")
nodes = graph.get_related("喵修匠")  # 返回 ["原点", ...]
```

### Phase 2: 可视化 + 验证（1-2天）

**目标**：能看到图谱，能手动修正

- [ ] Web UI 图谱查看器
- [ ] 节点/边的手动编辑
- [ ] 实体抽取结果展示

**验收标准**：
- 打开 `/graph` 页面能看到节点网络
- 能手动添加/删除节点
- 能看到实体抽取的结果

### Phase 3: LLM 增强（2-3天）

**目标**：自动构建，智能推理

- [ ] 从 Memory Palace 自动构建图谱
- [ ] LLM 关系推理
- [ ] 意图识别器

**验收标准**：
```python
# 能自动处理记忆
neural_graph.build_from_memory_palace(memory_palace)

# 能识别意图
intent = neural_graph.recognize_intent("喵修匠怎么样了")
# 返回: {topic: "喵修匠", type: "STATUS_CHECK", related: [...]}
```

### Phase 4: 优化 + 生产化（持续）

**目标**：性能优化，生产可用

- [ ] 关系衰减机制
- [ ] 主动建议
- [ ] 性能测试和优化
- [ ] 错误处理

---

## 三、核心代码实现

### neural_graph.py

```python
"""Neural Graph - Memory Palace 的索引层"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class Entity:
    """实体节点"""
    type: str          # PERSON/PROJECT/FILE/EVENT/CONCEPT/DATE/LOCATION
    name: str
    canonical_name: str = None
    confidence: float = 1.0
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.canonical_name is None:
            self.canonical_name = self.name
        if self.properties is None:
            self.properties = {}


@dataclass
class Relation:
    """关系边"""
    source: str
    target: str
    type: str          # BELONGS_TO/RELATED_TO/DEPENDS_ON/CAUSED_BY/WORKED_ON/...
    weight: float = 0.5
    evidence: str = None  # 来源记忆 ID


class NeuralGraph:
    """神经图谱 - Memory Palace 的索引层"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(
            Path.home() / ".openclaw" / "workspace" / ".omnia" / "memory_palace.db"
        )
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库 schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建节点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neural_nodes (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                canonical_name TEXT,
                aliases TEXT,
                properties TEXT,
                embedding BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0
            )
        """)
        
        # 创建边表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neural_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 0.5,
                evidence TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                FOREIGN KEY (source_id) REFERENCES neural_nodes(id),
                FOREIGN KEY (target_id) REFERENCES neural_nodes(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON neural_nodes(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON neural_nodes(entity_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON neural_edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON neural_edges(target_id)")
        
        conn.commit()
        conn.close()
    
    # ========== 节点操作 ==========
    
    def add_node(self, entity: Entity) -> str:
        """添加实体节点"""
        import uuid
        
        node_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{entity.type}:{entity.name}").hex
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM neural_nodes WHERE entity_name = ?", (entity.name,))
        if cursor.fetchone():
            conn.close()
            return node_id
        
        # 插入新节点
        cursor.execute("""
            INSERT OR REPLACE INTO neural_nodes 
            (id, entity_type, entity_name, canonical_name, aliases, properties, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            node_id,
            entity.type,
            entity.name,
            entity.canonical_name,
            json.dumps([]),
            json.dumps(entity.properties or {}),
            self._compute_embedding(entity.name),
        ))
        
        conn.commit()
        conn.close()
        
        return node_id
    
    def get_node(self, name: str) -> Optional[Dict]:
        """获取节点信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, entity_type, entity_name, canonical_name, properties, access_count
            FROM neural_nodes
            WHERE entity_name = ? OR canonical_name = ?
        """, (name, name))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "type": row[1],
                "name": row[2],
                "canonical_name": row[3],
                "properties": json.loads(row[4]) if row[4] else {},
                "access_count": row[5],
            }
        return None
    
    def search_nodes(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索节点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, entity_type, entity_name, access_count
            FROM neural_nodes
            WHERE entity_name LIKE ? OR canonical_name LIKE ?
            ORDER BY access_count DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"id": r[0], "type": r[1], "name": r[2], "access_count": r[3]}
            for r in rows
        ]
    
    # ========== 边操作 ==========
    
    def add_edge(self, relation: Relation) -> str:
        """添加关系边"""
        import uuid
        
        # 确保节点存在
        source_node = self.get_node(relation.source)
        if not source_node:
            self.add_node(Entity(type="UNKNOWN", name=relation.source))
        
        target_node = self.get_node(relation.target)
        if not target_node:
            self.add_node(Entity(type="UNKNOWN", name=relation.target))
        
        edge_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, 
            f"{relation.source}:{relation.type}:{relation.target}"
        ).hex
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT id, weight FROM neural_edges 
            WHERE source_id = ? AND target_id = ? AND relation_type = ?
        """, (relation.source, relation.target, relation.type))
        
        existing = cursor.fetchone()
        
        if existing:
            # 已存在，增强权重
            new_weight = min(existing[1] + 0.1, 1.0)
            cursor.execute("""
                UPDATE neural_edges SET weight = ?, last_accessed = ?
                WHERE id = ?
            """, (new_weight, datetime.now().isoformat(), existing[0]))
        else:
            # 新建边
            cursor.execute("""
                INSERT INTO neural_edges
                (id, source_id, target_id, relation_type, weight, evidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                edge_id,
                relation.source,
                relation.target,
                relation.type,
                relation.weight,
                relation.evidence,
            ))
        
        conn.commit()
        conn.close()
        
        return edge_id
    
    def get_related(self, name: str, max_depth: int = 2) -> List[Dict]:
        """获取相关节点（BFS 遍历）"""
        visited = set()
        queue = [(name, 0)]
        results = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        while queue:
            current, depth = queue.pop(0)
            
            if current in visited or depth > max_depth:
                continue
            
            visited.add(current)
            
            # 查询出边
            cursor.execute("""
                SELECT target_id, relation_type, weight
                FROM neural_edges
                WHERE source_id = ?
                ORDER BY weight DESC
            """, (current,))
            
            for row in cursor.fetchall():
                target, rel_type, weight = row
                if target not in visited:
                    results.append({
                        "name": target,
                        "relation": rel_type,
                        "weight": weight,
                        "depth": depth + 1,
                    })
                    queue.append((target, depth + 1))
            
            # 查询入边
            cursor.execute("""
                SELECT source_id, relation_type, weight
                FROM neural_edges
                WHERE target_id = ?
                ORDER BY weight DESC
            """, (current,))
            
            for row in cursor.fetchall():
                source, rel_type, weight = row
                if source not in visited:
                    results.append({
                        "name": source,
                        "relation": f"inverse_{rel_type}",
                        "weight": weight,
                        "depth": depth + 1,
                    })
                    queue.append((source, depth + 1))
        
        conn.close()
        
        # 按权重排序
        results.sort(key=lambda x: (-x["weight"], x["depth"]))
        
        return results
    
    # ========== 图谱构建 ==========
    
    def build_from_memory_palace(self, memory_palace, batch_size: int = 100):
        """从 Memory Palace 构建图谱"""
        from .entity_extractor import EntityExtractor
        from .relation_inferencer import RelationInferencer
        
        extractor = EntityExtractor()
        inferencer = RelationInferencer()
        
        # 获取所有 facts
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, key, value, category FROM facts")
        facts = cursor.fetchall()
        conn.close()
        
        print(f"[NeuralGraph] 开始处理 {len(facts)} 条记忆...")
        
        for i, (fact_id, key, value, category) in enumerate(facts):
            if i % 10 == 0:
                print(f"[NeuralGraph] 进度: {i}/{len(facts)}")
            
            # 提取实体
            text = f"{key} {value}"
            entities = extractor.extract(text, use_llm=False)
            
            # 添加节点
            for entity in entities:
                self.add_node(entity)
            
            # 推理关系
            if len(entities) >= 2:
                relations = inferencer.infer_batch(entities, text)
                for rel in relations:
                    rel.evidence = json.dumps({"fact_id": fact_id})
                    self.add_edge(rel)
        
        print(f"[NeuralGraph] 完成！构建了 {len(self.get_stats())} 个节点")
    
    # ========== 意图识别 ==========
    
    def recognize_intent(self, query: str) -> Dict:
        """识别用户意图"""
        from .entity_extractor import EntityExtractor
        
        extractor = EntityExtractor()
        entities = extractor.extract(query)
        
        if not entities:
            return {
                "topic": None,
                "type": "UNKNOWN",
                "confidence": 0.0,
                "related": [],
            }
        
        # 找到主要实体
        primary = entities[0]
        
        # 获取相关节点
        related = self.get_related(primary.name)
        
        # 判断意图类型
        intent_type = self._classify_intent(query, primary.type)
        
        return {
            "topic": primary.name,
            "topic_type": primary.type,
            "type": intent_type,
            "confidence": primary.confidence,
            "related": related[:5],
        }
    
    def _classify_intent(self, query: str, entity_type: str) -> str:
        """分类意图类型"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["怎么样", "状态", "如何"]):
            return "STATUS_CHECK"
        elif any(kw in query_lower for kw in ["帮我", "做", "执行"]):
            return "ACTION_REQUEST"
        elif any(kw in query_lower for kw in ["是什么", "介绍", "解释"]):
            return "EXPLANATION"
        elif any(kw in query_lower for kw in ["比较", "对比", "区别"]):
            return "COMPARISON"
        else:
            return "QUERY"
    
    # ========== 工具方法 ==========
    
    def _compute_embedding(self, text: str) -> bytes:
        """计算嵌入向量"""
        dim = 64
        vec = np.zeros(dim, dtype=np.float32)
        
        for i in range(dim):
            import hashlib
            h = hashlib.md5(f"{text}:{i}".encode()).hexdigest()
            vec[i] = int(h[:8], 16) / 0xFFFFFFFF
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return vec.tobytes()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM neural_nodes")
        node_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM neural_edges")
        edge_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT entity_type, COUNT(*) FROM neural_nodes GROUP BY entity_type")
        by_type = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "nodes": node_count,
            "edges": edge_count,
            "by_type": by_type,
        }
    
    def decay_weights(self, days: int = 30, rate: float = 0.95):
        """衰减未使用的关系"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE neural_edges
            SET weight = weight * ?
            WHERE last_accessed < datetime('now', ?)
        """, (rate, f"-{days} days"))
        
        # 删除权重过低的边
        cursor.execute("DELETE FROM neural_edges WHERE weight < 0.1")
        
        conn.commit()
        conn.close()
```

---

## 四、Web UI 可视化

### /graph 页面

```html
<!-- 简单的图谱可视化 -->
<div id="graph-container">
    <canvas id="graph-canvas"></canvas>
    <div id="node-info"></div>
</div>

<script>
// 使用 D3.js 或 simple-graph 库
class GraphVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.nodes = [];
        this.edges = [];
    }
    
    async loadGraph() {
        const response = await fetch('/api/neural-graph/data');
        const data = await response.json();
        this.nodes = data.nodes;
        this.edges = data.edges;
        this.render();
    }
    
    render() {
        // 渲染节点和边
        // 支持缩放、拖拽、点击查看详情
    }
}
</script>
```

---

## 五、与现有系统的集成

### 在 web_server.py 中添加端点

```python
@app.route("/api/neural-graph/stats")
def neural_graph_stats():
    from core.neural_graph import NeuralGraph
    graph = NeuralGraph()
    return jsonify(graph.get_stats())

@app.route("/api/neural-graph/related/<name>")
def neural_graph_related(name):
    from core.neural_graph import NeuralGraph
    graph = NeuralGraph()
    related = graph.get_related(name)
    return jsonify(related)

@app.route("/api/neural-graph/intent", methods=["POST"])
def neural_graph_intent():
    from core.neural_graph import NeuralGraph
    data = request.get_json()
    graph = NeuralGraph()
    intent = graph.recognize_intent(data.get("query", ""))
    return jsonify(intent)
```

---

_这个版本明确了技术选型、实施步骤，并提供了完整的代码框架。_
