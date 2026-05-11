# Trae/Omnia IDE 集成方案

**日期:** 2026-05-11
**优先级:** P1（先搞定8765端口FastAPI，再扩展IDE集成）
**状态:** 方案确定，待实现

## 背景

用户提出让 Omnia 魔改 VS Code/Trae，在开发任务时通过专用功能进行开发。

## 核心理念

- Trae 是一个 IDE（工具），Omnia 是一个 OS（系统）
- Omnia 应该成为"开发大脑"，IDE 只是它的"手"
- 不是让 Omnia 变成 Trae，而是让 Omnia 利用 Trae 的能力

## 方案：Omnia DevConsole

构建 Omnia VS Code 扩展，连接 `src/bridge/ide_bridge.py`，激活 DevConsole Persona。

### 核心功能

1. **项目级上下文索引** — 扫描项目建立神经图谱，理解代码+业务逻辑
2. **Builder 模式（Skill Forge 增强）** — 用户描述需求 → 自动生成完整代码+文件
3. **智能 Debugging（结合记忆）** — 报错时自动搜索记忆库找解决方案
4. **自动提交与部署** — 改完代码 → 测试 → commit → push → 部署

### 技术路径

扩展 `src/bridge/ide_bridge.py` 为 `OmniaDevAssistant` 类：
- `on_code_change(file_path, content)` — 触发 Skill Forge 检测模式
- `on_error(error_msg, stack_trace)` — 触发记忆检索找解决方案
- `handle_builder_request(prompt)` — 调用 LLM 生成代码，直接在编辑器中应用

### 杀手级应用

Omnia 知道业务逻辑+维修知识库，写出来的代码直接包含业务逻辑，不是通用代码。

### 对比优势

| 能力 | Trae | Omnia+IDE |
|:-----|:----:|:---------:|
| 记忆 | ❌ | ✅ 永久记忆 |
| 上下文 | 当前项目 | 全业务上下文 |
| 知识 | 通用代码 | 专业知识库 |
| 执行 | 只改代码 | 全栈执行 |
| 进化 | 静态 | Skill Forge 自动沉淀 |

## 实施顺序

1. ✅ 先搞定 8765 端口 FastAPI 框架
2. 然后扩展 IDE 集成功能
