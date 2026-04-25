# Omnia 自我认知地图

> **最后更新**: 2026-04-26
> **版本**: 1.2
> **状态**: 补充启动信息

---

## 🚀 启动方式（最重要！）

### 启动命令
```bash
cd /home/shan/omnia-os
bash start.sh              # 后台启动（推荐）
bash start_omnia.sh        # 前台启动（调试用）
```

### 端口
| 服务 | 端口 | 说明 |
|------|------|------|
| **Web Server** | **5001** | 主入口，WebUI |
| API Server | 8765 | REST API（备用） |

### 主程序入口
```
src/omnia/web_server.py    # 5001 端口的主服务
```

### 访问地址
- **WebUI**: http://localhost:5001/
- **API**: http://localhost:8765/

---

## 🏗️ 我的架构

```
omnia-os/
├── start.sh                  # ⭐ 后台启动脚本
├── start_omnia.sh            # ⭐ 前台启动脚本
│
├── src/
│   ├── omnia/
│   │   ├── web_server.py     # ⭐ Web Server (5001)
│   │   ├── main.py           # CLI 入口
│   │   └── stream_chat.py    # 对话处理
│   │
│   ├── core/
│   │   ├── memory_palace/    # 记忆宫殿 ✅
│   │   ├── neural_graph/     # 神经图谱 ✅
│   │   ├── mla/              # MLA 压缩器 ⚠️ 未接入
│   │   ├── reasoning/        # 推理引擎 ⚠️ 未接入
│   │   └── config.py         # 统一配置
│   │
│   ├── skills/
│   │   ├── auto_forge.py     # 自动技能发现 ✅
│   │   └── imported/         # 导入的技能
│   │
│   └── api/
│       └── app.py            # FastAPI 服务 (8765)
│
├── web/
│   └── index.html            # WebUI 神经图谱可视化 ✅
│
├── data/
├── scripts/
│   ├── self_diagnosis.py
│   └── clean_duplicate_memories.py
│
└── knowledge/
    └── DJI/
```

---

## 💾 我的数据库

**位置**: `~/.omnia/memory_palace.db`

### 表结构

| 表名 | 用途 | 当前数量 |
|------|------|----------|
| facts | 事实记忆 | 167 |
| relations | 关系记忆 | 112 |
| habits | 习惯记忆 | 14 |
| timeline | 时间线记忆 | **1902** (已清理) |
| neural_nodes | 神经节点 | 249 |
| neural_edges | 神经边 | 5286 |
| conversation_logs | 对话日志 | 6047 |

### 记忆健康度

| 指标 | 状态 | 说明 |
|------|------|------|
| 重复记忆 | ✅ 0 | 已清理 |
| 异常数据 | ✅ 0 | 已清理 |
| Embedding 覆盖率 | ⚠️ ~55% | 需要补全 |

---

## ✅ 已实现功能

### 核心功能
- [x] 记忆宫殿（facts, relations, habits, timeline）
- [x] 神经图谱（nodes, edges）
- [x] 语义搜索（embedding + FTS）
- [x] 技能自动发现（Skill Forge）
- [x] WebUI 神经图谱可视化
- [x] API 服务（FastAPI）
- [x] 守护进程（PersonaDaemon）
- [x] 自检脚本

### 记忆系统
- [x] 数据验证（过滤异常格式）
- [x] 去重检查（避免重复存储）
- [x] Embedding 生成
- [x] FTS 全文搜索

---

## ⚠️ 已知问题

### P0 - 已修复 ✅
- [x] **重复记忆**: 已清理 3808 条，添加去重逻辑
- [x] **异常数据**: 已清理 279 条，添加数据验证

### P1 - 待修复
- [ ] **Embedding 覆盖不足**: Timeline 仅 ~55% 有 embedding
- [ ] **MLA 压缩未接入**: 已实现但未使用
- [ ] **循环推理未接入**: 已实现但未使用
- [ ] **技能系统不透明**: 20+ 导入技能未激活

### P2 - 长期优化
- [ ] 知识库扩展（只有 DJI）
- [ ] 记忆检索优化
- [ ] 配置管理统一

---

## 🔧 自检流程

```bash
# 完整自检
python3 scripts/self_diagnosis.py

# 快速检查
python3 scripts/self_diagnosis.py --quick

# 清理重复记忆
python3 scripts/clean_duplicate_memories.py --execute
```

---

## 📊 最近修复记录

### 2026-04-26: 补充启动信息
- **新增**: 启动命令、端口、主程序入口
- **修复**: 认知地图缺失关键信息

### 2026-04-24: P0 修复
- **清理重复记忆**: 5710 → 1902 (减少 66.7%)
- **删除异常数据**: 279 条
- **删除重复记忆**: 3529 条
- **代码修复**: `remember_timeline()` 添加数据验证和去重

---

## 🎯 下一步行动

1. **P1 - 补全 Embedding**
   - 为缺失 embedding 的记忆生成向量
   - 提高语义搜索覆盖率

2. **P1 - 接入 MLA 压缩**
   - 将 MLA 压缩器接入主流程
   - 减少 context 长度

3. **P1 - 接入循环推理**
   - 将推理引擎接入主流程
   - 提高决策质量

---

*此文档由 Omnia 自动生成和维护*
