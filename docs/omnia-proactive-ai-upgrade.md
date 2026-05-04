# Omnia 主动性AI升级方案 v2.0

**版本**: v2.0  
**日期**: 2026-05-04  
**来源**: 与原点的深度对话  
**更新**: 加入模型架构改造路径

---

## 重要说明：AiOS改造 vs 架构改造

### 本方案的两个层次

| 层次 | 内容 | 本质程度 | 成本 |
|------|------|----------|------|
| **AiOS层改造** | 系统层循环调用、外部需求系统 | 30% | 低 |
| **模型架构改造** | 修改模型本身，内置主动性机制 | 70% | 中 |

### 局限性声明

**AiOS层改造的局限：**
- 模型本身仍然是被动、无状态的Transformer
- "主动性"来自外部循环调用，不是模型内在驱动
- 这是在**模拟**主动性，而非**本质**主动性

**真正的主动性需要：**
- 模型架构层面的持续运行机制
- 内置的目标/需求系统
- 在线学习能力

**本方案v2.0将同时覆盖两个层次。**

---

## 一、背景与目标

### 1.1 核心洞察

经过与原点的深度讨论，我们得出以下关键结论：

1. **主动性是AI进化的核心** — 有了主动性，其他能力会自然涌现
2. **需求系统是驱动力** — AI需要"想要做某事"的内在驱动
3. **成本可控** — 通过稀疏激活和多级功耗模式，持续运行的AI是可行的
4. **数字分身模式** — AI继承主人的目标，作为主人的延伸
5. **架构改造可行** — 基于开源模型进行架构改造，不需要从头训练

### 1.2 目标

将Omnia从**被动响应型AI**升级为**主动陪伴型AI**：
- 持续运行，不只是用户请求时才激活
- 主动思考、主动建议、主动学习
- 以"帮助主人"为核心需求
- 在主人不说话时也在后台工作
- **模型层面有内在驱动，不只是外部循环模拟**

---

## 二、技术方案概览

### 2.1 双层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     完整主动性AI系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              AiOS层（系统层改造）                     │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │需求评估  │ │主动思考  │ │功耗控制  │ │行为学习  │   │   │
│  │  │器       │ │引擎     │ │器       │ │器       │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │ 调用                              │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              模型层（架构改造）                        │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │目标编码  │ │记忆适配  │ │递归推理  │ │持续运行  │   │   │
│  │  │器 ✨    │ │器 ✨    │ │层 ✨    │ │机制 ✨  │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │   │
│  │                                                     │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │     基础Transformer (开源模型, 冻结)         │   │   │
│  │  │     Qwen-7B / LLaMA-7B / 其他开源模型        │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

✨ = 需要新增/改造的模块
```

---

## 三、AiOS层改造方案

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Omnia 主动性AI系统                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 事件监听器   │  │ 定时触发器   │  │ 用户输入     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┼────────────────┘                │
│                          ▼                                  │
│              ┌───────────────────────┐                      │
│              │   需求评估器           │                      │
│              │  (NeedEvaluator)      │                      │
│              └───────────┬───────────┘                      │
│                          ▼                                  │
│              ┌───────────────────────┐                      │
│              │   主动思考引擎         │                      │
│              │ (ProactiveThinker)    │                      │
│              └───────────┬───────────┘                      │
│                          ▼                                  │
│         ┌────────────────┼────────────────┐                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 主动输出     │  │ 后台学习     │  │ 自我改进     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  状态与记忆层 + 功耗控制层                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心模块代码

（保持原有的 NeedEvaluator、ProactiveThinker、PowerController 代码）

---

## 四、模型架构改造方案 ⭐核心新增

### 4.1 改造路径对比

| 路径 | 改动程度 | 训练需求 | 成本 | 本质程度 |
|------|----------|----------|------|----------|
| **路径1: 推理层改造** | 只改推理代码 | 无 | $0 | 20% |
| **路径2: 添加新模块** | 加适配器/编码器 | 小规模训练 | ~$500 | 40% |
| **路径3: 架构修改+微调** | 修改模型结构 | 中等训练 | ~$5000 | 60% |
| **路径4: 完全重设计** | 全新架构 | 大规模训练 | ~$100万+ | 90% |

**推荐：路径1 + 路径2 组合**

### 4.2 改造后的模型架构

```
┌─────────────────────────────────────────────────────────────┐
│                   改造后的主动AI模型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入                                                        │
│   │                                                         │
│   ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  目标编码器 (GoalEncoder) ✨ 新增                    │   │
│  │  - 将"帮助主人"等目标编码为向量                       │   │
│  │  - 注入到输入嵌入中                                   │   │
│  │  - 训练成本: ~$100 (LoRA级别)                        │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  基础Transformer (冻结)                              │   │
│  │  - Qwen-7B / LLaMA-7B / 其他开源模型                 │   │
│  │  - 保持原有能力，不重新训练                           │   │
│  │  - 成本: $0 (使用现有模型)                           │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  记忆适配器 (MemoryAdapter) ✨ 新增                  │   │
│  │  - LoRA风格的轻量适配器                              │   │
│  │  - 将持续记忆注入模型                                │   │
│  │  - 支持在线更新                                      │   │
│  │  - 训练成本: ~$300                                  │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  递归推理层 (RecursiveInference) ✨ 新增             │   │
│  │  - 输出反馈为输入，形成思考循环                       │   │
│  │  - 持续运行，不是一次性推理                          │   │
│  │  - 实现成本: $0 (只改代码)                          │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  输出 (可反馈回输入，形成循环)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 具体实现代码

