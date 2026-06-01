# Omnia P1 + P2 实施计划
# 生成时间：2026-05-30

## 任务清单

### P1-1: 在线授权验证服务 ✅ server/activation_server.py 已创建
- [x] 服务端激活 API (POST /api/v1/activate)
- [x] 服务端验证 API (POST /api/v1/verify)
- [x] 服务端停用 API (POST /api/v1/deactivate)
- [x] 管理员批量生成卡密 (POST /api/v1/admin/generate)
- [x] 管理员撤销卡密 (POST /api/v1/admin/revoke)
- [x] 管理员统计 (GET /api/v1/admin/stats)
- [ ] 客户端 license.py 增加在线验证功能
- [ ] 客户端离线宽限期机制（7天）
- [ ] 定期后台验证线程

### P1-2: 自动更新机制
- [ ] 服务端更新检查 API
- [ ] 客户端版本检测模块
- [ ] 前端更新提示 UI
- [ ] Tauri 内置 updater 集成

### P1-3: 防篡改保护
- [ ] PyArmor 配置（Python 字节码加密）
- [ ] 前端 JS 混淆
- [ ] 配置文件加密
- [ ] 代码完整性校验

### P2: 统计后台
- [ ] 统计后台 Web 页面 (admin-dashboard.html)
- [ ] 实时数据展示（激活数、在线数、设备分布）
- [ ] 7天趋势图表
- [ ] 卡密管理界面
