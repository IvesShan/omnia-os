# 神经图谱（Neural Graph）系统规划

## 概述

在 Omnia 空闲时，自动关联记忆内容，建立实体关系网络。
当用户查询时，快速识别意图并提供关联信息。

---

## 一、系统架构

```
输入: 用户消息 / 空闲触发
         │
         ▼
┌─────────────────────────────────────────────┐
│           实体抽取层 (NER)                   │
│  - 人物、项目、事件、概念、文件、日期         │
│  - 自动识别并标准化                          │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│           关系推理层                         │
│  - 语义关系 (属于、相关、依赖)                │
│  - 时序关系 (之前、之后、期间)                │
│  - 因果关系 (导致、影响、解决)                │
│  - 协作关系 (一起、委托、协作)                │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│           图谱存储层                         │
│  - Nodes (实体节点)                          │
│  - Edges (关系边)                            │
│  - Weights (关联强度)                        │
│  - Timestamps (时间戳)                       │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│           向量嵌入层                         │
│  - Node embeddings (节点向量)                │
│  - Graph embeddings (图向量)                 │
│  - Path embeddings (路径向量)                │
└─────────────────────────────────────────────┘
         │
         ▼
输出: 关联查询、意图识别、上下文推理
```

---

## 二、核心组件设计

### 1. 实体抽取器 (EntityExtractor)

```python
class EntityExtractor:
    """从文本中抽取实体"""
    
    def extract(self, text: str) -> List[Entity]:
        """
        实体类型:
        - PERSON: 人物 (原点, 无限, 李先生)
        - PROJECT: 项目 (喵修匠, 懂机帝, Omnia)
        - FILE: 文件 (README.md, config.json)
        - EVENT: 事件 (会议, 部署, 修复)
        - CONCEPT: 概念 (协作, 记忆, 工具调用)
        - DATE: 日期 (今天, 4月18日)
        - LOCATION: 位置 (本地, 云端)
        """
        pass
```

### 2. 关系推理器 (RelationInferencer)

```python
class RelationInferencer:
    """推理实体之间的关系"""
    
    def infer(self, entity1: Entity, entity2: Entity, context: str) -> Relation:
        """
        关系类型:
        - BELONGS_TO: 属于 (无限 -> OpenClaw)
        - RELATED_TO: 相关 (Omnia <-> 无限)
        - DEPENDS_ON: 依赖 (前端 -> 后端)
        - CAUSED_BY: 导致 (错误 -> 修复)
        - WORKED_ON: 工作 (原点 -> 喵修匠)
        - KNOWS_ABOUT: 了解 (无限 -> 喵修匠)
        - COLLABORATES_WITH: 协作 (Omnia <-> 无限)
        """
        pass
```

### 3. 图谱构建器 (GraphBuilder)

```python
class NeuralGraphBuilder:
    """构建和更新神经图谱"""
    
    def __init__(self, db_path: str):
        self.db = GraphDatabase(db_path)
    
    def add_entity(self, entity: Entity) -> Node:
        """添加实体节点"""
        pass
    
    def add_relation(self, relation: Relation) -> Edge:
        """添加关系边"""
        pass
    
    def strengthen_edge(self, edge_id: str, delta: float = 0.1):
        """强化关系（每次使用后加强）"""
        pass
    
    def decay_unused(self, days: int = 30):
        """衰减未使用的关系"""
        pass
```

### 4. 意图识别器 (IntentRecognizer)

```python
class IntentRecognizer:
    """基于图谱快速识别用户意图"""
    
    def recognize(self, query: str, graph: NeuralGraph) -> Intent:
        """
        步骤:
        1. 抽取查询中的实体
        2. 在图谱中找到相关节点
        3. 计算子图相关性
        4. 返回最可能的意图
        
        输出:
        - primary_topic: 主要话题
        - related_topics: 相关话题
        - confidence: 置信度
        - context_nodes: 上下文节点
        """
        pass
```

### 5. 空闲处理器 (IdleProcessor)

