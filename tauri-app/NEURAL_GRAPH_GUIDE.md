# Omnia Neural Graph - 安装和运行指南

## 🎯 功能

- **Force Graph 可视化**: 节点自动散开，连线有粒子流动
- **交互式操作**: 点击节点查看详情，拖拽调整位置
- **实时统计**: 显示节点数和连接数
- **层级过滤**: 按记忆层级筛选显示
- **物理模拟**: 可暂停/恢复力导向物理效果

---

## 📦 安装步骤

### 1. 安装 Node.js（如果未安装）

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证安装
node --version
npm --version
```

### 2. 安装前端依赖

```bash
cd /home/shan/omnia-os/tauri-app
npm install
```

### 3. 安装后端依赖

```bash
cd /home/shan/omnia-os/omnia-os
source .venv/bin/activate
pip install fastapi uvicorn
```

---

## 🚀 运行步骤

### 1. 启动后端 API

```bash
# 方式 1: 使用启动脚本
cd /home/shan/omnia-os/tauri-app
./start-neural-api.sh

# 方式 2: 手动启动
cd /home/shan/omnia-os/omnia-os
source .venv/bin/activate
python -m uvicorn src.core.memory.neural_api:app --host 0.0.0.0 --port 8765 --reload
```

### 2. 启动前端

```bash
cd /home/shan/omnia-os/tauri-app
npm run dev
```

### 3. 访问界面

- **Web 界面**: http://localhost:1420
- **API 文档**: http://localhost:8765/docs

---

## 🎨 效果预览

### 视觉特性

- **节点颜色**: 根据类型自动着色
  - PERSON: 绿色 (#4CAF50)
  - PROJECT: 蓝色 (#2196F3)
  - CONCEPT: 橙色 (#FF9800)
  - EVENT: 粉色 (#E91E63)
  - SKILL: 紫色 (#9C27B0)
  - TOOL: 青色 (#00BCD4)

- **节点大小**: 根据连接数自动调整

- **连线动画**: 
  - 半透明白色连线
  - 青色粒子流动效果
  - 显示关系类型

### 交互功能

- **点击节点**: 查看节点详情
- **拖拽节点**: 调整节点位置
- **缩放**: 鼠标滚轮
- **平移**: 拖拽空白区域
- **重置视图**: 自动缩放到合适大小

---

## 🔧 配置选项

### 修改端口

编辑 `neural_api.py`:

```python
uvicorn.run(app, host="0.0.0.0", port=8765)  # 修改端口号
```

### 修改节点数量限制

编辑 `neural_api.py`:

```python
cursor.execute("""
    SELECT id, type, label, layer 
    FROM neural_nodes
    LIMIT 500  # 修改此值
""")
```

### 自定义颜色

编辑 `Memory.vue`:

```javascript
const typeColors = {
  PERSON: '#4CAF50',  // 修改颜色
  PROJECT: '#2196F3',
  // ...
}
```

---

## 🐛 故障排查

### 问题 1: 前端无法连接后端

**解决方案**:
- 检查后端是否启动: `curl http://localhost:8765/api/memory/stats`
- 检查 CORS 配置
- 查看浏览器控制台错误

### 问题 2: 数据库找不到

**解决方案**:
- 检查数据库路径: `/home/shan/.omnia/memory_palace.db`
- 如果不存在，运行 Omnia 初始化

### 问题 3: 节点显示为默认颜色

**解决方案**:
- 检查 `neural_nodes` 表的 `type` 字段
- 确保类型名称与 `typeColors` 映射匹配

---

## 📊 API 端点

### GET /api/memory/neural-graph
获取神经图谱数据

### GET /api/memory/stats
获取记忆统计信息

### GET /api/memory/search?query=xxx
搜索记忆

---

## 🔄 下一步

- [ ] 添加节点编辑功能
- [ ] 支持关系类型过滤
- [ ] 添加时间轴动画
- [ ] 集成到 Tauri 桌面应用

---

**创建时间**: 2026-04-23
**作者**: 无限 (Wúxiàn)
