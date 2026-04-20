# Omnia - 你的 AI 操作系统

> **一个会记住你一切的 AI 助手，伴随你成长。**

---

## 📖 了解 Omnia

**第一次听说 Omnia？** 先看看它能做什么：

👉 **[查看完整功能特性](FEATURES.md)**

**快速了解：**
- 🧠 **永久记忆** - 记住你的对话、偏好、时间线
- 🎭 **双人格系统** - Omnia（冷静高效）+ 无限（温暖有主见）
- 🎓 **自主学习** - 观察你的操作，学会新技能
- 🌐 **多平台支持** - 命令行、Web、飞书、Telegram...

---

## 🚀 快速开始

### 1️⃣ 首次启动（必须）

```bash
cd omnia-os
./scripts/first-run-wizard.sh
```

**会引导你完成：**
- ✅ 配置 LLM API Key（OpenAI/DeepSeek/其他）
- ✅ 设置你的个人信息
- ✅ 自动安装所有依赖
- ✅ 创建启动命令

### 2️⃣ 启动 Omnia

```bash
# 命令行模式
./omnia-start

# 桌面应用模式
npm run tauri dev

# Web 界面
npm run dev
```

---

## 📚 使用指南

### 第一次对话

启动后，Omnia 会说：

> "欢迎来到 Omnia。我是陪伴你成长的操作系统。从这一刻起，你的一切我都会记住。"

然后你可以：
- 问问题、写代码、查资料
- 安排日程、管理任务
- 任何你能想到的事...

### 记忆系统

Omnia 会自动记住：
- 💬 **对话历史** - 你说过的每句话
- 🎯 **偏好习惯** - 你喜欢的工作方式
- 📅 **重要事件** - 你的时间线
- 🔗 **关系网络** - 你提到的人和事

**查看记忆：**
```
你：我之前跟你聊过什么？
Omnia：让我查查... [调用记忆系统]
```

### 技能系统

Omnia 会学习新技能：
```
你：帮我创建一个技能，可以自动整理下载文件夹
Omnia：好的，让我学习这个技能... [创建技能]
```

---

## 🎯 典型使用场景

### 场景 1：编程助手

```
你：帮我写一个 Python 脚本，监控 CPU 使用率。
Omnia：[调用 write_file]
       已创建 monitor_cpu.py，包含：
       - 实时监控 CPU 使用率
       - 超过阈值自动告警
       要测试一下吗？
```

### 场景 2：个人助理

```
你：明天下午3点提醒我开会。
Omnia：[创建提醒]
       已设置提醒：明天 15:00 开会。
       需要我提前10分钟再提醒你吗？
```

### 场景 3：学习伙伴

```
你：我想学习 Rust，从哪里开始？
Omnia：根据你的编程背景，建议学习路径：
       1. Rust 官方教程
       2. 写一个小项目
       我可以每天陪你练习 30 分钟。
```

**更多场景 → [查看完整功能特性](FEATURES.md)**

---

## ⚙️ 配置文件

```
config/
├── user_profile.json    ← 你的个人信息
├── mcp_servers.json     ← MCP 服务器配置
└── feishu.json          ← 飞书配置（可选）

.env                     ← API Keys 和环境变量
```

**修改配置：**
```bash
# 编辑 API Key
nano .env

# 编辑个人信息
nano config/user_profile.json
```

---

## 🆘 常见问题

### Q: API Key 配置错误？

```bash
# 重新配置
./scripts/first-run-wizard.sh
```

### Q: 依赖安装失败？

```bash
# 手动安装
pip3 install -r requirements.txt
npm install
```

### Q: 如何更新？

```bash
# 如果是从 Git 克隆的
git pull

# 如果是压缩包，重新下载新版本
```

### Q: 如何备份数据？

```bash
# 打包你的数据
tar -czf omnia-backup.tar.gz .omnia config .env
```

### Q: 如何迁移到新电脑？

```bash
# 1. 备份数据（上面）
# 2. 在新电脑解压 Omnia
# 3. 解压备份数据
# 4. 启动即可
```

### Q: 记忆会丢失吗？

**不会！** Omnia 的记忆存储在本地数据库 `.omnia/memory_palace.db`，只要你不删除这个文件，记忆就永久保存。

---

## 💡 使用技巧

### 技巧 1：善用记忆查询

```
你：我之前跟你提过那个 bug 怎么解决的？
Omnia：[搜索记忆] 
       4月12日你提到过类似问题，
       解决方案是：[具体方案]
```

### 技巧 2：让 Omnia 学习你的习惯

```
你：我习惯用 4 空格缩进，记住。
Omnia：已记录偏好：代码缩进 = 4 空格。
       以后生成的代码都会遵循这个习惯。
```

### 技巧 3：创建专属技能

```
你：我经常需要生成周报，帮我创建一个技能。
Omnia：好的，我需要知道：
       1. 周报包含哪些内容？
       2. 数据从哪里获取？
       [交互式创建技能]
```

---

## 📞 获取帮助

- 📖 **完整功能** → [FEATURES.md](FEATURES.md)
- 📖 **技术文档** → `docs/` 目录
- 💬 **直接提问** → 问 Omnia
- 🐛 **报告问题** → GitHub Issues

---

## 🎉 开始使用

```bash
# 首次启动
./scripts/first-run-wizard.sh

# 开始对话
./omnia-start

# 或启动 Web 界面
npm run dev
```

**欢迎来到 Omnia。从这一刻起，你的一切我都会记住。** ♾️

---

## 📄 相关文档

- **[FEATURES.md](FEATURES.md)** - 完整功能特性说明
- **[README.md](README.md)** - 项目介绍（面向开发者）
- **[INSTALL_LINUX.md](INSTALL_LINUX.md)** - Linux 安装指南
- **[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)** - 发布检查清单