```python
class IdleProcessor:
    """在 Omnia 空闲时自动处理"""
    
    def __init__(self, graph_builder: NeuralGraphBuilder):
        self.builder = graph_builder
        self.last_processed = None
    
    def process_batch(self, memories: List[Memory]):
        """批量处理记忆"""
        for memory in memories:
            entities = self.extractor.extract(memory.content)
            relations = self.inferencer.infer_batch(entities, memory.content)
            self.builder.add_batch(entities, relations)
    
    def consolidate(self):
        """整合弱关系，强化强关系"""
        pass
    
    def prune_obsolete(self):
        """清理过时关系"""
        pass
```

---

## 三、数据库设计

### 节点表 (nodes)

```sql
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,           -- PERSON/PROJECT/FILE/EVENT/CONCEPT/DATE/LOCATION
    name TEXT NOT NULL,
    canonical_name TEXT,          -- 标准化名称
    aliases TEXT,                 -- JSON array of aliases
    properties TEXT,              -- JSON object of properties
    created_at TEXT,
    updated_at TEXT,
    access_count INTEGER DEFAULT 0
);
```

### 边表 (edges)

```sql
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,  -- BELONGS_TO/RELATED_TO/DEPENDS_ON/...
    weight REAL DEFAULT 0.5,      -- 关联强度 0-1
    evidence TEXT,                -- 证据文本
    source_memory_id TEXT,        -- 来源记忆ID
    created_at TEXT,
    last_accessed TEXT,
    access_count INTEGER DEFAULT 0,
    FOREIGN KEY (source_id) REFERENCES nodes(id),
    FOREIGN KEY (target_id) REFERENCES nodes(id)
);
```

### 向量表 (embeddings)

```sql
CREATE TABLE embeddings (
    node_id TEXT PRIMARY KEY,
    embedding BLOB,               -- 序列化的向量
    model TEXT,                   -- 使用的嵌入模型
    updated_at TEXT,
    FOREIGN KEY (node_id) REFERENCES nodes(id)
);
```

---

## 四、触发机制

### 空闲检测

```python
class IdleDetector:
    """检测 Omnia 是否空闲"""
    
    IDLE_THRESHOLD = 300  # 5分钟无交互
    
    def is_idle(self) -> bool:
        last_interaction = self.get_last_interaction_time()
        return (datetime.now() - last_interaction).seconds > self.IDLE_THRESHOLD
    
    def get_idle_duration(self) -> int:
        """返回空闲时长（秒）"""
        pass
```

### 处理调度

```python
# 在 Omnia 的主循环中
async def idle_processing_loop():
    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        
        if idle_detector.is_idle():
            # 获取未处理的记忆
            unprocessed = memory_store.get_unprocessed()
            
            if unprocessed:
                # 批量处理
                idle_processor.process_batch(unprocessed)
                
                # 图谱整合
                idle_processor.consolidate()
```

---

## 五、查询增强

### 关联查询

```python
def enhanced_search(query: str) -> SearchResult:
    """增强搜索，自动关联相关内容"""
    
    # 1. 标准向量搜索
    vector_results = vector_store.search(query)
    
    # 2. 图谱关联查询
    entities = entity_extractor.extract(query)
    graph_nodes = graph.find_related(entities)
    
    # 3. 意图识别
    intent = intent_recognizer.recognize(query, graph)
    
    # 4. 合并结果
    return SearchResult(
        primary_results=vector_results,
        related_entities=graph_nodes,
        detected_intent=intent,
        suggested_context=intent.context_nodes
    )
```

### 意图识别示例

```python
# 用户输入: "喵修匠怎么样了"

# 图谱查询:
entities = ["喵修匠"]
related = graph.get_relations("喵修匠")
# 返回:
# - 喵修匠 --BELONGS_TO--> 原点
# - 喵修匠 --HAS_STATUS--> 活跃
# - 喵修匠 --DEPENDS_ON--> miaoxiujiang-api
# - 喵修匠 --WORKED_ON_BY--> 无限 (最近)
# - 喵修匠 --HAS_FILES--> merchant.html, server_v2.py

# 意图识别:
intent = {
    "primary_topic": "喵修匠",
    "intent_type": "STATUS_CHECK",
    "context": ["原点", "活跃", "miaoxiujiang-api"],
    "suggested_query": "喵修匠项目状态如何？最近有什么更新？"
}
```

