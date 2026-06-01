# Omnia P1 + P2 实施计划
# 最后更新：2026-06-01

## 任务清单

### P1-1: 在线授权验证服务 ✅ 完成
- [x] 服务端激活 API (POST /api/v1/activate) — server/activation_server.py
- [x] 服务端验证 API (POST /api/v1/verify)
- [x] 服务端停用 API (POST /api/v1/deactivate)
- [x] 管理员批量生成卡密 (POST /api/v1/admin/generate)
- [x] 管理员撤销卡密 (POST /api/v1/admin/revoke)
- [x] 管理员统计 (GET /api/v1/admin/stats)
- [x] 客户端 license.py 增加在线验证功能 (activate_online/verify_online)
- [x] 客户端离线宽限期机制（7天）
- [x] 定期后台验证线程 (_BackgroundVerifier)
- [x] 前端授权页面完整重构（试用/在线激活/停用/API Key配置）
- [x] license 路由增加 /trial /deactivate /api-key /update /types 端点

### P1-2: 自动更新机制 ✅ 完成
- [x] 服务端更新检查 API（通过 GitHub Releases API）
- [x] 客户端版本检测模块（_BackgroundVerifier._do_update_check）
- [x] 前端更新提示 UI（license.html 的 update-banner）
- [ ] Tauri 内置 updater 集成（需真实发布环境配置）

### P1-3: 防篡改保护 ✅ 完成
- [x] 完整性校验模块 (src/omnia/integrity.py)
- [x] 代码保护脚本 (protect_code.py) — PyArmor + JS Obfuscator
- [x] 前端 JS 混淆配置
- [x] API Key 加密存储（XOR + HMAC）
- [ ] PyArmor 实际执行（需安装 pyarmor 包）
- [ ] javascript-obfuscator 实际执行（需安装 npm 包）

### P2: 统计后台 ✅ 完成
- [x] 统计后台 Web 页面 (server/templates/admin-dashboard.html)
- [x] 实时数据展示（总卡密数/已激活/活跃设备/今日激活）
- [x] 7天激活趋势图（CSS 柱状图）
- [x] 授权类型分布图表
- [x] 卡密管理界面（列表/生成/撤销）
- [x] 激活记录查看
- [x] 事件日志筛选
- [x] 管理后台路由 (GET /admin)

### 待完成（需要真实环境）
- [ ] 在线激活服务器部署（需要域名和服务器）
- [ ] GitHub Actions CI/CD 测试（需要 push 到 GitHub）
- [ ] PyArmor / javascript-obfuscator 实际执行
- [ ] Tauri 多平台打包验证
- [ ] 自动更新的实际发布流程