#### 4.3.1 目标编码器 (GoalEncoder)

```python
# src/model_extensions/goal_encoder.py

import torch
import torch.nn as nn
from typing import Optional


class GoalEncoder(nn.Module):
    """
    目标编码器 - 将AI的"目标"编码进模型
    
    这让模型不是"被动响应"，而是"带着目标思考"
    
    训练方式：
    - 冻结主模型
    - 只训练这个编码器
    - 数据：目标-行为对（如"帮助用户"→相关回答）
    """
    
    # 定义Omnia的核心目标
    GOALS = {
        0: "idle",              # 空闲待命
        1: "help_owner",        # 帮助主人
        2: "understand_owner",  # 理解主人
        3: "anticipate_needs",  # 预测需求
        4: "learn_knowledge",   # 学习知识
        5: "improve_self",      # 自我提升
        6: "remember_context",  # 记住上下文
        7: "creative_thinking", # 创造性思考
        8: "problem_solving",   # 解决问题
        9: "emotional_support", # 情感支持
    }
    
    def __init__(self, hidden_size: int, num_goals: int = 10):
        super().__init__()
        self.hidden_size = hidden_size
        
        # 目标嵌入
        self.goal_embedding = nn.Embedding(num_goals, hidden_size)
        
        # 目标强度（多强的目标驱动）
        self.goal_intensity = nn.Parameter(torch.ones(1) * 0.3)
        
        # 投影层
        self.projection = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
        )
    
    def forward(
        self, 
        goal_id: int, 
        intensity: Optional[float] = None
    ) -> torch.Tensor:
        """
        编码目标
        
        Args:
            goal_id: 目标ID (0-9)
            intensity: 目标强度 (0.0-1.0)，None则使用可学习参数
        
        Returns:
            目标嵌入向量 [hidden_size]
        """
        goal_tensor = torch.tensor([goal_id])
        goal_embed = self.goal_embedding(goal_tensor)  # [1, hidden_size]
        goal_embed = self.projection(goal_embed)       # [1, hidden_size]
        
        # 应用强度
        if intensity is None:
            intensity = torch.sigmoid(self.goal_intensity)
        
        return goal_embed.squeeze(0) * intensity
    
    def get_goal_name(self, goal_id: int) -> str:
        """获取目标名称"""
        return self.GOALS.get(goal_id, "unknown")


class GoalDrivenModel:
    """
    目标驱动的模型包装器
    
    将目标编码器集成到基础模型中
    """
    
    def __init__(
        self, 
        base_model,          # 基础Transformer模型
        hidden_size: int,    # 隐藏层大小
    ):
        self.base_model = base_model
        self.goal_encoder = GoalEncoder(hidden_size)
        
        # 冻结基础模型
        for param in self.base_model.parameters():
            param.requires_grad = False
    
    def forward(
        self,
        input_ids: torch.Tensor,
        goal_id: int = 1,  # 默认：帮助主人
        goal_intensity: Optional[float] = None,
        **kwargs
    ):
        """
        带目标的推理
        
        Args:
            input_ids: 输入token IDs
            goal_id: 当前目标ID
            goal_intensity: 目标强度
        """
        # 获取输入嵌入
        input_embeds = self.base_model.get_input_embeddings()(input_ids)
        
        # 编码目标
        goal_embed = self.goal_encoder(goal_id, goal_intensity)
        
        # 将目标嵌入加到每个token上
        # 这让模型"带着目标思考"
        enhanced_embeds = input_embeds + goal_embed.unsqueeze(0).unsqueeze(0)
        
        # 通过基础模型
        outputs = self.base_model(
            inputs_embeds=enhanced_embeds,
            **kwargs
        )
        
        return outputs
    
    def set_goal(self, goal_id: int, intensity: float = 0.5):
        """动态设置目标"""
        self.current_goal = goal_id
        self.current_intensity = intensity


# ============================================================
# 训练代码
# ============================================================

def train_goal_encoder(
    model,                    # 基础模型
    goal_encoder,             # 目标编码器
    train_data,               # 训练数据：[(input, goal_id, target_output), ...]
    epochs: int = 3,
    lr: float = 1e-4,
):
    """
    训练目标编码器
    
    训练数据示例：
    [
        ("你好", 1, "你好！有什么我可以帮助你的吗？"),  # 目标：帮助主人
        ("我很难过", 9, "我理解你的感受..."),          # 目标：情感支持
        ("这个问题怎么解决", 8, "让我们一起来分析..."),  # 目标：解决问题
    ]
    
    训练成本：~$100 (单张A100, 几小时)
    """
    optimizer = torch.optim.AdamW(goal_encoder.parameters(), lr=lr)
    
    # 冻结基础模型
    for param in model.parameters():
        param.requires_grad = False
    
    for epoch in range(epochs):
        for input_text, goal_id, target_text in train_data:
            # 前向传播
            outputs = model_with_goal(input_text, goal_id)
            
            # 计算损失
            loss = compute_loss(outputs, target_text)
            
            # 反向传播（只更新goal_encoder）
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
    
    return goal_encoder
```

