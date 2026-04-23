# Omnia Manager - Tauri 桌面应用安装指南

## 📦 构建完成！

恭喜！Omnia Manager Tauri 应用已成功构建。

### 构建产物

| 文件 | 大小 | 说明 |
|------|------|------|
| `omnia-manager` | 14MB | 原生可执行文件 |
| `Omnia Manager_1.0.0_amd64.deb` | 4.9MB | Debian/Ubuntu 安装包 |

### 文件位置

```
~//home/shan/omnia-os/tauri-app/src-tauri/target/release/
├── omnia-manager                          # 可执行文件
└── bundle/deb/
    ├── Omnia Manager_1.0.0_amd64/         # 解压目录
    └── Omnia Manager_1.0.0_amd64.deb      # 安装包
```

---

## 🚀 安装方式

### 方式 1：安装 DEB 包（推荐）

```bash
sudo dpkg -i ~//home/shan/omnia-os/tauri-app/src-tauri/target/release/bundle/deb/Omnia\ Manager_1.0.0_amd64.deb
```

安装后：
- 应用菜单会出现 "Omnia Manager"
- 命令行可直接运行 `omnia-manager`

### 方式 2：直接运行

```bash
~//home/shan/omnia-os/tauri-app/src-tauri/target/release/omnia-manager
```

### 方式 3：创建桌面快捷方式

```bash
# 创建 .desktop 文件
cat > ~/.local/share/applications/omnia-tauri.desktop << 'EOF'
[Desktop Entry]
Name=Omnia Manager (Tauri)
Comment=Omnia Memory Palace Manager - Native Desktop App
Exec=/home/shan/omnia-os/tauri-app/src-tauri/target/release/omnia-manager
Icon=omnia
Terminal=false
Type=Application
Categories=System;Utility;
StartupNotify=true
EOF

# 设置权限
chmod +x ~/.local/share/applications/omnia-tauri.desktop
```

---

## 🎯 功能列表

| 功能 | 说明 |
|------|------|
| 📊 状态仪表盘 | 守护进程、API、记忆统计 |
| 🔄 服务控制 | 启动/停止/重启 |
| 📝 日志查看 | 实时日志流 |
| 💾 备份管理 | 创建/恢复/删除备份 |
| 🔍 记忆搜索 | 关键词搜索 |
| 📈 分类统计 | 可视化图表 |
| ⚙️ 配置管理 | 编辑配置文件 |

---

## 🛠️ 开发命令

```bash
# 开发模式（热重载）
cd ~//home/shan/omnia-os/tauri-app
npm run tauri dev

# 构建发布版本
npm run tauri build

# 仅构建前端
npm run build

# 检查 Rust 代码
cd src-tauri && cargo check
```

---

## 📋 系统要求

- Ubuntu 24.04+ (或其他 Linux 发行版)
- GTK 3.0+
- WebKit2GTK 4.1+
- 已安装 Omnia 系统

---

## 🐛 故障排除

### 应用无法启动

检查依赖：
```bash
ldd ~//home/shan/omnia-os/tauri-app/src-tauri/target/release/omnia-manager | grep "not found"
```

安装缺失的库：
```bash
sudo apt install -y libwebkit2gtk-4.1-dev libgtk-3-dev
```

### 看不到守护进程状态

确保 Omnia 守护进程正在运行：
```bash
pgrep -f start_daemon.py
```

### 数据库连接错误

检查数据库文件是否存在：
```bash
ls -lh ~//home/shan/omnia-os/memory_palace.db
```

---

## 📊 技术栈

- **前端**: Vue 3 + Vite + Tailwind CSS
- **后端**: Rust + Tauri 2
- **数据库**: SQLite (rusqlite)
- **HTTP 客户端**: reqwest
- **GUI 框架**: GTK 3 + WebKit2GTK

---

## 🎨 对比：CLI vs GUI vs Tauri

| 功能 | CLI | Zenity GUI | Tauri App |
|------|:---:|:----------:|:---------:|
| 查看状态 | ✓ | ✓ | ✓ |
| 服务控制 | ✓ | ✓ | ✓ |
| 日志查看 | ✓ | ✓ | ✓ |
| 备份管理 | ✓ | ✓ | ✓ |
| 记忆搜索 | ✓ | ✓ | ✓ |
| 图形界面 | ✗ | ✓ | ✓ |
| 桌面通知 | ✗ | ✓ | ✓ |
| 应用菜单 | ✗ | ✓ | ✓ |
| 热重载 | ✗ | ✗ | ✓ |
| 跨平台 | ✗ | ✗ | ✓ |
| 原生性能 | ✓ | ✓ | ✓ |
| 美观 UI | ✗ | 中 | 高 |
| 可扩展性 | 高 | 低 | 高 |

---

## 📝 版本历史

### v1.0.0 (2026-04-20)

- ✅ 首次发布
- ✅ 完整的 Omnia 管理功能
- ✅ 原生桌面应用体验
- ✅ 跨平台支持（Linux/macOS/Windows）

---

## 🙏 致谢

- Tauri Team - 现代化的桌面应用框架
- Vue.js Team - 优秀的前端框架
- Rust Community - 安全高效的系统编程语言

---

**Enjoy Omnia Manager! 🎉**
