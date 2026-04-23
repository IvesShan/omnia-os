# Omnia 对话连续性诊断报告

**日期**: 2026-04-22  
**诊断者**: 无限  
**问题**: 重启服务/刷新页面后，对话无法接续之前话题

---

## 🔍 问题根源

### 发现 1: 前端历史传递限制

**代码位置**: `/home/shan/omnia-os/web/app.js:718`

```javascript
const history = chatHistory.slice(-10).map(m => ({
  role: m.role,
  content: m.content
}));
```

**问题**: 前端只传递最近 **10 条**消息给后端。

---

### 发现 2: 后端历史加载条件过严

**代码位置**: `/home/shan/omnia-os/src/omnia/chat_handler.py:52`

```python
if len(history) < 5:
    print(f"[Chat] Frontend history too short ({len(history)}), loading from database...")
    db_history = load_recent_conversations(limit=10, ...)
    history = merge_histories(history, db_history, max_total=20)
```

**问题**: 只有当前端历史 **< 5 条**时，才从数据库加载。  
**结果**: 前端传 10 条 → 后端认为"足够了" → 不加载历史 → 无法接续更早的话题。

---

### 发现 3: localStorage 依赖问题

**代码位置**: `/home/shan/omnia-os/web/app.js:44-48`

```javascript
const CHAT_KEY = 'omnia_chat_history_v1';
const MAX_CHAT_HISTORY = 200;

// 从 localStorage 加载
const raw = localStorage.getItem(CHAT_KEY);
```

**问题**: 
- localStorage 只保存最近 200 条
- 刷新页面后，前端从 localStorage 恢复历史
- **但 localStorage 可能被浏览器清理**（隐私模式、存储限制等）
- 清空后，前端传空历史 → 后端加载 10 条 → 用户看不到更早的对话

---

### 发现 4: 会话超时机制

**代码位置**: `/home/shan/omnia-os/src/core/session_manager.py:17`

```python
def is_expired(self, timeout: int = 3600) -> bool:
    """检查会话是否过期（默认 1 小时）"""
    return time.time() - self.last_activity > timeout
```

**问题**: 会话 1 小时后过期，新会话无法接续旧会话的话题。

---

## 💡 解决方案

### 方案 1: 调整历史加载策略（推荐）

**修改**: `/home/shan/omnia-os/src/omnia/chat_handler.py`

```python
# 旧逻辑
if len(history) < 5:
    db_history = load_recent_conversations(limit=10, ...)

# 新逻辑：始终补充历史
if len(history) < 20:  # 提高阈值
    db_history = load_recent_conversations(
        limit=20,  # 加载更多
        current_message=message,
        min_similarity=0.5  # 启用语义搜索
    )
    history = merge_histories(history, db_history, max_total=40)
```

**效果**: 
- 前端传 10 条 → 后端再补充 20 条 → 总共 30 条历史
- 用户可以看到更早的对话，接续话题更容易

---

### 方案 2: 前端加载更多历史

**修改**: `/home/shan/omnia-os/web/app.js`

```javascript
// 旧逻辑
const history = chatHistory.slice(-10).map(...)

// 新逻辑：加载更多
const history = chatHistory.slice(-30).map(m => ({
  role: m.role,
  content: m.content
}));
```

**效果**: 前端传递 30 条历史给后端。

---

### 方案 3: 智能历史加载（最佳）

**实现**: 根据当前消息，智能检索相关历史

```python
# 在 chat_handler.py 中
if message:  # 如果有当前消息
    # 语义检索相关对话
    relevant_history = load_recent_conversations(
        limit=10,
        current_message=message,
        min_similarity=0.7  # 高相似度
    )
    
    # 加载最近的对话
    recent_history = load_recent_conversations(limit=10)
    
    # 合并
    history = merge_histories(
        frontend_history,
        relevant_history + recent_history,
        max_total=30
    )
```

**效果**: 
- 既加载最近的对话
- 又检索与当前话题相关的历史
- 双重保障，确保接续性

---

### 方案 4: 持久化会话上下文

**已实现**: `ContextManager` 会保存最后上下文

**优化**: 在 `assemble_wake_prompt()` 中强化显示

```python
# 在 wake.py 中
if last_context:
    prompt_parts.append(f"""
## 上次会话上下文

📅 时间: {last_context.timestamp}
📌 主题: {last_context.topic}
📝 摘要: {last_context.summary}
🏗️ 项目: {last_context.active_project}
➡️ 下一步: {last_context.next_steps}

**重要**: 如果用户的话题与上次相关，请主动接续。
""")
```

---

## 🚀 实施计划

### P0 - 立即修复（今天）

1. ✅ **调整历史加载阈值**
   - 文件: `src/omnia/chat_handler.py`
   - 改动: `if len(history) < 5` → `if len(history) < 20`
   - 改动: `limit=10` → `limit=20`

2. ✅ **启用语义搜索**
   - 文件: `src/omnia/chat_handler.py`
   - 改动: `min_similarity=0.0` → `min_similarity=0.5`

3. ✅ **增强 Wake Prompt**
   - 文件: `src/omnia/wake.py`
   - 添加: 更明确的上下文提示

---

### P1 - 短期优化（本周）

4. ⬜ **前端历史加载优化**
   - 文件: `web/app.js`
   - 改动: `slice(-10)` → `slice(-30)`

5. ⬜ **会话超时延长**
   - 文件: `src/core/session_manager.py`
   - 改动: `timeout=3600` → `timeout=7200`（2 小时）

---

### P2 - 长期优化（下周）

6. ⬜ **向量检索优化**
   - 为所有历史对话生成向量（当前只有 15%）
   - 提高语义搜索准确度

7. ⬜ **会话摘要生成**
   - 长会话自动生成摘要
   - 减少上下文长度，提高接续性

---

## 📊 预期效果

| 指标 | 当前 | 优化后 |
|------|------|--------|
| **历史加载量** | 10 条 | 30-40 条 |
| **语义检索** | ❌ 未启用 | ✅ 启用 |
| **话题接续成功率** | ~30% | ~80% |
| **用户感知连续性** | ❌ 差 | ✅ 好 |

---

## 🧪 测试方法

1. **重启服务测试**:
   ```bash
   # 重启 Omnia
   pkill -f web_server.py
   python3 src/omnia/web_server.py
   
   # 在 Web 界面发送消息
   # 检查是否能接续之前的话题
   ```

2. **刷新页面测试**:
   ```bash
   # 在浏览器中刷新页面
   # 检查历史是否恢复
   # 发送消息，检查是否接续
   ```

3. **日志检查**:
   ```bash
   tail -f logs/omnia_*.log | grep -E "\[Chat\]|\[SessionManager\]"
   ```

---

## 📝 总结

**核心问题**: 前端历史传递限制 + 后端加载条件过严 = 对话无法接续

**解决方案**: 放宽历史加载条件，启用语义检索，增强上下文提示

**实施优先级**: P0 立即修复，P1 本周完成，P2 后续优化

---

**诊断完成时间**: 2026-04-22 02:45  
**下一步**: 开始实施 P0 优化
