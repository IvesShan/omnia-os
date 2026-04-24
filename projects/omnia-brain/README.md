# Omnia Brain - 全息知识图谱可视化

> **融合项目**: VowVector 架构 + porweb 视觉风格

## 🧠 项目概述

Omnia Brain 是一个本地化的 GPU 加速知识图谱系统，结合了：
- **VowVector** 的 Neo4j + Qdrant 架构
- **porweb** 的全息3D大脑视觉效果

### 核心特性

✨ **全息3D大脑可视化**
- 粒子系统渲染（50,000+ 粒子）
- Bloom + Noise + Vignette 后处理
- 鼠标跟随旋转 + 脉动效果

📊 **知识图谱引擎**
- Neo4j 图数据库存储
- Qdrant 向量搜索
- 本地化部署，无云端依赖

🎨 **视觉风格**
- 橙蓝配色（#ff8a00 + #00ffff）
- 玻璃拟态 UI
- 赛博朋克风格

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Omnia Brain Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Browser ──────────▶ ┌──────────────────┐                  │
│  :5173              │   Frontend        │                  │
│                     │   Vite + Three.js │                  │
│                     │   + Bloom Effects │                  │
│                     └────────┬─────────┘                  │
│                              │ /api                        │
│                     ┌────────▼─────────┐                  │
│                     │   Backend        │                  │
│                     │   FastAPI        │                  │
│                     └────────┬─────────┘                  │
│                              │                             │
│          ┌───────────────────┼───────────────────┐        │
│          │                   │                   │        │
│   ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐  │
│   │   Neo4j     │    │   Qdrant    │    │   Ollama    │  │
│   │  Graph DB   │    │  Vector DB  │    │   LLM       │  │
│   └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 18+
- Python 3.10+
- （可选）NVIDIA GPU 用于加速

### 安装步骤

```bash
# 1. 克隆项目
cd /home/shan/omnia-os/projects/omnia-brain

# 2. 启动服务
docker-compose up -d

# 3. 安装前端依赖
cd frontend
npm install

# 4. 启动前端开发服务器
npm run dev
```

### 访问地址

- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **Neo4j**: http://localhost:7474
- **Qdrant**: http://localhost:6333

## 📁 项目结构

```
omnia-brain/
├── frontend/                 # Vite + Three.js 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── canvas/      # 3D 组件
│   │   │   │   ├── Brain.jsx       # 全息大脑粒子
│   │   │   │   ├── Particles.jsx   # 背景粒子
│   │   │   │   ├── KnowledgeGraph.jsx  # 知识图谱节点
│   │   │   │   └── Experience.jsx  # 场景编排
│   │   │   └── dom/         # UI 组件
│   │   │       ├── Overlay.jsx     # 玻璃拟态 UI
│   │   │       └── SearchBar.jsx   # 搜索栏
│   │   ├── App.jsx
│   │   └── index.css
│   └── package.json
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由
│   │   ├── services/        # 业务逻辑
│   │   └── models/          # 数据模型
│   └── requirements.txt
├── docker-compose.yml        # Docker 编排
└── README.md
```

## 🎨 视觉特性

### 全息大脑粒子系统

- **50,000+ 粒子** 渲染大脑形状
- **橙蓝配色**:
  - 品牌橙 `#ff8a00` - 高亮节点
  - 青色 `#00ffff` - 背景粒子
  - 深青 `#00151a` - 暗部粒子
- **后处理效果**:
  - Bloom（辉光）
  - Noise（噪点）
  - Vignette（暗角）

### 交互效果

- 鼠标跟随旋转
- 脉动动画
- 知识节点悬浮高亮

## 📊 数据模型

### 知识图谱节点

```python
class KnowledgeNode:
    id: str
    content: str
    embedding: List[float]  # 向量嵌入
    metadata: dict
    connections: List[str]  # 关联节点
```

### Neo4j 图谱

```cypher
CREATE (n:Knowledge {
    id: "node_001",
    content: "Omnia 知识图谱",
    created_at: datetime()
})
```

## 🔧 配置

### 环境变量

```bash
# .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=omnia2026

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

## 📈 性能优化

- GPU 加速粒子渲染
- WebWorker 处理向量计算
- IndexedDB 本地缓存
- 虚拟滚动优化大数据集

## 🤝 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可证

MIT License

---

**Created by Omnia Team** | 融合 VowVector + porweb 的智慧结晶