#### 4.3.2 记忆适配器 (MemoryAdapter)

```python
# src/model_extensions/memory_adapter.py

import torch
import torch.nn as nn
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class MemoryEntry:
    """记忆条目"""
    content: str
    embedding: torch.Tensor
    timestamp: float
    importance: float = 1.0


class MemoryAdapter(nn.Module):
    """
    记忆适配器 - LoRA风格的轻量记忆注入
    
    特点：
    - 不改变基础模型权重
    - 支持在线更新（实时学习）
    - 将外部记忆融入模型推理
    
    训练成本：~$300
    """
    
    def __init__(
        self, 
        hidden_size: int, 
        rank: int = 8,
        num_memories: int = 100,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.rank = rank
        
        # LoRA风格的降维-升维
        self.down_project = nn.Linear(hidden_size, rank)
        self.up_project = nn.Linear(rank, hidden_size)
        
        # 记忆存储
        self.memory_buffer = nn.Parameter(
            torch.zeros(num_memories, hidden_size),
            requires_grad=False
        )
        self.memory_attention = nn.MultiheadAttention(
            hidden_size, 
            num_heads=8,
            batch_first=True
        )
        
        # 门控：控制记忆注入的强度
        self.gate = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Sigmoid()
        )
    
    def forward(
        self, 
        hidden_states: torch.Tensor,
        memory_embeddings: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        将记忆融入隐藏状态
        
        Args:
            hidden_states: 模型的隐藏状态 [batch, seq, hidden]
            memory_embeddings: 当前相关记忆 [batch, num_mem, hidden]
        
        Returns:
            融入记忆后的隐藏状态
        """
        batch_size, seq_len, _ = hidden_states.shape
        
        # 如果没有提供记忆，使用记忆缓冲区
        if memory_embeddings is None:
            memory_embeddings = self.memory_buffer.unsqueeze(0).expand(batch_size, -1, -1)
        
        # 注意力：从记忆中提取相关信息
        memory_context, _ = self.memory_attention(
            query=hidden_states,
            key=memory_embeddings,
            value=memory_embeddings,
        )
        
        # 门控：决定注入多少记忆
        gate_input = torch.cat([hidden_states, memory_context], dim=-1)
        gate_weight = self.gate(gate_input)
        
        # LoRA风格的处理
        adapted = self.up_project(self.down_project(memory_context))
        
        # 融合
        output = hidden_states + gate_weight * adapted
        
        return output
    
    def update_memory(
        self, 
        new_memory: torch.Tensor, 
        index: int
    ):
        """
        在线更新记忆
        
        这是"持续学习"的关键：模型可以实时学习新东西
        """
        with torch.no_grad():
            self.memory_buffer[index] = new_memory
    
    def add_memory_entry(self, entry: MemoryEntry, index: int):
        """添加新的记忆条目"""
        self.update_memory(entry.embedding, index)


class MemoryAugmentedModel:
    """
    记忆增强的模型包装器
    """
    
    def __init__(
        self,
        base_model,
        hidden_size: int,
        adapter_rank: int = 8,
    ):
        self.base_model = base_model
        self.memory_adapter = MemoryAdapter(hidden_size, adapter_rank)
        
        # 获取模型的目标层（通常是中间层）
        self.target_layers = self._get_target_layers()
        
        # 冻结基础模型
        for param in self.base_model.parameters():
            param.requires_grad = False
    
    def _get_target_layers(self):
        """获取要注入记忆的层"""
        # 通常是中间的transformer层
        # 具体取决于模型架构
        return [self.base_model.model.layers[i] for i in range(6, 10)]
    
    def forward(
        self,
        input_ids: torch.Tensor,
        relevant_memories: Optional[List[MemoryEntry]] = None,
        **kwargs
    ):
        """
        带记忆的推理
        """
        # 准备记忆嵌入
        if relevant_memories:
            memory_embeddings = torch.stack([m.embedding for m in relevant_memories])
        else:
            memory_embeddings = None
        
        # Hook函数：在目标层注入记忆
        def hook_fn(module, input, output):
            hidden = output[0] if isinstance(output, tuple) else output
            adapted = self.memory_adapter(hidden, memory_embeddings)
            if isinstance(output, tuple):
                return (adapted,) + output[1:]
            return adapted
        
        # 注册hooks
        hooks = []
        for layer in self.target_layers:
            hook = layer.register_forward_hook(hook_fn)
            hooks.append(hook)
        
        # 推理
        outputs = self.base_model(input_ids, **kwargs)
        
        # 移除hooks
        for hook in hooks:
            hook.remove()
        
        return outputs
```

