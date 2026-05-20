# Omnia OS

## IDE Extension - VSCode Chat API Integration

### 重构完成！已切换到 VSCode 原生 Chat API

**最新版本：** `omnia-ide-bridge-0.4.0.vsix`

---

## 🚀 重构对比

| | 旧版（Webview） | 新版（原生 Chat API） |
|---|---|---|
| **聊天位置** | 独立侧边栏面板 | Copilot Chat 面板内 |
| **调用方式** | `Ctrl+Shift+O` 打开面板 | 在 Copilot Chat 里选 `@omnia` |
| **复制粘贴** | ❌ 不好用 | ✅ VSCode 原生支持 |
| **Markdown 渲染** | 需自己做 | ✅ VSCode 原生渲染 |
| **代码高亮** | 需自己做 | ✅ 原生语法高亮 |
| **文件引用** | 自己实现的 `@file` | ✅ VSCode 原生 `#file` 引用 |
| **快捷键** | 部分可用 | ✅ 全部原生 |
| **开发量** | ~1350 行 | ~880 行（减少 35%） |

---

## 🎯 使用方法

### 1. 重启 VSCode

```bash
code
```

### 2. 打开 Copilot Chat 面板

- **侧边栏：** 左侧边栏最下方，有一个**气泡对话框图标**（聊天），点击它
- **快捷键：** `Ctrl+Shift+P` 输入 `聊天: 聚焦到聊天视图`
- **菜单栏：** 顶部菜单 → 视图 → 聊天

### 3. 选择 @omnia

在 Copilot Chat 输入框左边，点击下拉菜单，选择 `@omnia`（你的 AI）

### 4. 开始对话

```
@omnia 你好
@omnia /explain
@omnia /fix
@omnia /commit
@omnia /test
```

---

## 🎮 快捷命令

| 命令 | 说明 |
|------|------|
| `@omnia 你好` | 自由对话 |
| `@omnia /explain` | 解释代码 |
| `@omnia /fix` | 修复代码 |
| `@omnia /commit` | 生成 commit 消息 |
| `@omnia /test` | 生成测试 |
| `Ctrl+Shift+I` | Inline Edit + Diff 预览 |

---

## 📦 安装

```bash
# 从源码编译
cd /home/shan/omnia-os/omnia-ide-bridge
npm run compile
vsce package

# 安装 VSIX
code --install-extension /home/shan/omnia-os/omnia-ide-bridge/omnia-ide-bridge-0.4.0.vsix
```

---

## 🔧 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `omnia.ideBridge.enabled` | `true` | 是否启用 IDE 集成 |
| `omnia.ideBridge.endpoint` | `http://127.0.0.1:8765` | 后端地址 |
| `omnia.ideBridge.debounceMs` | `300` | 防抖延迟 |
| `omnia.ai.autoInjectContext` | `true` | 自动注入上下文 |
| `omnia.ai.maxContextLength` | `4000` | 最大上下文长度 |

---

## 📝 开发日志

### v0.4.0 - 原生 Chat API 重构
- ✅ 切换到 VSCode 原生 Chat API
- ✅ 删除自定义 Webview 面板
- ✅ 注册 `@omnia` 聊天参与者
- ✅ 所有原生功能支持（复制粘贴、Markdown 渲染、代码高亮）
- ✅ 保留所有后端逻辑（Agent Engine 调用、代码分析等）

### v0.3.0 - 阶段 2 功能
- ✅ Inline Edit + Diff 预览
- ✅ Quick Edit
- ✅ CodeLens 提示
- ✅ @file 引用
- ✅ Generate Tests

### v0.2.0 - 基础功能
- ✅ 右键菜单：Explain Code / Fix Code
- ✅ 聊天面板
- ✅ 快捷键支持

### v0.1.0 - 初始版本
- ✅ 基础集成框架
