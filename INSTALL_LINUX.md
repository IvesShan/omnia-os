# Omnia Linux 安装指南

## 系统要求

- Ubuntu 18.04+ 或其他基于 Debian 的发行版
- 依赖库：`libwebkit2gtk-4.1-0`, `libgtk-3-0`（安装时会自动安装）

## 安装步骤

### 方法一：DEB 包安装（推荐）

```bash
# 1. 下载 deb 包
cd /home/shan/omnia-os/src-tauri/target/release/bundle/deb

# 2. 安装
sudo dpkg -i Omnia_1.1.1_amd64.deb

# 3. 如果有依赖问题，修复
sudo apt-get install -f

# 4. 启动 Omnia
omnia-desktop
```

### 方法二：从源码构建

```bash
# 1. 克隆仓库
git clone https://github.com/your-repo/omnia-os.git
cd omnia-os

# 2. 安装依赖
npm install

# 3. 构建
npm run tauri build

# 4. 安装生成的 deb 包
sudo dpkg -i src-tauri/target/release/bundle/deb/Omnia_1.1.1_amd64.deb
```

## 首次启动

安装后首次启动会：

1. **创建用户数据目录**：`~/.omnia/`
   - `config/settings.json` - API 配置
   - `memory_palace.db` - 记忆数据库
   - `logs/` - 日志文件

2. **提示配置 API**
   - 打开设置页面
   - 选择 API 提供商（Kimi / OpenAI / 其他）
   - 输入 API Key

3. **初始化人格**
   - Omnia（系统人格）
   - Infinite（助手人格）

## 卸载

```bash
sudo apt remove omnia

# 用户数据会保留在 ~/.omnia/
# 如需删除用户数据：
rm -rf ~/.omnia
```

## 文件位置

安装后文件分布：

```
/usr/bin/omnia-desktop          # 桌面应用
/usr/bin/omnia-backend          # 后端服务
/usr/lib/Omnia/_up_/web/        # 前端 UI
/usr/lib/Omnia/_up_/seeds/      # 人格设定
/usr/lib/Omnia/_up_/config/     # 配置模板
/usr/share/applications/Omnia.desktop  # 桌面图标
~/.omnia/                       # 用户数据（首次启动创建）
```

## 故障排查

### 后端无法启动

```bash
# 检查后端是否可执行
which omnia-backend
omnia-backend --help

# 查看日志
tail -f ~/.omnia/logs/backend.log
```

### 前端无法加载

```bash
# 检查 web 文件
ls -la /usr/lib/Omnia/_up_/web/

# 检查权限
ls -l /usr/bin/omnia-desktop
```

### API 配置问题

```bash
# 查看配置
cat ~/.omnia/config/settings.json

# 手动编辑
nano ~/.omnia/config/settings.json
```

## 更新

```bash
# 下载新版本 deb 包后
sudo dpkg -i Omnia_新版本_amd64.deb

# 用户数据和配置会自动保留
```

## 开发模式

如果想在开发模式下运行：

```bash
cd /path/to/omnia-os

# 启动后端（开发模式）
python backend/standalone_main.py

# 启动前端（开发模式）
npm run tauri dev
```

## 支持

- GitHub Issues: https://github.com/your-repo/omnia-os/issues
- 文档: https://github.com/your-repo/omnia-os/wiki