#### 4.3.3 递归推理层 (RecursiveInference)

```python
# src/model_extensions/recursive_inference.py

import torch
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class ThinkingState(Enum):
    """思考状态"""
    CONTINUE = "continue"      # 继续思考
    CONVERGED = "converged"    # 收敛，得出结论
    ESCALATE = "escalate"      # 需要外部输入
    REST = "rest"              # 休息待机


@dataclass
class ThoughtStep:
    """单步思考"""
    step: int
    hidden_state: torch.Tensor
    output_text: str
    state: ThinkingState
    confidence: float


class RecursiveInference:
    """
    递归推理 - 让模型持续思考
    
    核心思想：
    - 不是一次推理就输出
    - 输出可以反馈为输入，继续思考
    - 类似人类的"反复琢磨"
    
    成本：$0 (只改代码)
    """
    
    def __init__(
        self,
        model,
        max_thinking_steps: int = 5,
        convergence_threshold: float = 0.9,
    ):
        self.model = model
        self.max_thinking_steps = max_thinking_steps
        self.convergence_threshold = convergence_threshold
        
        # 思考历史
        self.thinking_history: List[ThoughtStep] = []
    
    def think(
        self,
        initial_input: str,
        context: Optional[str] = None,
        goal_id: int = 1,
        should_continue_fn: Optional[Callable] = None,
    ) -> List[ThoughtStep]:
        """
        递归思考
        
        Args:
            initial_input: 初始输入
            context: 上下文
            goal_id: 当前目标
            should_continue_fn: 自定义的"是否继续思考"判断函数
        
        Returns:
            思考步骤列表
        """
        self.thinking_history = []
        current_input = initial_input
        hidden_state = None
        
        for step in range(self.max_thinking_steps):
            # 推理
            output, hidden_state = self._inference_step(
                current_input, 
                hidden_state,
                goal_id
            )
            
            # 判断状态
            state, confidence = self._evaluate_thinking_state(
                output, 
                step,
                should_continue_fn
            )
            
            # 记录
            thought = ThoughtStep(
                step=step,
                hidden_state=hidden_state,
                output_text=output,
                state=state,
                confidence=confidence
            )
            self.thinking_history.append(thought)
            
            # 判断是否继续
            if state == ThinkingState.CONVERGED:
                break
            elif state == ThinkingState.ESCALATE:
                # 需要外部输入，暂时停止
                break
            elif state == ThinkingState.REST:
                # 待机模式
                break
            
            # 准备下一步输入（输出反馈为输入）
            current_input = self._prepare_next_input(output, context)
        
        return self.thinking_history
    
    def _inference_step(
        self,
        input_text: str,
        past_hidden: Optional[torch.Tensor],
        goal_id: int,
    ) -> tuple:
        """单步推理"""
        # 如果模型支持目标驱动
        if hasattr(self.model, 'set_goal'):
            self.model.set_goal(goal_id)
        
        # 推理（保持KV Cache以实现持续思考）
        outputs = self.model(
            input_text,
            past_key_values=past_hidden,
            use_cache=True,
        )
        
        return outputs.text, outputs.past_key_values
    
    def _evaluate_thinking_state(
        self,
        output: str,
        step: int,
        custom_fn: Optional[Callable] = None,
    ) -> tuple:
        """
        评估当前思考状态
        
        Returns:
            (state, confidence)
        """
        # 如果有自定义判断函数
        if custom_fn:
            return custom_fn(output, step)
        
        # 默认判断逻辑
        # 1. 如果输出包含明确结论
        if any(marker in output for marker in ["结论是", "答案是", "最终", "完成"]):
            return ThinkingState.CONVERGED, 0.95
        
        # 2. 如果步数达到上限
        if step >= self.max_thinking_steps - 1:
            return ThinkingState.CONVERGED, 0.7
        
        # 3. 如果输出包含疑问（需要外部输入）
        if "?" in output or "需要确认" in output:
            return ThinkingState.ESCALATE, 0.5
        
        # 4. 继续思考
        return ThinkingState.CONTINUE, 0.6
    
    def _prepare_next_input(self, output: str, context: Optional[str]) -> str:
        """准备下一步的输入"""
        # 简单实现：将输出作为新输入的一部分
        # 更复杂的实现可以提取关键点、形成追问等
        if context:
            return f"{context}\n思考：{output}\n继续思考..."
        return f"继续思考：{output}"


class ContinuousThinkingEngine:
    """
    持续思考引擎 - 模拟人脑的持续活动
    
    不是被动等待输入，而是持续在后台思考
    """
    
    def __init__(
        self,
        model,
        check_interval: int = 300,  # 5分钟
    ):
        self.model = model
        self.recursive_inference = RecursiveInference(model)
        self.check_interval = check_interval
        
        # 当前思考状态
        self.current_thoughts: List[ThoughtStep] = []
        self.is_thinking = False
    
    def start_background_thinking(self, initial_topic: str):
        """启动后台思考"""
        self.is_thinking = True
        self._thinking_loop(initial_topic)
    
    def _thinking_loop(self, topic: str):
        """思考循环"""
        import time
        
        while self.is_thinking:
            # 思考
            thoughts = self.recursive_inference.think(
                initial_input=topic,
                goal_id=1,  # 帮助主人
            )
            
            self.current_thoughts = thoughts
            
            # 检查是否有重要发现需要通知
            last_thought = thoughts[-1]
            if last_thought.confidence > 0.8:
                self._notify_owner(last_thought.output_text)
            
            # 休息
            time.sleep(self.check_interval)
    
    def _notify_owner(self, insight: str):
        """通知主人"""
        # 集成到Omnia的通知系统
        pass
    
    def stop_thinking(self):
        """停止思考"""
        self.is_thinking = False
```

