# 🧠 Neural Graph 3D - 神经图谱可视化

## 简介

基于 **3d-force-graph** 的酷炫神经图谱可视化组件，用于展示 Omnia 的 Memory Palace 数据。

## 特性

✨ **酷炫效果**
- 力导向自动布局
- 节点发光效果
- 连线脉冲动画
- 自动旋转摄像机

🎯 **交互功能**
- 鼠标拖拽节点
- 点击查看详情
- 悬停高亮
- 缩放和旋转

📊 **数据展示**
- Memory Palace 实体
- 关系网络
- 习惯和时间线
- 技能和知识库

## 安装

```bash
cd /home/shan/omnia-os/projects/omnia-brain/frontend
npm install
# 或
pnpm install
# 或
yarn install
```

## 使用方法

### 1. 在 Experience.jsx 中使用

```jsx
import { NeuralGraph3D } from './NeuralGraph3D'

export function Experience() {
    return (
        <div style={{ width: '100%', height: '100vh' }}>
            <NeuralGraph3D />
        </div>
    )
}
```

### 2. 在 HUD 面板中使用

```jsx
import { NeuralGraph3D } from './NeuralGraph3D'

export function HUDPanel() {
    return (
        <div className="hud-panel">
            <NeuralGraph3D width={800} height={600} />
        </div>
    )
}
```

## 数据格式

### 节点数据

```javascript
{
    id: 'unique-id',
    name: '显示名称',
    type: 'core | persona | user | module | project | skill | knowledge | device',
    val: 5  // 节点大小权重
}
```

### 连接数据

```javascript
{
    source: 'source-node-id',
    target: 'target-node-id'
}
```

## 节点类型和颜色

| 类型 | 颜色 | 说明 |
|------|------|------|
| core | #ff8a00 (橙) | 核心实体 |
| persona | #ff00ff (紫) | 人格 |
| user | #00ff00 (绿) | 用户 |
| module | #00ffff (青) | 模块 |
| project | #ff6600 (橙红) | 项目 |
| skill | #ffcc00 (金) | 技能 |
| knowledge | #cc66ff (紫罗兰) | 知识 |
| device | #66ccff (天蓝) | 设备 |

## 自定义配置

### 修改力导向参数

```jsx
<NeuralGraph3D 
    linkDistance={50}        // 连线距离
    chargeStrength={-120}    // 排斥力
    d3AlphaDecay={0.02}      // 收敛速度
/>
```

### 修改视觉效果

```jsx
// 在 NeuralGraph3D.jsx 中修改
.nodeOpacity(0.9)
.linkOpacity(0.3)
.linkDirectionalParticles(2)  // 粒子数量
.linkDirectionalParticleSpeed(0.005)  // 粒子速度
```

## 后端 API 集成

### 创建 Memory Palace API

```python
# backend/api/memory_graph.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/memory/graph")
async def get_memory_graph():
    """返回 Memory Palace 的图谱数据"""
    return {
        "nodes": [
            {"id": "omnia", "name": "Omnia", "type": "core", "val": 10},
            # ... 更多节点
        ],
        "links": [
            {"source": "omnia", "target": "wuxian"},
            # ... 更多连接
        ]
    }
```

## 运行开发服务器

```bash
cd /home/shan/omnia-os/projects/omnia-brain/frontend
npm run dev
```

访问: http://localhost:5173

## 构建生产版本

```bash
npm run build
```

## 效果预览

- 🌐 3D 力导向图自动布局
- ✨ 节点发光和光晕效果
- 💫 连线粒子流动动画
- 🔄 摄像机自动旋转
- 🖱️ 鼠标交互（拖拽、点击、悬停）

## 技术栈

- **3d-force-graph**: 3D 力导向图库
- **Three.js**: 3D 渲染引擎
- **three-spritetext**: 文字标签
- **React**: UI 框架
- **Vite**: 构建工具

## 下一步

1. ✅ 安装依赖
2. ✅ 集成到 HUD 面板
3. ⏳ 连接真实 Memory Palace API
4. ⏳ 添加更多交互功能（搜索、过滤）
5. ⏳ 优化性能（大数据量）

---

**Created by 无限 for Omnia Memory Palace**
