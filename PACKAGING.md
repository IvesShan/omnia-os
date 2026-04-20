# Omnia 打包策略

## 设计原则

**核心与数据分离**：应用打包核心功能，用户数据独立存储，实现"打开即用"且"每个用户独立"。

## 打包内容

### 应用内（只读/共享）

```yaml
omnia-desktop/
├── omnia-backend           # Python 后端可执行文件（PyInstaller 打包）
├── web/                    # 前端 UI
│   ├── index.html         # 主界面
│   ├── settings.html      # 设置页面
│   ├── app.js             # 前端逻辑
│   └── styles.css         # 样式
├── seeds/                  # 基础人格设定 ✅
│   ├── omnia/SOUL.md      # Omnia 人格
│   └── infinite/SOUL.md   # Infinite 人格
└── config/                 # 配置模板
    └── settings.template.json
```

### 用户数据（首次启动创建）

```bash
~/.omnia/
├── config/
│   └── settings.json      # API 配置（每个用户独立）
├── memory_palace.db       # 记忆数据库（每个用户独立）
├── data/                  # 其他数据
│   └── agents/            # Agent 数据
└── logs/                  # 日志
    └── backend.log
```

## 首次启动流程

```python
# 1. 检测用户数据目录
if not Path.home().joinpath(".omnia").exists():
    # 2. 创建目录结构
    create_user_directories()
    
    # 3. 复制默认配置
    copy_default_config()
    
    # 4. 初始化记忆库
    initialize_memory_palace()
    
    # 5. 显示欢迎界面
    show_welcome_screen()
else:
    # 加载现有数据
    load_user_data()
```

## 打包配置

### Tauri 配置

```json
{
  "bundle": {
    "resources": [
      "../seeds/**/*",           # 人格设定 ✅
      "../config/settings.template.json",
      "../web/**/*"
    ],
    "externalBin": [
      "binaries/omnia-backend"   # Python 后端
    ]
  }
}
```

### PyInstaller 打包后端

```bash
pyinstaller --onefile \
  --name omnia-backend \
  --add-data "seeds:seeds" \
  --add-data "config:config" \
  --add-data "src/core/memory_palace/schema.sql:memory_palace" \
  backend/standalone_main.py
```

## 用户数据管理

### API 配置

```json
{
  "api_provider": "kimi",
  "api_key": "",              # 用户首次配置
  "model_name": "moonshot-v1-8k",
  "backend_port": 5001,
  "auto_start_backend": true
}
```

### 记忆数据库

- **位置**：`~/.omnia/memory_palace.db`
- **初始化**：首次启动时从 schema.sql 创建
- **迁移**：升级时自动迁移

### 人格加载

```python
# 打包后的路径
SEEDS_DIR = Path(__file__).parent / "seeds"

# 加载人格
def load_personas():
    omnia_soul = SEEDS_DIR / "omnia" / "SOUL.md"
    infinite_soul = SEEDS_DIR / "infinite" / "SOUL.md"
    
    return {
        "omnia": Persona.from_soul(omnia_soul),
        "infinite": Persona.from_soul(infinite_soul)
    }
```

## 升级策略

- **应用更新**：不影响用户数据
- **配置迁移**：自动合并新配置项
- **记忆保留**：数据库独立于版本

## 数据主权

- 用户数据完全在用户机器
- 卸载应用时用户数据保留
- 可以备份、迁移数据
- 每个用户都有自己独立的 Omnia