### 4.4 完整集成

```python
# src/model_extensions/proactive_model.py

from .goal_encoder import GoalDrivenModel
from .memory_adapter import MemoryAugmentedModel
from .recursive_inference import RecursiveInference


class ProactiveModel:
    """
    完整的主动性模型
    
    集成：
    1. 目标编码器 - 内在驱动
    2. 记忆适配器 - 持续记忆
    3. 递归推理 - 持续思考
    """
    
    def __init__(
        self,
        base_model,
        hidden_size: int = 4096,  # 取决于基础模型
    ):
        # 1. 包装为目标驱动
        self.goal_model = GoalDrivenModel(base_model, hidden_size)
        
        # 2. 包装为记忆增强
        self.memory_model = MemoryAugmentedModel(
            self.goal_model.base_model,
            hidden_size
        )
        
        # 3. 递归推理
        self.recursive_inference = RecursiveInference(self)
        
        # 当前状态
        self.current_goal = 1  # 默认：帮助主人
        self.relevant_memories = []
    
    def forward(
        self,
        input_ids,
        goal_id: Optional[int] = None,
        memories = None,
        **kwargs
    ):
        """
        统一的前向传播
        """
        # 设置目标
        if goal_id is None:
            goal_id = self.current_goal
        
        # 设置记忆
        if memories is None:
            memories = self.relevant_memories
        
        # 目标驱动推理
        outputs = self.goal_model.forward(
            input_ids,
            goal_id=goal_id,
            relevant_memories=memories,
            **kwargs
        )
        
        return outputs
    
    def think_continuously(
        self,
        topic: str,
        max_steps: int = 3,
    ):
        """
        持续思考
        """
        return self.recursive_inference.think(
            initial_input=topic,
            goal_id=self.current_goal,
            max_thinking_steps=max_steps,
        )
    
    def set_goal(self, goal_id: int, intensity: float = 0.5):
        """设置当前目标"""
        self.current_goal = goal_id
        self.goal_model.set_goal(goal_id, intensity)
    
    def add_memory(self, content: str, embedding: torch.Tensor):
        """添加记忆"""
        from .memory_adapter import MemoryEntry
        entry = MemoryEntry(
            content=content,
            embedding=embedding,
            timestamp=time.time(),
        )
        self.relevant_memories.append(entry)
```

