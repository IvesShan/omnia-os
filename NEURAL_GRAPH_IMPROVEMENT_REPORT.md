# 神经图谱面板改进建议

## 📊 当前状态

### ✅ 已有功能
- **数据量**: 249 个节点，5286 条边
- **节点类型**: PERSON(30), PROJECT(44), FILE(114), CONCEPT(25), DATE(26), LOCATION(4), ENTITY(6)
- **关系类型**: BELONGS_TO, DEPENDS_ON, RELATED_TO, WORKED_ON, KNOWS_ABOUT 等
- **可视化方案**: 
  - 3D Force Graph (neural-graph.js)
  - Three.js 粒子风格 (neural-graph-porweb.js)
- **图算法**: 路径查找、中心度分析、社区发现

### ❌ 发现的问题

| 问题 | 严重性 | 描述 |
|------|--------|------|
| **端口不匹配** | 🔴 高 | 前端请求 `localhost:8765`，服务运行在 `5001` |
| **API 路径错误** | 🔴 高 | 前端使用 `/api/memory/stats`，实际是 `/api/neural-graph/stats` |
| **数据可视化有限** | 🟡 中 | 只显示节点和边，缺少交互和筛选 |
| **性能问题** | 🟡 中 | 5000+ 边全部加载，前端卡顿 |
| **缺少搜索功能** | 🟡 中 | 无法搜索特定节点 |
| **缺少时间维度** | 🟡 中 | 无法查看图谱演变历史 |

---

## 🚀 改进建议

### 第一阶段：修复关键问题（1 天）

#### 1. 修复端口和 API 路径

**问题**:
```javascript
// neural-graph-porweb.js 第 365 行
const response = await fetch('http://localhost:8765/api/memory/stats');
// ❌ 端口错误：应该是 5001
// ❌ 路径错误：应该是 /api/neural-graph/stats
```

**修复方案**:
```javascript
// 使用相对路径，自动适配当前端口
const response = await fetch('/api/neural-graph/stats');
```

#### 2. 修复数据库路径

**问题**:
```python
# memory_palace.py 第 23 行
self.db_path = Path("/home/shan/omnia-os/data/memory.db")
# ❌ 硬编码路径
```

**修复方案**:
```python
from core.config import MEMORY_PALACE_DB
self.db_path = MEMORY_PALACE_DB
```

---

### 第二阶段：功能增强（3 天）

#### 1. 添加节点搜索功能

**新增 API**:
```python
@app.route("/api/neural-graph/search", methods=["POST"])
def search_nodes():
    query = request.json.get("query", "")
    # 模糊搜索节点
    results = graph.search_nodes(query, limit=20)
    return jsonify(results)
```

**前端实现**:
```html
<div class="search-box">
  <input type="text" id="node-search" placeholder="搜索节点...">
  <div id="search-results"></div>
</div>
```

#### 2. 添加节点筛选功能

**按类型筛选**:
```javascript
function filterByType(type) {
  const visibleNodes = nodes.filter(n => n.type === type);
  updateGraph(visibleNodes);
}
```

**按关系筛选**:
```javascript
function filterByRelation(relation) {
  const visibleEdges = edges.filter(e => e.relation === relation);
  updateGraph(nodes, visibleEdges);
}
```

#### 3. 添加时间维度

**新增时间线视图**:
```javascript
function showTimeline() {
  // 按创建时间排序节点
  const sortedNodes = nodes.sort((a, b) => 
    new Date(a.created_at) - new Date(b.created_at)
  );
  
  // 显示时间轴
  renderTimeline(sortedNodes);
}
```

---

### 第三阶段：性能优化（2 天）

#### 1. 分页加载

**问题**: 一次性加载 5286 条边导致卡顿

**解决方案**:
```python
@app.route("/api/neural-graph/export")
def export_graph():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 100, type=int)
    
    # 分页查询
    offset = (page - 1) * per_page
    edges = query_edges(limit=per_page, offset=offset)
    return jsonify({
        "nodes": nodes,
        "edges": edges,
        "total": total_count,
        "page": page,
        "has_more": offset + per_page < total_count
    })
```

#### 2. 按需加载

**实现**:
```javascript
async function loadConnectedNodes(nodeId, depth = 1) {
  const response = await fetch(`/api/neural-graph/related/${nodeId}?depth=${depth}`);
  const data = await response.json();
  addToGraph(data.nodes, data.edges);
}
```

#### 3. WebGL 渲染优化

