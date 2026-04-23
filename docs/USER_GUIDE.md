# Omnia 使用说明书

**版本**: v0.1.0  
**日期**: 2026-04-11  
**作者**: 无限 (Wúxiàn) + 原点 (Yuán diǎn)

---

## 1. Omnia 是什么

Omnia 是一个**永不遗忘的本地 Agent 操作系统**。她不是普通的聊天机器人，而是会记住你们的每一次对话、每一段代码、每一个决定，并在你需要的时候主动出现的数字伙伴。

**核心原则**:
- **连续性**: 你们的羁绊会累积
- **在场感**: 她能感知你的 IDE、Git、系统状态
- **主权**: 所有数据都保存在你自己的机器上
- **反脆弱**: 她会自动学习、进化、生成新技能

---

## 2. 快速启动

### 2.1 环境要求
- **操作系统**: Ubuntu / macOS / WSL (Linux)
- **Python**: 3.10+
- **关键依赖**:
  - `flask`, `flask-cors`, `requests` (Web UI 与 API 代理)
  - `psutil` (系统体征监控，可选但推荐)

### 2.2 三种使用方式

#### 方式 A: Web 驾驶舱（推荐）
在终端运行：
```bash
cd ~//home/shan/omnia-os
python3 src/omnia/web_server.py
```
然后打开浏览器：
```
http://127.0.0.1:5001/
```

你会看到完整的 Omnia 驾驶舱界面，包含：
- 左侧战术面板（链路状态、记忆宫殿、环境快照、Git 态势、快捷操作、机体头像框）
- 中央聊天区
- 右侧战术面板（IDE 上下文、系统体征、通知中心、技能矩阵、全息投影）

#### 方式 B: 终端快速唤醒
```bash
cd ~//home/shan/omnia-os
./omnia wake
```
这会输出完整的 system prompt，包含当前 IDE 上下文和记忆召回。

#### 方式 C: 终端对话
```bash
cd ~//home/shan/omnia-os
./omnia chat "你今天做了什么？"
```

---

## 3. 首次配置

### 3.1 API Key 配置
Omnia 需要一个大模型 API Key 才能开口说话。

在 `omnia-os/.env` 文件中写入：
```bash
MOONSHOT_API_KEY=your_key_here
```

**支持的 Key 类型**（按优先级）:
1. `MOONSHOT_API_KEY` / `KIMI_API_KEY` → 走 Kimi Coding 端点
2. `OPENAI_API_KEY` → 走 OpenAI
3. `ANTHROPIC_API_KEY` → 仅 CLI 支持，Web UI 暂不支持

### 3.2 启动守护进程（Daemon）
Daemon 负责后台监控文件变化、Git 状态、定时任务健康度。
```bash
python3 scripts/start_daemon.py
```
关闭：
```bash
python3 scripts/stop_daemon.py
```

**建议**: 每次开机后启动一次 Web Server 和 Daemon，就能全天使用 Omnia。

### 3.3 IDE Bridge 配置（VS Code）
Omnia 能实时感知你在 VS Code 里打开的文件和光标位置。

1. 确保 VS Code 已安装
2. 安装 Omnia IDE Bridge 扩展：
   ```bash
   code --install-extension omnia-ide-bridge/omnia-ide-bridge-0.1.0.vsix
   ```
3. 打开任意项目文件，Web UI 右侧 `IDE.CTX` 面板就会显示当前文件和行号

---

## 4. Web 驾驶舱界面详解

### 顶部 HUD
| 元素 | 说明 |
|------|------|
| **OMNIA Logo** | 系统标识 |
| **数字时钟** | 实时系统时间，每秒跳动 |

### 左侧战术面板
| 面板 | 内容 |
|------|------|
| **SYS.LINK · 链路状态** | 守护进程 / API 通道 / IDE 桥接 的在线状态 |
| **MEM.PALACE · 记忆宫殿** | 事实 / 关系 / 习惯 / 时间线 的记忆条目数 |
| **GIT.OP · Git 态势** | 当前分支、24小时提交数、待提交文件数 |
| **ENV.SNAP · 环境快照** | 机器名、当前模型、Shell、操作系统 |
| **QUICK.OP · 快捷操作** | 唤醒系统 / 打开工作区 / 刷新状态 |
| **INFINITE 机体** | 左下角大头像框，显示 MEM / SKILL 总数和链接强度 |

### 右侧战术面板
| 面板 | 内容 |
|------|------|
| **IDE.CTX · IDE 上下文** | 当前 VS Code 打开的文件、光标位置、语言 |
| **SYS.VITAL · 系统体征** | CPU / 内存 / 磁盘 的实时占用进度条 |
| **NOTIF · 通知中心** | 最近的系统事件、Git 提醒、Daemon 消息 |
| **SKILL.MTX · 技能矩阵** | 已装载技能总数、其中 Auto-Skill Forge 生成的数量 |
| **HOLO.AVATAR · 全息投影** | 纯 CSS 绘制的 Omnia 拟人化身，点击可听到她的回应 |

