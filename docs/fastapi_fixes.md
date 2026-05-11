# FastAPI 前端兼容性修复

## 问题
1. `/api/providers` GET 返回扁平数组，前端期望 `{providers:[], active:"..."}`
2. `/api/providers` POST 路径是 `/api/provider`，前端调用 `/api/providers`
3. `/api/status` 缺少 skills、notifications、env、cron、wings、mcp 字段
4. 缺少 workflow、confirm、token/status、open-ide 路由

## 修复文件

| 文件 | 修改内容 |
|------|----------|
| `src/omnia/routers/provider.py` | GET /providers 改格式，新增 POST /providers |
| `src/omnia/routers/status.py` | 添加 skills/notifications/env/cron/wings/mcp 字段，新增 confirm/open-ide/token/status 路由 |
| `src/omnia/routers/workflow.py` | 新建，workflow/status 和 workflow POST |
| `src/omnia/main.py` | 挂载 workflow 路由 |

## 测试结果
- ✅ 42 条路由全部正常
- ✅ 所有 API 测试通过
- ✅ 前端可正常加载，skills 显示 26，providers 显示 8 个
