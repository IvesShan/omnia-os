# P1 集成计划

## 状态总结

### ✅ P0 已完成
- [x] 清理重复记忆 (5710 → 1902)
- [x] 修复记忆存储逻辑 (数据验证 + 去重)
- [x] 补全 Embedding (100% 覆盖)

### 🔄 P1 待集成

| 模块 | 文件位置 | 状态 | 集成点 |
|------|----------|------|--------|
| MLA 压缩器 | `src/core/memory/mla_compressor.py` | ✅ 已实现 | 未接入 |
| 循环推理引擎 | `src/core/openmythos/recurrent_engine.py` | ✅ 已实现 | 未接入 |
| OmniaChatEngine | `src/core/openmythos/omnia_chat_engine.py` | ✅ 已实现 | 未接入 |

---

## 1. MLA 压缩器集成

### 目标
- 在记忆检索时压缩 context
- 减少内存占用和 API token 消耗

### 集成方案
```python
# 在 MemoryPalace.recall_* 方法中
from core.memory.mla_compressor import create_mla_compressor

class MemoryPalace:
    def __init__(self):
        self.compressor = create_mla_compressor()
    
    def search_semantic(self, query, top_k=10):
        # 检索记忆
        results = self._raw_search(query, top_k)
        
        # 压缩结果
        compressed = self.compressor.compress_batch(results)
        return compressed
```

### 预期收益
- Context 长度减少 ~12x
- 检索速度提升 ~3-5x

---

## 2. 循环推理引擎集成

### 目标
- 对复杂问题进行多轮自我反思
- 动态停机，避免过度推理

### 集成方案
```python
# 在 chat.py 或 web_server.py 中
from core.openmythos import RecurrentReasoning

def chat_with_reasoning(message: str, complexity: str = "auto"):
    # 检测问题复杂度
    if complexity == "auto":
        complexity = detect_complexity(message)
    
    if complexity == "high":
        # 使用循环推理
        engine = RecurrentReasoning(
            model_call=call_llm,
            max_iterations=8,
            confidence_threshold=0.85
        )
        result = engine.reason(message)
        return result.final_answer
    else:
        # 直接回答
        return call_llm(message)
```

### 触发条件
- 用户明确要求"深入分析"
- 检测到复杂问题（代码、数学、逻辑推理）
- 用户追问"为什么"或"如何"

---

## 3. 技能系统检查

### 当前状态
- 26 个技能已导入
- 但激活状态未知

### 检查脚本
```bash
python3 -c "
from core.skill_registry import SkillRegistry
registry = SkillRegistry()
for skill in registry.list_skills():
    print(f'{skill.name}: {skill.status}')
"
```

---

## 实施优先级

1. **MLA 压缩器** - 低风险，高收益
2. **技能系统检查** - 快速诊断
3. **循环推理引擎** - 需要更多测试

---

## 下一步行动

- [ ] 创建 MLA 集成 PR
- [ ] 运行技能系统检查
- [ ] 测试循环推理引擎
- [ ] 更新 SELF_KNOWLEDGE.md
