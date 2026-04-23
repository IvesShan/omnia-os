# Omnia CLI 使用指南

Omnia CLI 是一个命令行工具，用于快速管理和配置 Omnia 系统。

## 安装

```bash
# 方法1: 运行安装脚本
cd /home/shan/omnia-os
./scripts/install-cli.sh

# 方法2: 手动安装
chmod +x scripts/omnia-cli
mkdir -p ~/.local/bin
ln -sf $(pwd)/scripts/omnia-cli ~/.local/bin/omnia

# 确保 ~/.local/bin 在 PATH 中
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 可用命令

### 系统管理

```bash
# 查看系统状态（守护进程、API、记忆统计）
omnia status

# 启动守护进程
omnia start

# 停止守护进程
omnia stop

# 重启守护进程
omnia restart
```

### 日志查看

```bash
# 查看最近 50 行日志
omnia logs

# 查看最近 100 行日志
omnia logs 100
```

### 配置管理

```bash
# 编辑配置文件（交互式选择）
omnia config
```

### 记忆管理

```bash
# 搜索记忆
omnia search dji
omnia search 无人机

# 显示详细统计
omnia stats
```

### 备份与恢复

```bash
# 备份记忆数据库
omnia backup

# 恢复备份（交互式选择）
omnia restore
```

### 帮助

```bash
# 显示帮助信息
omnia help
```

## 示例输出

### status 命令

```
============================================================
  Omnia 系统状态
============================================================

✓ 守护进程运行中 (PID: 14181)
✗ API 服务未响应

记忆统计:
  facts:        164 条
  relations:     25 条
  habits:          2 条
  timeline:        9 条
  总计:          200 条
  数据库大小: 8.02 MB

备份: 4 个文件
```

### search 命令

```
============================================================
  搜索: dji
============================================================

找到 39 条结果:

  [dji] dji_assistant_version: DJI Assistant 2 Consumer Drones Series v2.1.39
  [dji] dji_architecture: Electron + Qt + Ogre3D
  [dji] dji_usb_vendor_id: 0x2ca3
  [dji] dji_usb_product_id: 0x0020
  ...
```

## 数据位置

- **数据目录**: `~/.omnia/`
- **守护进程 PID**: `~/.omnia/daemon.pid`
- **日志文件**: `~/.omnia/daemon.log`
- **记忆数据库**: `~/.omnia/memory_palace.db`
- **配置文件**: `~/.omnia/config/`
- **备份目录**: `~/.omnia/backup/`

## 故障排除

### 守护进程无法启动

```bash
# 检查日志
omnia logs 50

# 检查 PID 文件
cat ~/.omnia/daemon.pid

# 手动启动
python3 /home/shan/omnia-os/scripts/start_daemon.py
```

### API 服务未响应

```bash
# 检查端口是否被占用
lsof -i :8765

# 重启守护进程
omnia restart
```

### 记忆数据库损坏

```bash
# 恢复最近的备份
omnia restore

# 或手动恢复
cp ~/.omnia/backup/memory_palace_YYYYMMDD_HHMMSS.db ~/.omnia/memory_palace.db
omnia restart
```

## 开发信息

- **脚本位置**: `/home/shan/omnia-os/scripts/omnia-cli`
- **安装脚本**: `/home/shan/omnia-os/scripts/install-cli.sh`
- **Python 版本**: 3.x
- **依赖**: 仅使用 Python 标准库 + requests（可选，用于 API 健康检查）

## 未来计划

- [ ] 添加 Tab 自动补全
- [ ] 支持更多配置选项
- [ ] 添加记忆导入/导出功能
- [ ] 集成系统托盘状态
- [ ] 添加 Web UI 快速启动
