# Omnia WebServer 重构方案

**创建时间**: 2026-05-09
**负责人**: Agent 0 (无限)
**状态**: Phase 1 进行中

---

## 一、重构目标

### 架构升级
- **Flask (同步)** → **FastAPI (异步)**
- **单文件 (1853行)** → **模块化 (10+ 文件)**
- **全局变量** → **依赖注入**
- **同步阻塞** → **异步并发**
- **无类型** → **Pydantic 强类型**

### 性能目标
| 指标 | 当前 | 目标 |
|------|------|------|
| 并发聊天请求 | 4 | 100+ |
| API 响应时间 | 50-200ms | 10-50ms |
| 流式连接数 | 50 | 500+ |
| WebSocket 支持 | ❌ | ✅ |

---

## 二、模块划分

```
src/omnia/
├── main.py                      # FastAPI 入口（Agent 0）
├── config.py                    # 配置管理（Agent 0）
├── dependencies.py              # 依赖注入（Agent 0）
│
├── routers/                     # 路由模块
│   ├── __init__.py
│   ├── chat.py                  # Agent 1：聊天核心
│   ├── memory.py                # Agent 2：记忆搜索
│   ├── graph.py                 # Agent 3：神经图谱
│   ├── provider.py              # Agent 4：Provider 管理
│   ├── workflow.py              # Agent 5：工作流
│   ├── feishu.py                # Agent 6：飞书集成
│   └── status.py                # Agent 7：状态监控
│
├── services/                    # 业务逻辑
│   ├── __init__.py
│   ├── chat_service.py          # 聊天服务（异步）
│   ├── memory_service.py        # 记忆服务（异步）
│   ├── graph_service.py         # 图谱服务（异步）
│   └── llm_client.py            # LLM 客户端（异步）
│
├── models/                      # Pydantic 模型
│   ├── __init__.py
│   ├── chat.py
│   ├── memory.py
│   └── graph.py
│
└── web_server.py                # 保留备份，逐步废弃
```

---

## 三、Agent 分工

| Agent | 负责模块 | 核心任务 | 难度 |
|-------|---------|---------|------|
| **Agent 0 (无限)** | 主架构 + 审核 | FastAPI 入口、配置、依赖注入、最终审核 | 高 |
| Agent 1 | chat.py | 聊天路由、流式响应、异步 LLM 调用 | 高 |
| Agent 2 | memory.py | 记忆搜索、异步数据库查询 | 中 |
| Agent 3 | graph.py | 图谱路由、CPU 密集任务异步化 | 中 |
| Agent 4 | provider.py | Provider 切换、配置检测 | 低 |
| Agent 5 | workflow.py | 工作流执行、后台任务 | 中 |
| Agent 6 | feishu.py | 飞书 webhook、WebSocket | 中 |
| Agent 7 | status.py | 状态监控、系统指标 | 低 |

---

## 四、实施步骤

### Phase 1：基础设施（Agent 0，1天）
**目标**：搭建 FastAPI 骨架，确保可运行

**交付物**：
- `main.py` - 可启动的 FastAPI 服务
- `config.py` - 配置管理（环境变量、路径）
- `dependencies.py` - 依赖注入（MemoryPalace、NeuralGraph）
- 启动脚本：`uvicorn omnia.main:app --reload`

**验收标准**：
- ✅ 服务可启动
- ✅ `/health` 返回 `{"status": "ok"}`
- ✅ 静态文件可访问
- ✅ CORS 配置正确

---

### Phase 2：并行开发（Agent 1-7，2-3天）

每个 Agent 按照模板开发：
1. 创建路由文件
2. 实现 API 端点
3. 编写单元测试
4. 提交审核

**审核流程**：
1. Agent 提交 PR
2. Agent 0 审核代码质量 + 功能正确性
3. 提出修改意见或批准合并
4. 集成测试

---

### Phase 3：集成测试（Agent 0，1天）

**测试清单**：
```bash
# 1. API 兼容性测试
curl -X POST http://localhost:8000/api/chat -d '{"message": "你好"}'
curl -X GET http://localhost:8000/api/status
curl -X POST http://localhost:8000/api/memory/search -d '{"query": "test"}'

# 2. 并发测试
ab -n 100 -c 10 http://localhost:8000/api/status

# 3. 流式测试
curl -N http://localhost:8000/api/chat/stream

# 4. WebSocket 测试
wscat -c ws://localhost:8000/ws/chat
```

---

### Phase 4：切换流量（半天）

```bash
# 1. 启动 FastAPI（端口 8000）
uvicorn omnia.main:app --port 8000

# 2. Nginx 配置
upstream omnia {
    server 127.0.0.1:8000;
    # server 127.0.0.1:5001 backup;  # Flask 作为 backup
}

# 3. 监控日志
tail -f /var/log/omnia/access.log

# 4. 确认无问题后，停止 Flask
```

---

## 五、代码质量审核标准

### ✅ 通过标准
1. **类型安全**：所有函数有类型注解，使用 Pydantic 模型
2. **异步正确**：async def + await，无阻塞调用
3. **错误处理**：统一异常处理，有明确错误码
4. **日志规范**：使用 structlog，有 trace_id
5. **测试覆盖**：核心逻辑有单元测试
6. **文档完整**：API 有 docstring，复杂逻辑有注释

---

## 六、优化项

### 1. 配置管理
- 使用 `pydantic-settings` 统一管理配置
- 环境变量、路径、默认值集中管理

### 2. 日志系统
- 使用 `structlog` 替代 `print()`
- 结构化日志，便于查询和分析

### 3. 错误处理
- 统一异常类 `OmniaError`
- 明确错误码和 HTTP 状态码

### 4. 异步化
- `httpx.AsyncClient` 替代 `requests`
- 异步数据库查询
- CPU 密集任务使用 `asyncio.to_thread()`

### 5. 测试覆盖
- pytest + pytest-asyncio
- 核心路由有单元测试
- 集成测试覆盖主要场景

---

## 七、风险控制

### 回滚方案
```bash
# 1. 保留 Flask 版本
git checkout HEAD -- src/omnia/web_server.py

# 2. Nginx 切换
upstream omnia {
    server 127.0.0.1:5001;  # 回到 Flask
}

# 3. 重启服务
systemctl restart omnia
```

### 兼容性保证
- **API 路径不变**：`/api/chat` 还是 `/api/chat`
- **请求格式不变**：前端无需修改
- **响应格式不变**：JSON 结构一致
- **错误码兼容**：HTTP 状态码 + 错误信息

---

## 八、进度跟踪

- [x] 重构方案制定
- [ ] Phase 1：基础设施搭建（进行中）
- [ ] Phase 2：并行开发
- [ ] Phase 3：集成测试
- [ ] Phase 4：切换流量
- [ ] 完成清理

---

## 九、备注

- Flask 版本 `web_server.py` 保留作为备份
- 前端无需修改，API 保持兼容
- 优先保证功能正确性，性能优化次之