**使用 Pixi.js 或 Sigma.js**:
```javascript
// Sigma.js 更适合大规模图谱
import Sigma from 'sigma';
import Graph from 'graphology';

const graph = new Graph();
// 添加节点和边...
const renderer = new Sigma(graph, container);
```

---

### 第四阶段：交互增强（2 天）

#### 1. 节点详情面板

```html
<div class="node-detail" id="node-detail">
  <h3 id="node-name"></h3>
  <p id="node-type"></p>
  <div id="node-properties"></div>
  <div id="node-connections"></div>
</div>
```

#### 2. 路径查找功能

```javascript
async function findPath(sourceId, targetId) {
  const response = await fetch('/api/neural-graph/path', {
    method: 'POST',
    body: JSON.stringify({ source: sourceId, target: targetId })
  });
  const path = await response.json();
  highlightPath(path);
}
```

#### 3. 社区发现可视化

```javascript
async function showCommunities() {
  const response = await fetch('/api/neural-graph/communities');
  const communities = await response.json();
  
  // 为不同社区分配不同颜色
  communities.forEach((community, index) => {
    const color = COMMUNITY_COLORS[index % COMMUNITY_COLORS.length];
    community.nodes.forEach(node => {
      node.color = color;
    });
  });
  
  updateGraph();
}
```

---

### 第五阶段：数据质量改进（持续）

#### 1. 实体消歧

**问题**: "原点" 和 "用户" 可能是同一个人

**解决方案**:
```python
def merge_entities(entity1_id, entity2_id):
    """合并两个实体"""
    # 1. 合并属性
    # 2. 合并关系
    # 3. 删除重复实体
    pass
```

#### 2. 关系权重优化

**问题**: 大部分关系权重相同，无法区分重要性

**解决方案**:
```python
def calculate_relation_weight(source, target, relation_type):
    """根据多种因素计算关系权重"""
    weight = 0.5
    
    # 1. 共现频率
    weight += co_occurrence_count(source, target) * 0.1
    
    # 2. 时间衰减
    weight *= time_decay(last_accessed)
    
    # 3. 关系类型权重
    type_weights = {
        "WORKED_ON": 0.9,
        "KNOWS_ABOUT": 0.8,
        "RELATED_TO": 0.5
    }
    weight *= type_weights.get(relation_type, 0.5)
    
    return min(weight, 1.0)
```

#### 3. 自动实体识别

**集成 NLP**:
```python
def extract_entities_from_text(text):
    """从文本中自动提取实体"""
    # 使用 spaCy 或其他 NLP 工具
    entities = nlp(text).ents
    for entity in entities:
        add_node(entity.label_, entity.text)
```

---

## 📈 优先级排序

| 优先级 | 改进项 | 预计时间 | 影响 |
|--------|--------|----------|------|
| P0 | 修复端口和 API 路径 | 1 小时 | 🔴 关键 |
| P0 | 修复数据库路径 | 1 小时 | 🔴 关键 |
| P1 | 添加搜索功能 | 4 小时 | 🟡 重要 |
| P1 | 添加筛选功能 | 4 小时 | 🟡 重要 |
| P1 | 性能优化（分页） | 8 小时 | 🟡 重要 |
| P2 | 节点详情面板 | 4 小时 | 🟢 增强 |
| P2 | 路径查找功能 | 4 小时 | 🟢 增强 |
| P2 | 社区发现可视化 | 4 小时 | 🟢 增强 |
| P3 | 实体消歧 | 持续 | 🟢 增强 |
| P3 | 关系权重优化 | 持续 | 🟢 增强 |

---

## 🎯 快速修复清单

### 立即修复（30 分钟内）

1. **修复前端端口**
   - 文件: `src/frontend/static/js/neural-graph-porweb.js`
   - 行: 365, 398
   - 改为: `/api/neural-graph/stats`

2. **修复 API 路径**
   - 文件: `src/frontend/static/js/neural-graph-porweb.js`
   - 行: 398
   - 改为: `/api/neural-graph/export`

3. **添加缺失的 HTML 文件**
   - 创建: `src/frontend/static/neural.html`

---

## 📊 预期效果

修复后，神经图谱应该能够：
1. ✅ 正确显示 249 个节点
2. ✅ 正确显示 5286 条边
3. ✅ 支持节点搜索
4. ✅ 支持类型筛选
5. ✅ 流畅交互（60fps）

---

**生成时间**: 2026-04-29
**检查文件数**: 15
**发现问题数**: 6
**改进建议数**: 15
