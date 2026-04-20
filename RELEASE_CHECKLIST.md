# Omnia 发布检查清单

> 在打包发布前，确保完成以下检查

---

## ✅ 发布前检查

### 1. 代码完整性
- [ ] 所有核心功能正常运行
- [ ] 守护进程可以启动
- [ ] 桌面应用可以编译
- [ ] MCP 工具可以连接
- [ ] 记忆系统可以读写

### 2. 配置清理
- [ ] 删除个人 API Keys（`.env`）
- [ ] 删除飞书配置（`config/feishu*.json`）
- [ ] 删除 MCP 服务器配置（`config/mcp_servers.json`）
- [ ] 删除个人数据（`.omnia/`、`logs/`、`data/`）
- [ ] 删除构建产物（`dist/`、`node_modules/`、`*.deb`）

### 3. 依赖文件
- [ ] `requirements.txt` 存在且完整
- [ ] `package.json` 存在且正确
- [ ] `.env.example` 存在（如果有）

### 4. 文档完整性
- [ ] `README_FOR_USER.md` 存在
- [ ] 首次启动向导脚本存在
- [ ] 安装文档存在
- [ ] 用户指南存在

### 5. 脚本权限
- [ ] `scripts/first-run-wizard.sh` 可执行
- [ ] `scripts/quick-start.sh` 可执行
- [ ] `scripts/package-for-usb.sh` 可执行
- [ ] `start.sh` 可执行

---

## 📦 打包流程

### 方式 1: 自动打包（推荐）

```bash
cd /home/shan/.openclaw/workspace/omnia-os
./scripts/package-for-usb.sh 1.0
```

### 方式 2: 手动打包

```bash
# 1. 清理个人配置
rm -rf .omnia logs data dist node_modules
rm -f config/feishu*.json config/mcp_servers.json .env

# 2. 创建基础配置
cp .env.example .env  # 如果有
echo '{"mcpServers":{}}' > config/mcp_servers.json

# 3. 打包
tar -czf omnia-os-v1.0.tar.gz .
```

---

## 🧪 测试流程

### 在新环境测试

1. **解压测试**
   ```bash
   tar -xzf omnia-os-v1.0.tar.gz
   cd omnia-os-v1.0
   ```

2. **首次启动测试**
   ```bash
   ./scripts/first-run-wizard.sh
   ```
   - 检查 API Key 配置是否正常
   - 检查依赖安装是否成功
   - 检查启动命令是否创建

3. **功能测试**
   ```bash
   ./scripts/quick-start.sh
   ```
   - 检查守护进程是否启动
   - 检查桌面应用是否打开
   - 检查对话功能是否正常
   - 检查记忆系统是否工作

4. **记忆测试**
   - 说一句话："我喜欢用 VSCode"
   - 重启 Omnia
   - 问："我之前说过我喜欢什么？"
   - 检查是否能回忆

---

## 📋 发布包内容检查

### 必须包含
```
omnia-os/
├── src/                    # 核心代码
├── scripts/                # 脚本
│   ├── first-run-wizard.sh
│   ├── quick-start.sh
│   └── start_daemon.py
├── config/                 # 配置目录（空或基础模板）
├── docs/                   # 文档
├── requirements.txt        # Python 依赖
├── package.json            # Node 依赖
├── .env.example            # 环境变量模板
├── README_FOR_USER.md      # 用户文档
└── start.sh                # 启动脚本
```

### 必须排除
```
❌ .omnia/                  # 个人数据
❌ logs/                    # 日志
❌ data/                    # 数据
❌ dist/                    # 构建产物
❌ node_modules/            # Node 依赖（用户自己安装）
❌ config/feishu*.json      # 飞书配置
❌ .env                     # 个人 API Keys
❌ *.deb                    # 安装包
❌ *.log                    # 日志文件
```

---

## 🎯 发布渠道

### 1. U盘/网盘
- 打包成 `.tar.gz`
- 提供 `README_FOR_USER.md`
- 提供 MD5 校验（可选）

### 2. GitHub Release
- 创建 Release
- 上传 `.tar.gz` 和 `.zip`
- 写 Release Notes

### 3. 自建服务器
- 上传到服务器
- 提供下载链接
- 提供在线文档

---

## 💡 发布建议

### 对新手友好
1. **提供视频教程** - 录制首次启动流程
2. **提供示例对话** - 展示 Omnia 能做什么
3. **提供常见问题** - 预判用户可能遇到的问题
4. **提供社区支持** - 创建微信群/Discord

### 版本管理
1. **使用语义化版本** - v1.0.0, v1.1.0
2. **记录变更日志** - CHANGELOG.md
3. **提供升级指南** - 如何从旧版本升级

### 持续改进
1. **收集用户反馈** - 哪些地方卡住了
2. **优化首次体验** - 减少配置步骤
3. **完善文档** - 补充缺失的说明

---

## ✨ 发布后

### 用户支持
- 监控 GitHub Issues
- 建立用户社群
- 定期更新文档

### 数据收集（可选）
- 匿名使用统计
- 错误日志上报
- 功能使用情况

---

**记住：发布包的目标是让用户"开箱即用"，让 Omnia 伴随他们成长。**
