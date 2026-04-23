# Omnia 待机问题排查与解决方案

## 🔍 问题描述

用户反馈：
1. 待机久了后台服务会关闭
2. 前端 UI 界面会卡住

## 📊 根因分析

### 1. 守护进程内存占用过高

```
PID: 10149
内存: 725MB (4.4%)
OOM Score: 200 (默认值)
```

**问题**：
- 加载了 PyTorch + sentence-transformers 模型
- 内存占用高达 725MB
- OOM score = 200，在内存紧张时容易被系统杀掉

### 2. 缺少健康检查机制

**守护进程**：
- ✅ 有自演化循环（每 5 分钟）
- ❌ 没有心跳检测
- ❌ 没有看门狗机制
- ❌ 进程卡死后无法自动恢复

**前端**：
- ✅ 有定时刷新（15 秒状态检查）
- ❌ 没有连接失败处理
- ❌ 没有自动重连机制
- ❌ 页面后台时会被浏览器降速

### 3. 连接管理问题

**后端**：
- 使用 Flask 开发服务器
- 无 TCP keepalive 设置
- 无连接超时处理

**前端**：
- 使用 HTTP 短连接
- 无 WebSocket 长连接
- 浏览器后台标签页会被降速

## 🛠️ 解决方案

### 方案 1: Watchdog 监控（已实现）

**文件**: `scripts/watchdog.py`

**功能**：
- 每 30 秒检查进程存活
- 每 30 秒检查 API 响应
- 连续失败 3 次自动重启
- 记录健康日志

**启动**：
```bash
python3 scripts/watchdog.py
# 或使用一键启动
bash scripts/start_all.sh
```

### 方案 2: 前端健康检查（已实现）

**文件**: `web/health_check.js`

**功能**：
- 每 30 秒检查后端状态
- 页面恢复可见时立即检查
- 更新 UI 连接状态指示器
- 失败 3 次显示断开状态

**已集成到**: `web/index.html`

### 方案 3: Systemd 服务管理（推荐）

**优势**：
- ✅ 自动重启（Restart=always）
- ✅ 降低 OOM score（减少被杀概率）
- ✅ 日志管理
- ✅ 开机自启

**启用方法**：
```bash
# 重新加载 systemd
systemctl --user daemon-reload

# 启用并启动守护进程
systemctl --user enable omnia-daemon
systemctl --user start omnia-daemon

# 启用并启动 Web Server
systemctl --user enable omnia-web
systemctl --user start omnia-web

# 查看状态
systemctl --user status omnia-daemon
systemctl --user status omnia-web

# 查看日志
journalctl --user -u omnia-daemon -f
```

### 方案 4: 内存优化

**降低内存占用**：
1. 使用轻量级向量模型（已使用 all-MiniLM-L6-v2）
2. 延迟加载模型（已启用 lazy 模式）
3. 使用 hash 向量作为 fallback（模型不可用时）

**调整 OOM Score**：
```bash
# 手动调整（需要 root）
sudo echo -500 > /proc/$(cat ~/.omnia/daemon.pid)/oom_score_adj

# 或使用优化脚本
bash scripts/optimize_daemon.sh
```

## 📋 使用建议

### 日常使用

1. **使用 systemd 管理**（推荐）：
   ```bash
   systemctl --user start omnia-daemon
   systemctl --user start omnia-web
   ```

2. **或使用一键启动**：
   ```bash
   bash scripts/start_all.sh
   ```

3. **查看健康状态**：
   ```bash
   cat ~/.omnia/watchdog_state.json
   tail -f ~/.omnia/watchdog.log
   ```

### 监控日志

```bash
# 守护进程日志
tail -f ~/.omnia/daemon.log

# Web Server 日志
tail -f ~/.omnia/web_server.log

# Watchdog 日志
tail -f ~/.omnia/watchdog.log

# Systemd 日志
journalctl --user -u omnia-daemon -f
```

### 故障排查

1. **检查进程是否运行**：
   ```bash
   ps aux | grep omnia
   ```

2. **检查端口是否监听**：
   ```bash
   netstat -tlnp | grep 5200
   ```

3. **检查 API 是否响应**：
   ```bash
   curl http://localhost:5200/api/status
   ```

4. **查看内存使用**：
   ```bash
   ps aux --sort=-%mem | head -10
   ```

## 🎯 总结

| 问题 | 原因 | 解决方案 | 状态 |
|------|------|----------|------|
| 守护进程被杀 | 内存占用高 + OOM score 高 | Systemd + OOM 调整 | ✅ 已实现 |
| 进程卡死 | 无看门狗 | Watchdog 监控 | ✅ 已实现 |
| 前端卡住 | 无健康检查 | 前端健康检查 | ✅ 已实现 |
| 连接断开 | 无重连机制 | 自动重连 + Systemd | ✅ 已实现 |

**推荐配置**：使用 systemd 管理 + Watchdog 监控 + 前端健康检查

---

**创建时间**: 2026-04-21
**最后更新**: 2026-04-21