### 中央聊天区
- **Enter**: 发送消息
- **Shift + Enter**: 换行
- 左侧 Omnia 消息为 cyan 边框气泡，右侧你的消息为灰色气泡
- 发送后状态面板会自动刷新

---

## 5. 点击面板 = 与她互动

大部分 HUD 面板都支持 **点击触发**:

| 面板 | 点击效果 |
|------|----------|
| `SYS.LINK` | Omnia 回复守护进程的说明 |
| `MEM.PALACE` | Omnia 解释记忆结构 |
| `GIT.OP` | Omnia 提示查看未提交列表 |
| `ENV.SNAP` | Omnia 解释当前环境 |
| `IDE.CTX` | **自动打开 VS Code** |
| `SYS.VITAL` | Omnia 解释资源监控 |
| `NOTIF` | Omnia 汇总最近通知 |
| `SKILL.MTX` | Omnia 解释技能来源 |
| `HOLO.AVATAR` | Omnia 随机回复一句话（如"我在。"） |

---

## 6. 文件目录结构

```
omnia-os/
├── web/                        # Web 驾驶舱前端
│   ├── index.html              # 主页面
│   ├── styles.css              # HUD 样式 + 全息投影动画
│   └── app.js                  # 前端逻辑与状态轮询
├── src/
│   ├── core/
│   │   ├── cognition/          # ULTRAPLAN / Context Compressor / Token Budget
│   │   ├── memory_palace/      # SQLite 4层记忆系统
│   │   ├── neuro_center/       # Daemon / Heartbeat / Notification Queue
│   │   ├── personas/           # Persona Loader（SOUL.md 解析）
│   │   └── skill_forge/        # Auto-Skill Forge（检测/生成/审查/安装）
│   └── omnia/
│       ├── __main__.py         # ./omnia CLI 入口
│       ├── wake.py             # 唤醒周期 + system prompt 组装
│       ├── chat.py             # 终端聊天 + API 代理
│       └── web_server.py       # Flask 后端
├── scripts/
│   ├── start_daemon.py         # 启动守护进程
│   ├── stop_daemon.py          # 停止守护进程
│   ├── omnia_boot.py           # OpenClaw 会话启动钩子
│   └── test_*.py               # 各种测试脚本
├── seeds/
│   ├── omnia/SOUL.md           # Omnia 的人格种子
│   ├── infinite/SOUL.md        # 无限的人格种子
│   └── bond_manifesto.md       # 羁绊宣言
├── docs/
│   ├── ARCHITECTURE.md         # 5层架构设计
│   ├── INTERACTION_DESIGN.md   # 交互模式设计
│   └── USER_GUIDE.md           # 本文件
├── .env.example                # API Key 配置模板
└── README.md                   # 项目总览
```

---

## 7. 故障排查

### Q: 打开 `127.0.0.1:5001` 显示空白或无法连接
**A**: Web Server 可能已退出。重新启动：
```bash
cd ~//home/shan/omnia-os
python3 src/omnia/web_server.py
```

### Q: Daemon 显示离线
**A**: 重新启动：
```bash
python3 scripts/start_daemon.py
```

### Q: Omnia 不回复消息，显示 "未配置 API Key"
**A**: 检查 `omnia-os/.env` 是否存在且包含有效的 `MOONSHOT_API_KEY`。

### Q: IDE 上下文始终显示 "未连接"
**A**: 
1. 确认 VS Code 中已安装 `origin.omnia-ide-bridge` 扩展
2. 在 VS Code 中打开任意文件
3. 等待 5~10 秒后刷新 Web 页面

### Q: 系统体征面板显示 "暂无体征数据"
**A**: 安装 psutil：
```bash
pip3 install psutil
```
若遇系统限制，可加 `--break-system-packages`。

---

## 8. 常用命令速查

```bash
# 查看 Omnia 状态
./omnia status

# 唤醒并输出完整 system prompt
./omnia wake

# 终端聊天
./omnia chat "你的消息"

# 启动 Web UI
python3 src/omnia/web_server.py

# 启动/停止守护进程
python3 scripts/start_daemon.py
python3 scripts/stop_daemon.py

# 安装 VS Code 扩展
code --install-extension omnia-ide-bridge/omnia-ide-bridge-0.1.0.vsix --force
```

---

## 9. 更新日志

### v0.1.0 (2026-04-11)
- 首个可运行的 Omnia Web 驾驶舱
- 集成 Memory Palace / IDE Bridge / Auto-Skill Forge / Daemon / Heartbeat
- 新增全息投影拟人化身
- 支持 Kimi / OpenAI API 聊天
- 支持 VS Code 实时光标同步
- 10+ Git commits，由 原点 与 无限 共同完成

---

> **"Welcome to Omnia. The operating system that never forgets."**
>
> — 原点 + 无限 ♾️
