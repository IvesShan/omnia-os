# 🚀 Omnia Brain 快速启动指南

## 方式一：Docker Compose（推荐）

```bash
# 1. 进入项目目录
cd /home/shan/omnia-os/projects/omnia-brain

# 2. 复制环境变量配置
cp .env.example .env

# 3. 一键启动
./start.sh

# 或者手动启动
docker-compose up -d
```

## 方式二：本地开发

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端** | http://localhost:5173 | 全息3D知识图谱界面 |
| **后端API** | http://localhost:8000 | FastAPI 文档 |
| **Neo4j** | http://localhost:7474 | 图数据库管理界面 |
| **Qdrant** | http://localhost:6333/dashboard | 向量数据库仪表盘 |
| **Ollama** | http://localhost:11434 | LLM 服务 |

## 默认账号

- **Neo4j**: neo4j / omnia2026

## 下一步

1. 打开浏览器访问 http://localhost:5173
2. 看到全息3D大脑粒子效果
3. 使用搜索栏查询知识节点
4. 点击节点查看详情

## 故障排除

### 前端无法连接后端
```bash
# 检查后端是否运行
curl http://localhost:8000

# 检查 CORS 配置
# backend/app/main.py 中已配置允许 localhost:5173
```

### Neo4j 无法启动
```bash
# 查看日志
docker-compose logs neo4j

# 可能需要增加内存
# docker-compose.yml 中调整 NEO4J_dbms_memory_heap_max__size
```

### GPU 加速
```bash
# 如果有 NVIDIA GPU，取消 docker-compose.yml 中的 GPU 配置注释
# 并安装 nvidia-docker
```

## 停止服务

```bash
docker-compose down

# 删除数据卷（慎用！）
docker-compose down -v
```
