# 🚀 快速启动指南

## 方法 1: 自动安装（推荐）

```bash
cd /home/shan/omnia-os/projects/omnia-brain/frontend
chmod +x install_neural_graph.sh
./install_neural_graph.sh
```

## 方法 2: 手动安装

### 安装依赖

```bash
# 使用 npm
npm install 3d-force-graph three-spritetext

# 或使用 pnpm
pnpm add 3d-force-graph three-spritetext

# 或使用 yarn
yarn add 3d-force-graph three-spritetext
```

### 启动开发服务器

```bash
npm run dev
# 或
pnpm dev
# 或
yarn dev
```

### 访问页面

打开浏览器访问: **http://localhost:5173**

---

## 🎯 效果预览

启动后你会看到：

1. **3D 力导向图** - 节点自动布局，像神经网络一样
2. **发光节点** - 每个节点都有光晕效果
3. **粒子流动** - 连线上有粒子流动动画
4. **自动旋转** - 摄像机缓慢旋转
5. **交互功能** - 可以拖拽、点击、悬停节点

---

## 📊 数据说明

当前使用的是 **Memory Palace 演示数据**，包含：

- **核心实体**: Omnia, 无限, 原点
- **记忆系统**: Memory Palace, Facts, Relations, Habits, Timeline
- **项目**: 喵修匠, 懂机帝, OpenClaw
- **技能**: DJI 维修, 无人机诊断
- **知识库**: DJI 设备型号

---

## 🔧 自定义数据

修改 `NeuralGraph3D.jsx` 中的 `generateMemoryPalaceData()` 函数：

```javascript
const nodes = [
    { id: 'your-id', name: '名称', type: 'core', val: 10 },
    // 添加更多节点...
]

const links = [
    { source: 'source-id', target: 'target-id' },
    // 添加更多连接...
]
```

---

## 🌐 后端 API 集成

创建 `/api/memory/graph` 接口：

```python
# backend/api/memory_graph.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/memory/graph")
async def get_memory_graph():
    # 从 Memory Palace 读取真实数据
    return {
        "nodes": [...],
        "links": [...]
    }
```

---

## ❓ 常见问题

### 1. 安装失败？

检查网络连接，或使用国内镜像：

```bash
npm config set registry https://registry.npmmirror.com
npm install
```

### 2. 页面空白？

检查浏览器控制台是否有错误，确保依赖已安装。

### 3. 性能问题？

减少节点数量或调整力导向参数：

```javascript
.d3AlphaDecay(0.05)      // 加快收敛
.d3VelocityDecay(0.4)    // 降低速度
```

---

## 📖 更多文档

查看完整文档: `NEURAL_GRAPH_GUIDE.md`

---

**Created by 无限 for Omnia Memory Palace** 🧠✨