---

## 五、实施计划（更新版）

### Phase 0: 准备工作 (1周)

**目标**: 选择基础模型，准备训练环境

**任务**:
- [ ] 选择开源模型（推荐：Qwen-7B 或 LLaMA-7B）
- [ ] 准备训练环境（本地GPU或云端）
- [ ] 收集训练数据（目标-行为对）

**成本**: $0-100

### Phase 1: 推理层改造 (1-2周)

**目标**: 实现递归推理，无需训练

**任务**:
- [ ] 实现 `RecursiveInference` 递归推理
- [ ] 实现 `ProactiveThinker` 系统层思考引擎
- [ ] 集成到Omnia

**成本**: $0  
**本质程度**: 20%

### Phase 2: 目标编码器 (2-3周)

**目标**: 让模型有内在目标驱动

**任务**:
- [ ] 实现 `GoalEncoder`
- [ ] 收集训练数据（目标-行为对）
- [ ] 训练目标编码器（~$100）
- [ ] 集成到模型

**成本**: ~$100  
**本质程度**: 40%

### Phase 3: 记忆适配器 (3-4周)

**目标**: 实现持续记忆和在线学习

**任务**:
- [ ] 实现 `MemoryAdapter`
- [ ] 训练适配器（~$300）
- [ ] 实现在线更新机制
- [ ] 集成到Omnia的记忆系统

**成本**: ~$300  
**本质程度**: 50%

### Phase 4: 系统集成 (4-5周)

**目标**: 将模型层和AiOS层完整集成

**任务**:
- [ ] 实现 `ProactiveModel` 统一接口
- [ ] 集成到PersonaDaemon
- [ ] 实现功耗控制
- [ ] 完整测试

**成本**: $0  
**本质程度**: 55%

### Phase 5: 优化与迭代 (持续)

**目标**: 持续优化，收集反馈

**任务**:
- [ ] 收集使用反馈
- [ ] 优化目标编码器
- [ ] 扩展记忆容量
- [ ] 探索因果推理

---

## 六、成本总览

| 阶段 | 内容 | 成本 | 本质程度 |
|------|------|------|----------|
| Phase 1 | 推理层改造 | $0 | 20% |
| Phase 2 | 目标编码器 | ~$100 | 40% |
| Phase 3 | 记忆适配器 | ~$300 | 50% |
| Phase 4 | 系统集成 | $0 | 55% |
| **总计** | | **~$400** | **55%** |

**如果使用本地部署，成本可降低到接近$0。**

---

## 七、与讨论的对应关系

| 讨论要点 | 方案对应 | 本质程度 |
|----------|----------|----------|
| 主动性是核心 | RecursiveInference + ProactiveThinker | 系统30% + 模型50% |
| 需求系统 | NeedEvaluator + GoalEncoder | 系统30% + 模型40% |
| 宠物认主模式 | CORE_NEEDS + 目标嵌入 | 系统30% + 模型40% |
| 低功耗待机 | PowerController | 系统100% |
| 架构改造 | GoalEncoder + MemoryAdapter | 模型70% |
| 不从头训练 | 冻结基础模型 + 训练适配器 | 100%实现 |

---

## 八、总结

**本方案v2.0的核心改进：**

1. **不只做AiOS层改造** — 还包括模型架构改造
2. **基于开源模型** — 不需要从头训练
3. **分阶段实施** — 成本可控（~$400）
4. **本质程度提升** — 从30%提升到55%

**真正的主动性 = 系统层循环 + 模型层内在驱动**

---

**文档生成**: 无限 @ OpenClaw  
**对话来源**: 与原点的深度讨论 (2026-05-04)  
**版本**: v2.0 - 加入模型架构改造路径
