# Omnia GUI 使用指南

## 📦 安装

GUI 已自动安装，包括：
- ✓ 桌面快捷方式（应用菜单中可搜索）
- ✓ 命令行工具 `omnia-gui`
- ✓ 系统图标

## 🚀 启动方式

### 方式 1：应用菜单（推荐）
1. 按 `Super` 键（Windows 键）打开应用菜单
2. 搜索 "Omnia Manager"
3. 点击启动

### 方式 2：命令行
```bash
omnia-gui           # 打开主菜单
omnia-gui status    # 直接查看状态
omnia-gui backup    # 直接备份
```

### 方式 3：直接运行
```bash
python3 ~//home/shan/omnia-os/scripts/omnia-gui.py
```

## 🎯 功能列表

### 主菜单功能

| 功能 | 说明 |
|------|------|
| **状态** | 查看系统状态仪表盘 |
| **启动** | 启动守护进程 |
| **停止** | 停止守护进程 |
| **重启** | 重启守护进程 |
| **日志** | 查看系统日志（最后100行） |
| **备份** | 备份记忆数据库 |
| **恢复** | 从备份恢复记忆 |
| **搜索** | 搜索记忆内容 |
| **统计** | 查看详细统计信息 |
| **配置** | 编辑配置文件 |

### 状态仪表盘

显示信息：
- 🟢/🔴 守护进程状态
- 🟢/🔴 API 服务状态
- 📊 记忆统计（facts, relations, habits, timeline）
- 💾 数据库大小
- 📁 数据目录位置

### 备份管理

**备份**：
- 自动生成时间戳文件名
- 存储在 `~/.omnia/backups/`
- 显示备份大小

**恢复**：
- 列出最近的 20 个备份
- 显示文件大小
- 确认后才执行恢复
- 自动覆盖当前数据库

### 记忆搜索

- 输入关键词
- 搜索所有记忆表（facts, relations, habits, timeline）
- 显示匹配结果（最多 50 条）

## 📸 界面预览

### 主菜单
```
┌─────────────────────────────────┐
│     Omnia 管理器                │
│     守护进程: 运行中             │
├─────────────────────────────────┤
│ 功能      │ 说明                │
├─────────────────────────────────┤
│ 状态      │ 查看系统状态        │
│ 启动      │ 启动守护进程        │
│ 停止      │ 停止守护进程        │
│ 重启      │ 重启守护进程        │
│ 日志      │ 查看系统日志        │
│ 备份      │ 备份记忆数据库      │
│ 恢复      │ 恢复备份            │
│ 搜索      │ 搜索记忆            │
│ 统计      │ 详细统计信息        │
│ 配置      │ 编辑配置文件        │
└─────────────────────────────────┘
```

### 状态仪表盘
```
┌─────────────────────────────────┐
│     Omnia 系统状态              │
├─────────────────────────────────┤
│ 守护进程: ✓ 运行中 (PID: 12345) │
│ API 服务: ✓ 就绪                │
│                                 │
│ 记忆统计:                       │
│   Facts:      164 条            │
│   Relations:   25 条            │
│   Habits:        2 条           │
│   Timeline:      9 条           │
│   ─────────────────────          │
│   总计:       200 条            │
│                                 │
│ 数据库大小: 8.02 MB             │
│ 数据目录: /home/shan/.omnia     │
└─────────────────────────────────┘
```

## 🔧 技术细节

### 依赖
- Python 3.8+
- Zenity（Ubuntu 默认已安装）
- SQLite3

### 文件位置
- GUI 脚本: `~//home/shan/omnia-os/scripts/omnia-gui.py`
- 桌面快捷方式: `~/.local/share/applications/omnia.desktop`
- 图标: `~/.local/share/icons/omnia.svg`
- 命令: `~/.local/bin/omnia-gui`

### 桌面通知
GUI 会发送桌面通知：
- 启动/停止守护进程
- 备份完成
- 恢复完成

## 🐛 故障排查

### 问题：zenity 未安装
```bash
sudo apt install zenity
```

### 问题：命令找不到
```bash
# 添加到 PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 问题：GUI 无法启动
```bash
# 检查依赖
python3 -c "import sqlite3; print('OK')"

# 直接运行查看错误
python3 ~//home/shan/omnia-os/scripts/omnia-gui.py
```

## 📝 快捷键

在 GUI 对话框中：
- `Enter` - 确认
- `Esc` - 取消
- `Tab` - 切换按钮

## 🎨 自定义

### 修改图标
替换文件：`~/.local/share/icons/omnia.svg`

### 修改桌面快捷方式
编辑文件：`~/.local/share/applications/omnia.desktop`

### 修改 GUI 行为
编辑脚本：`~//home/shan/omnia-os/scripts/omnia-gui.py`

## 📚 相关文档

- [CLI 使用指南](CLI_GUIDE.md)
- [系统架构](../docs/ARCHITECTURE.md)
- [配置说明](../docs/CONFIGURATION.md)

---

*Omnia GUI v1.0 - 让管理更简单*
