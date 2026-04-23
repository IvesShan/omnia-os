# Omnia HUD 面板诊断报告

生成时间：2026-04-20

---

## 📊 面板清单

### 左侧战术列

| 面板 | data-action | 处理函数 | 状态 | 问题 |
|------|-------------|----------|------|------|
| 链路状态 | `daemon` | ✅ 有 | ✅ 正常 | - |
| 记忆宫殿 | `memory` | ✅ 有 | ✅ 正常 | - |
| Git 态势 | `git` | ✅ 有 | ⚠️ 待完善 | 只显示提示，未调用 API |
| 环境快照 | `env` | ✅ 有 | ⚠️ 待完善 | 只显示提示，未调用 API |
| 快捷操作 | `quick` | ✅ 有 | ❌ 空实现 | 无任何功能 |

### 中央区域

| 面板 | data-action | 处理函数 | 状态 | 问题 |
|------|-------------|----------|------|------|
| 神经图谱 | `neural-graph` | ❌ 缺失 | ❌ 无响应 | 点击无任何反应 |
| API 选择器 | `api-selector` | ❌ 缺失 | ❌ 无响应 | 点击无任何反应 |
| IDE 状态 | `ide` | ✅ 有 | ⚠️ API 缺失 | 后端无 `/api/open-ide` |
| 系统体征 | `system` | ✅ 有 | ⚠️ 待完善 | 只显示提示，未调用 API |
| 通知中心 | `notif` | ✅ 有 | ⚠️ 待完善 | 只显示提示，未调用 API |

### 右侧战术列

| 面板 | data-action | 处理函数 | 状态 | 问题 |
|------|-------------|----------|------|------|
| 技能矩阵 | `skills` | ✅ 有 | ⚠️ 待完善 | 只显示提示，未调用 API |
| 记忆搜索 | `memory-search` | ❌ 缺失 | ❌ 无响应 | 点击无任何反应 |
| 工作流 | `workflow` | ❌ 缺失 | ❌ 无响应 | 点击无任何反应 |

---

## 🔍 详细问题分析

### 1. 缺失的 handlePanelClick case 分支

**文件**: `web/app.js` 第 1277 行

**问题**: 以下 action 没有对应的 case 分支：
- `neural-graph`
- `api-selector`
- `memory-search`
- `workflow`

**影响**: 点击这些面板时，`handlePanelClick` 函数无法匹配 action，导致无任何响应。

---

### 2. 后端 API 缺失

#### 2.1 `/api/open-ide` 缺失

**调用位置**: `app.js` 第 1310 行

```javascript
case 'ide':
  appendOmnia('[提示] 正在尝试打开 VS Code…（请确保已安装）');
  fetch(`${API_BASE}/api/open-ide`, { method: 'POST' }).catch(() => {});
  break;
```

**问题**: 后端 `omnia_backend.py` 没有定义 `/api/open-ide` 路由。

**解决方案**: 添加 API 端点或移除前端调用。

---

#### 2.2 `/api/workflow` 缺失

**调用位置**: `app.js` 第 1076 行

**问题**: 后端没有定义 `/api/workflow` 路由。

---

### 3. 功能实现不完整

以下面板只有简单的提示信息，缺少实际功能：

| 面板 | 当前行为 | 应有行为 |
|------|----------|----------|
| `git` | 显示提示 | 调用 `/api/git/status` 显示未提交文件 |
| `env` | 显示提示 | 调用 `/api/system/env` 显示环境变量 |
| `system` | 显示提示 | 调用 `/api/system/stats` 显示 CPU/内存 |
| `notif` | 显示提示 | 调用 `/api/notifications` 显示通知列表 |
| `skills` | 显示提示 | 调用 `/api/skills` 显示技能列表 |
| `quick` | 无行为 | 应提供快捷操作按钮 |

---

## 🛠️ 修复方案

### 优先级 1: 修复缺失的 case 分支

在 `app.js` 的 `handlePanelClick` 函数中添加：

```javascript
case 'neural-graph':
  // 触发图谱加载
  if (typeof GraphViz !== 'undefined') {
    GraphViz.loadGraph();
  }
  appendOmnia('[系统] 神经图谱已加载，显示实体关系网络。');
  break;

case 'api-selector':
  // 切换 API 提供商
  const currentApi = localStorage.getItem('omnia_api_provider') || 'baidu';
  const nextApi = currentApi === 'baidu' ? 'kimi' : 'baidu';
  localStorage.setItem('omnia_api_provider', nextApi);
  appendOmnia(`[系统] API 已切换为: ${nextApi.toUpperCase()}`);
  break;

case 'memory-search':
  // 触发记忆搜索
  appendOmnia('[系统] 请使用输入框输入搜索关键词，或输入 /memory 命令搜索记忆宫殿。');
  break;

case 'workflow':
  // 显示工作流状态
  appendOmnia('[系统] 工作流引擎正在运行，当前无活动工作流。');
  break;
```

---

### 优先级 2: 添加后端 API

在 `backend/omnia_backend.py` 中添加：

```python
@app.route('/api/open-ide', methods=['POST'])
def open_ide():
    """打开 VS Code"""
    import subprocess
    try:
        subprocess.Popen(['code', '.'], cwd=os.getcwd())
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/git/status', methods=['GET'])
def git_status():
    """获取 Git 状态"""
    import subprocess
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return jsonify({'files': files, 'count': len(files)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/env', methods=['GET'])
def system_env():
    """获取系统环境"""
    import platform
    return jsonify({
        'os': platform.system(),
        'python': platform.python_version(),
        'hostname': platform.node(),
        'cwd': os.getcwd()
    })

@app.route('/api/system/stats', methods=['GET'])
def system_stats():
    """获取系统资源"""
    import psutil
    return jsonify({
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    })
```

---

### 优先级 3: 完善面板功能

为每个面板添加实际的数据获取和显示逻辑。

---

## 📈 测试清单

- [ ] 点击"链路状态"面板，显示守护进程状态
- [ ] 点击"记忆宫殿"面板，显示记忆统计
- [ ] 点击"神经图谱"面板，加载图谱可视化
- [ ] 点击"API 选择器"面板，切换 API 提供商
- [ ] 点击"IDE 状态"面板，打开 VS Code
- [ ] 点击"记忆搜索"面板，显示搜索提示
- [ ] 点击"工作流"面板，显示工作流状态
- [ ] 验证所有面板的视觉反馈（高亮、动画）

---

## 🎯 下一步行动

1. **立即修复**: 添加缺失的 case 分支
2. **添加 API**: 实现后端缺失的 API 端点
3. **完善功能**: 为每个面板添加实际功能
4. **测试验证**: 执行测试清单

---

生成者：Omnia 系统诊断模块
