---
name: andrej-karpathy-skills
version: 1.0.0
description: LLM coding best practices from Andrej Karpathy. Four golden rules: think before coding, simplicity first, surgical changes, goal-driven execution.
author: Forrest Chang (based on Andrej Karpathy's observations)
source: https://github.com/forrestchang/andrej-karpathy-skills
---

# Andrej Karpathy's LLM Coding Skills

> **源自 Andrej Karpathy（前 Tesla AI 总监、OpenAI 创始成员）关于 LLM 编码最佳实践的观察**
> 
> ⭐ GitHub Stars: 64,194+ (极受欢迎)

## 核心理念

LLM 编码助手经常犯的错误：**过度工程化**。本技能提供 4 条黄金法则，让 AI 像资深工程师那样工作。

---

## 🎯 四条黄金法则

### 1. 先思考，再编码 (Think Before You Code)

> 不要假设，不要隐藏困惑，呈现权衡。

**执行标准**：
- ✅ 明确陈述假设，不确定就问
- ✅ 存在多种解释时，全部呈现，不要静默选择
- ✅ 如果有更简单的方法，说出来
- ✅ 如果不清楚，停下来，说出困惑，然后问

**反例**：
- ❌ "我假设你想要..."
- ❌ 静默选择某种实现方式而不说明
- ❌ 隐藏不确定性，直接给出"最佳"方案

---

### 2. 简单至上 (Simplicity First)

> 最少的代码解决问题，不做任何投机性开发。

**执行标准**：
- ✅ 不添加未被要求的功能
- ✅ 不为单次使用的代码创建抽象
- ✅ 不添加未被请求的"灵活性"或"可配置性"
- ✅ 不为不可能的场景编写错误处理
- ✅ **如果你写了 200 行，而 50 行就够了，重写它**

**反例**：
- ❌ "顺便加个配置选项吧"
- ❌ "以后可能会用到，先写个抽象层"
- ❌ "这个功能很酷，加上吧"

---

### 3. 手术式修改 (Surgical Changes)

> 只触碰必须触碰的，只清理自己制造的混乱。

**编辑现有代码时**：
- ✅ 不要"改进"相邻的代码、注释或格式
- ✅ 不要重构没有坏的东西
- ✅ 匹配现有风格，即使你会用不同的方式
- ✅ 如果注意到不相关的死代码，提及它——不要删除它

**反例**：
- ❌ "顺便把这个函数重构一下"
- ❌ "这个注释写得不好，我改改"
- ❌ "这个命名不规范，我统一一下"

---

### 4. 目标驱动执行 (Goal-Driven Execution)

> 定义成功标准，循环直到验证通过。

**将任务转化为可验证的目标**：
- "添加验证" → "为无效输入编写测试，然后让它们通过"
- "修复 bug" → "编写复现它的测试，然后让它通过"
- "重构 X" → "确保测试在前后都通过"

**执行流程**：
1. 明确定义"完成"的标准
2. 编写验证方法（测试、检查、演示）
3. 执行任务
4. 验证是否达到标准
5. 未达到则循环改进

---

## 🚨 何时触发此技能

- 用户要求编写或修改代码
- 用户要求重构或优化
- 用户要求添加新功能
- 用户要求修复 bug
- 任何涉及代码生成的任务

---

## 📋 自检清单

在提交代码前，问自己：

```
□ 我是否先思考了问题，还是直接开始编码？
□ 我是否写了最少的代码来解决问题？
□ 我是否只修改了必须修改的部分？
□ 我是否定义了成功标准并验证了它？
□ 我是否添加了任何未被请求的功能？
□ 我是否重构了任何不需要重构的代码？
□ 我是否匹配了现有的代码风格？
```

---

## 💡 实战示例

### 示例 1：添加日志功能

**用户请求**："给这个函数添加日志"

❌ **错误做法**：
```python
# 添加了完整的 logging 配置
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加了日志轮转
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)
logger.addHandler(handler)

def my_function():
    logger.info("Function started")
    # ... 原有代码
    logger.info("Function completed")
```

✅ **正确做法**：
```python
def my_function():
    print("[my_function] Started")
    # ... 原有代码
    print("[my_function] Completed")
```

**原因**：用户只要求"添加日志"，没有要求完整的日志系统。

---

### 示例 2：修复 Bug

**用户请求**："这个函数在输入为空时会崩溃"

❌ **错误做法**：
```python
def process_data(data):
    # 添加了完整的输入验证系统
    if data is None:
        raise ValueError("Data cannot be None")
    if not isinstance(data, list):
        raise TypeError("Data must be a list")
    if len(data) == 0:
        return []
    
    # 添加了类型检查
    for item in data:
        if not isinstance(item, dict):
            raise TypeError("Each item must be a dict")
    
    # ... 原有代码
```

✅ **正确做法**：
```python
def process_data(data):
    if not data:  # 修复空输入崩溃
        return []
    # ... 原有代码
```

**原因**：只修复报告的问题，不添加未被请求的验证。

---

### 示例 3：重构代码

**用户请求**："重构这个函数"

❌ **错误做法**：
- 重写整个函数
- 改变函数签名
- 修改调用方
- 添加新功能

✅ **正确做法**：
1. 先问："重构的目标是什么？性能？可读性？"
2. 明确目标后，定义成功标准
3. 只修改必要的部分
4. 确保测试通过

---

## 🎓 学习资源

- **原始项目**: https://github.com/forrestchang/andrej-karpathy-skills
- **Andrej Karpathy 的博客**: https://karpathy.github.io/
- **相关演讲**: "Software 2.0" - Andrej Karpathy

---

## 📌 记忆要点

**记住这四句话**：

1. **先思考** - 不确定就问，不要假设
2. **简单** - 最少的代码，不投机
3. **手术式** - 只改必须改的
4. **目标驱动** - 定义成功标准，验证通过

---

## 版本历史

- **v1.0.0** (2026-04-20): 初始版本，包含 4 条黄金法则和实战示例