---

## 六、改进建议

### 1. 实体消歧

**问题**: "无限"可能指 AI助手，也可能指"无限手套"

**解决方案**:
```python
class EntityDisambiguator:
    def disambiguate(self, entity: str, context: str) -> Entity:
        # 1. 检查上下文关键词
        # 2. 查询图谱中已有的同实体
        # 3. 计算上下文相似度
        # 4. 返回最可能的实体
        pass
```

### 2. 关系强度衰减

**问题**: 旧的关系可能不再相关

**解决方案**:
```python
def decay_weights():
    """每天衰减未访问的关系"""
    DECAY_RATE = 0.95
    MIN_WEIGHT = 0.1
    
    for edge in graph.get_edges():
        if edge.last_accessed < (now - timedelta(days=30)):
            edge.weight *= DECAY_RATE
            if edge.weight < MIN_WEIGHT:
                graph.remove_edge(edge.id)
```

### 3. 主动关联建议

**功能**: 在用户对话时，主动提示相关内容

```python
# 用户: "我在做喵修匠的..."

# 系统检测到 "喵修匠" 节点
related = graph.get_high_weight_relations("喵修匠")

# 主动建议:
suggestions = [
    "喵修匠最近更新了商户工作台",
    "miaoxiujiang-api 后端需要启动",
    "有关 Omnia 协作的新功能"
]
```

### 4. 多模态关联

**扩展**: 不仅关联文本，还关联:
- 文件 (代码、文档)
- 图片 (截图、设计图)
- 对话记录
- Shell 命令历史

```python
class MultiModalLinker:
    def link(self, node: Node, resource: Resource):
        """关联多模态资源"""
        pass
```

### 5. 图谱可视化

**功能**: 在 Web UI 中可视化神经图谱

```
用户可以:
- 浏览节点网络
- 查看关系强度
- 手动添加/删除关系
- 搜索特定实体
```

---

## 七、实施步骤

### Phase 1: 基础框架 (1-2天)

- [ ] 创建图谱数据库 schema
- [ ] 实现实体抽取器
- [ ] 实现关系推理器
- [ ] 基础的图谱构建

### Phase 2: 空闲处理 (1-2天)

- [ ] 实现空闲检测
- [ ] 批量处理记忆
- [ ] 图谱整合逻辑

### Phase 3: 查询增强 (1-2天)

- [ ] 意图识别器
- [ ] 关联查询
- [ ] 搜索结果增强

### Phase 4: 优化改进 (持续)

- [ ] 实体消歧
- [ ] 关系衰减
- [ ] 主动建议
- [ ] 图谱可视化

---

## 八、预期效果

### Before (当前)

```
用户: "喵修匠怎么样了"
系统: [搜索记忆] -> 返回最近的记录
```

### After (神经图谱)

```
用户: "喵修匠怎么样了"
系统: 
  1. [图谱查询] 喵修匠节点
  2. [关联推理] 
     - 状态: 活跃
     - 最近工作: 商户工作台 (4月17日)
     - 相关组件: miaoxiujiang-api
     - 关联项目: Omnia 协作
  3. [意图识别] STATUS_CHECK
  4. [返回] 
     "喵修匠项目状态: 活跃
      最近更新: 商户工作台前端 (4月17日)
      注意: 后端服务未运行
      相关: 已集成 Omnia 协作功能"
```

---

## 九、性能指标

| 指标 | 目标 |
|------|------|
| 实体抽取速度 | < 100ms |
| 图谱查询速度 | < 50ms |
| 意图识别速度 | < 200ms |
| 空闲处理吞吐 | 100条/秒 |
| 图谱大小 | < 10MB (10万节点) |

---

## 十、风险与缓解

| 风险 | 缓解方案 |
|------|----------|
| 实体抽取不准确 | 人工校验 + 反馈学习 |
| 关系过度生长 | 定期衰减 + 重要性阈值 |
| 性能下降 | 分片存储 + 缓存热点 |
| 隐私问题 | 本地存储 + 加密敏感信息 |

---

_这是一个强大的记忆增强系统，能让 Omnia 真正"理解"用户的世界！_
