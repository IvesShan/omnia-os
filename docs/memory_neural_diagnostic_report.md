# Omnia 记忆系统与神经图谱诊断报告

**诊断时间**: 2026-04-23 22:30  
**诊断范围**: 记忆系统、神经图谱系统、向量功能

---

## 📊 总体状态

| 系统 | 状态 | 说明 |
|------|------|------|
| 记忆系统 | ✅ 正常 | 数据库完整，功能正常 |
| 向量功能 | ✅ 已启用 | 语义搜索工作正常 |
| 神经图谱 | ⚠️ 部分正常 | 数据存在但覆盖率低 |

---

## 1. 记忆系统诊断

### 1.1 数据库状态

**主数据库**: `~/.omnia/memory_palace.db` (33.5 MB)

| 表 | 记录数 | Embedding 覆盖 | 状态 |
|----|--------|---------------|------|
| facts | 166 | 98.2% (163/166) | ✅ 优秀 |
| relations | 112 | 22.3% (25/112) | ⚠️ 需补充 |
| habits | 14 | 57.1% (8/14) | ✅ 良好 |
| timeline | 5710 | 54.9% (3135/5710) | ✅ 良好 |
| conversation_logs | 5796 | 100.0% (5796/5796) | ✅ 完美 |
| tool_logs | 6 | - | ✅ 正常 |

### 1.2 向量功能验证

- **向量服务**: HybridVectorService (本地模式)
- **嵌入维度**: 384 (符合预期)
- **嵌入类型**: float32
- **语义搜索**: ✅ 正常工作

**语义搜索测试结果**:
```
查询: "无人机维修"
结果数: 3
Top 1: omnia_independence (score: 0.143)
Top 2: 阶段 3.0 (score: 0.118)
Top 3: 确认日期 (score: 0.103)
```

### 1.3 问题发现

1. **旧数据库残留**: `/home/shan/omnia-os/data/memory_palace.db` 存在旧版本数据库
   - Schema 不匹配（缺少 embedding 列）
   - 建议：清理或迁移

2. **relations 表 embedding 覆盖率低**: 仅 22.3%
   - 影响：关系型记忆的语义搜索能力受限
   - 建议：批量补充 embedding

---

## 2. 神经图谱系统诊断

### 2.1 图谱规模

- **节点数**: 249 个
- **边数**: 5286 条
- **平均度**: 42.5 (密集图谱)

### 2.2 节点类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
| FILE | 114 | 45.8% |
| PROJECT | 44 | 17.7% |
| PERSON | 30 | 12.0% |
| DATE | 26 | 10.4% |
| CONCEPT | 25 | 10.0% |
| ENTITY | 6 | 2.4% |
| LOCATION | 4 | 1.6% |

### 2.3 关系类型分布

| 关系类型 | 数量 | 占比 |
|----------|------|------|
| DEPENDS_ON | 2097 | 39.6% |
| RELATED_TO | 1856 | 35.1% |
| BELONGS_TO | 1278 | 24.2% |
| WORKED_ON | 24 | 0.5% |
| 其他 | 31 | 0.6% |

### 2.4 问题发现

1. **Embedding 覆盖率极低**: 仅 6.8% (17/249)
   - 影响：图谱的语义检索能力受限
   - 建议：批量补充节点 embedding

2. **孤立节点较多**: 114 个节点无连接
   - 占比: 45.8%
   - 主要是 FILE 类型节点
   - 建议：清理或补充关系

3. **API 不完整**: NeuralGraph 缺少 `get_nodes` 方法
   - 影响：外部调用受限
   - 建议：补充 API

---

## 3. 向量服务诊断

### 3.1 服务架构

```
┌─────────────┐         Unix Socket        ┌─────────────┐
│ Web Server  │ ─────────────────────────→ │   Daemon    │
│  (client)   │                            │  (server)   │
│             │ ←─────────────────────────  │  (model)    │
└─────────────┘      vector results        └─────────────┘
```

### 3.2 服务状态

- **类型**: HybridVectorService
- **模式**: 本地模式 (fallback)
- **模型**: sentence-transformers (lazy load)
- **状态**: ✅ 正常工作

### 3.3 性能指标

- **嵌入维度**: 384
- **加载方式**: 按需加载
- **IPC 方式**: Unix Socket

---

## 4. 建议与修复方案

### 4.1 高优先级

1. **补充 relations 表 embedding**
   ```python
   # 批量补充脚本
   for relation in relations_without_embedding:
       embedding = vector_service.encode(relation.context)
       update_embedding(relation.id, embedding)
   ```

2. **补充 neural_nodes embedding**
   ```python
   # 批量补充脚本
   for node in nodes_without_embedding:
       text = f"{node.entity_name} {node.canonical_name}"
       embedding = vector_service.encode(text)
       update_node_embedding(node.id, embedding)
   ```

### 4.2 中优先级

3. **清理孤立节点**
   - 分析孤立原因
   - 补充关系或删除节点

4. **清理旧数据库**
   - 迁移 `/home/shan/omnia-os/data/memory_palace.db` 数据
   - 删除旧文件

### 4.3 低优先级

5. **补充 NeuralGraph API**
   - 添加 `get_nodes()` 方法
   - 添加 `get_edges()` 方法
   - 添加 `find_path()` 方法

---

## 5. 结论

### ✅ 正常的部分

- 记忆系统核心功能正常
- 向量服务已启用且工作正常
- 语义搜索功能正常
- 数据库结构正确

### ⚠️ 需要改进的部分

- relations 表 embedding 覆盖率低 (22.3%)
- neural_nodes embedding 覆盖率极低 (6.8%)
- 孤立节点较多 (45.8%)

### 📋 下一步行动

1. 运行 embedding 补充脚本
2. 清理孤立节点
3. 清理旧数据库文件

---

*报告生成时间: 2026-04-23 22:30*
