"""
Omnia Management Backend - FastAPI
重构版本：模块化、类型安全、自动文档
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path

# 路径配置
OMNIA_ROOT = Path(__file__).parent.parent.parent
MEMORY_PATH = OMNIA_ROOT / "memory"
SKILLS_PATH = OMNIA_ROOT / "skills"
LOGS_PATH = OMNIA_ROOT / "logs"
CONFIG_PATH = OMNIA_ROOT / "config"

# FastAPI 应用
app = FastAPI(
    title="Omnia Management API",
    description="Omnia AIOS 管理接口",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 数据模型 ============

class MemoryQuery(BaseModel):
    query: str
    layer: Optional[str] = None
    limit: Optional[int] = 20

class MemoryEntry(BaseModel):
    key: str
    value: str
    category: str
    source: str
    timestamp: Optional[str] = None

class SystemStatus(BaseModel):
    status: str
    uptime: Optional[str] = None
    memory_count: int
    skills_count: int
    last_activity: Optional[str] = None

class SkillInfo(BaseModel):
    name: str
    path: str
    description: Optional[str] = None
    enabled: bool = True

# ============ 辅助函数 ============

def load_json_file(path: Path) -> Dict:
    """加载 JSON 文件"""
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_json_file(path: Path, data: Dict) -> bool:
    """保存 JSON 文件"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def get_memory_stats() -> Dict[str, int]:
    """获取记忆统计"""
    stats = {"facts": 0, "relations": 0, "habits": 0, "timeline": 0}
    
    for layer in stats.keys():
        layer_path = MEMORY_PATH / layer
        if layer_path.exists():
            for file in layer_path.glob("*.json"):
                data = load_json_file(file)
                stats[layer] += len(data)
    
    return stats

def scan_skills() -> List[Dict]:
    """扫描已安装技能"""
    skills = []
    
    # 扫描 imported
    imported_path = SKILLS_PATH / "imported"
    if imported_path.exists():
        for skill_dir in imported_path.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                skills.append({
                    "name": skill_dir.name,
                    "path": str(skill_dir),
                    "type": "imported",
                    "enabled": True
                })
    
    # 扫描 auto-forge
    auto_forge_path = SKILLS_PATH / "auto-forge"
    if auto_forge_path.exists():
        for skill_dir in auto_forge_path.iterdir():
            if skill_dir.is_dir():
                skills.append({
                    "name": skill_dir.name,
                    "path": str(skill_dir),
                    "type": "auto-forge",
                    "enabled": True
                })
    
    return skills

# ============ API 路由 ============

@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """获取系统状态"""
    stats = get_memory_stats()
    skills = scan_skills()
    
    return SystemStatus(
        status="running",
        memory_count=sum(stats.values()),
        skills_count=len(skills),
        last_activity=datetime.now().isoformat()
    )

@app.get("/api/memory/stats")
async def get_memory_stats_api():
    """获取记忆统计详情"""
    return get_memory_stats()


@app.get("/api/memory/graph")
async def get_memory_graph():
    """获取记忆图谱数据（节点和边）"""
    nodes = []
    edges = []
    node_map = {}  # 避免重复节点
    
    # 从 relations 层构建图谱
    relations_path = MEMORY_PATH / "relations"
    if relations_path.exists():
        for file in relations_path.glob("*.json"):
            data = load_json_file(file)
            for key, value in data.items():
                if isinstance(value, dict):
                    # 解析关系: "A --[type]--> B"
                    parts = key.split(" --[")
                    if len(parts) >= 2:
                        source = parts[0].strip()
                        rest = parts[1].split("]-->")
                        if len(rest) >= 2:
                            rel_type = rest[0].strip()
                            target = rest[1].strip()
                            
                            # 添加源节点
                            if source not in node_map:
                                node_map[source] = len(nodes)
                                nodes.append({
                                    "id": source,
                                    "label": source,
                                    "type": "ENTITY"
                                })
                            
                            # 添加目标节点
                            if target not in node_map:
                                node_map[target] = len(nodes)
                                nodes.append({
                                    "id": target,
                                    "label": target,
                                    "type": "ENTITY"
                                })
                            
                            # 添加边
                            edges.append({
                                "source": source,
                                "target": target,
                                "type": rel_type
                            })
    
    # 从 facts 层补充节点信息
    facts_path = MEMORY_PATH / "facts"
    if facts_path.exists():
        for file in facts_path.glob("*.json"):
            data = load_json_file(file)
            for key, value in data.items():
                if key not in node_map and isinstance(value, dict):
                    node_type = value.get("type", "ENTITY")
                    nodes.append({
                        "id": key,
                        "label": key,
                        "type": node_type,
                        "data": value
                    })
                    node_map[key] = len(nodes) - 1
    
    # 如果没有数据，返回示例数据
    if not nodes:
        nodes = [
            {"id": "Omnia", "label": "Omnia", "type": "PROJECT"},
            {"id": "无限", "label": "无限", "type": "PERSON"},
            {"id": "原点", "label": "原点", "type": "PERSON"},
            {"id": "记忆宫殿", "label": "记忆宫殿", "type": "CONCEPT"},
            {"id": "喵修匠", "label": "喵修匠", "type": "PROJECT"},
            {"id": "懂机帝", "label": "懂机帝", "type": "PROJECT"}
        ]
        edges = [
            {"source": "Omnia", "target": "无限", "type": "created_by"},
            {"source": "Omnia", "target": "原点", "type": "created_by"},
            {"source": "Omnia", "target": "记忆宫殿", "type": "has_feature"},
            {"source": "无限", "target": "原点", "type": "sibling"},
            {"source": "喵修匠", "target": "Omnia", "type": "related_to"},
            {"source": "懂机帝", "target": "Omnia", "type": "related_to"}
        ]
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    }

@app.get("/api/memory/search")
async def search_memory(
    q: str = Query(..., description="搜索关键词"),
    layer: Optional[str] = Query(None, description="记忆层: facts, relations, habits, timeline")
):
    """搜索记忆"""
    results = []
    search_lower = q.lower()
    
    layers = [layer] if layer else ["facts", "relations", "habits", "timeline"]
    
    for l in layers:
        layer_path = MEMORY_PATH / l
        if not layer_path.exists():
            continue
        
        for file in layer_path.glob("*.json"):
            data = load_json_file(file)
            for key, value in data.items():
                if isinstance(value, dict):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                
                if search_lower in key.lower() or search_lower in value_str.lower():
                    results.append({
                        "key": key,
                        "value": value,
                        "category": l,
                        "source": file.stem
                    })
    
    return {"query": q, "count": len(results), "results": results[:50]}

@app.get("/api/memory/{layer}")
async def get_memory_layer(layer: str):
    """获取指定层的所有记忆"""
    if layer not in ["facts", "relations", "habits", "timeline"]:
        raise HTTPException(status_code=400, detail="Invalid layer")
    
    layer_path = MEMORY_PATH / layer
    all_data = {}
    
    if layer_path.exists():
        for file in layer_path.glob("*.json"):
            data = load_json_file(file)
            all_data.update(data)
    
    return {"layer": layer, "count": len(all_data), "data": all_data}

@app.post("/api/memory/{layer}")
async def add_memory(layer: str, entry: MemoryEntry):
    """添加记忆"""
    if layer not in ["facts", "relations", "habits", "timeline"]:
        raise HTTPException(status_code=400, detail="Invalid layer")
    
    layer_path = MEMORY_PATH / layer / f"{entry.source}.json"
    data = load_json_file(layer_path)
    data[entry.key] = entry.value
    
    if save_json_file(layer_path, data):
        return {"status": "success", "key": entry.key}
    else:
        raise HTTPException(status_code=500, detail="Failed to save memory")

@app.delete("/api/memory/{layer}/{key}")
async def delete_memory(layer: str, key: str, source: str = "default"):
    """删除记忆"""
    if layer not in ["facts", "relations", "habits", "timeline"]:
        raise HTTPException(status_code=400, detail="Invalid layer")
    
    layer_path = MEMORY_PATH / layer / f"{source}.json"
    data = load_json_file(layer_path)
    
    if key not in data:
        raise HTTPException(status_code=404, detail="Key not found")
    
    del data[key]
    
    if save_json_file(layer_path, data):
        return {"status": "success", "key": key}
    else:
        raise HTTPException(status_code=500, detail="Failed to save memory")

@app.get("/api/skills")
async def get_skills():
    """获取所有技能"""
    return {"skills": scan_skills()}

@app.get("/api/logs")
async def get_logs(lines: int = 100):
    """获取日志"""
    log_file = LOGS_PATH / "omnia.log"
    
    if not log_file.exists():
        return {"logs": [], "message": "No log file found"}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {"logs": [line.strip() for line in recent_lines], "total": len(all_lines)}
    except Exception as e:
        return {"logs": [], "error": str(e)}

@app.get("/api/logs/stream")
async def stream_logs():
    """实时日志流 (SSE)"""
    log_file = LOGS_PATH / "omnia.log"
    
    async def log_generator():
        last_size = 0
        while True:
            if log_file.exists():
                current_size = log_file.stat().st_size
                if current_size > last_size:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        f.seek(last_size)
                        new_content = f.read()
                        last_size = current_size
                        for line in new_content.strip().split('\n'):
                            if line:
                                yield f"data: {line}\n\n"
            await asyncio.sleep(1)
    
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/api/config")
async def get_config():
    """获取配置"""
    config_file = CONFIG_PATH / "config.json"
    return load_json_file(config_file)

@app.post("/api/config")
async def update_config(config: Dict[str, Any]):
    """更新配置"""
    config_file = CONFIG_PATH / "config.json"
    if save_json_file(config_file, config):
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save config")

# ============ 静态文件 ============

# 挂载前端静态文件
frontend_path = OMNIA_ROOT / "src" / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

@app.get("/")
async def index():
    """主页"""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        return {"message": "Omnia Management Interface", "docs": "/api/docs"}

# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)

# ============ 模型管理 API ============

# 导入 SmartModelRouter
import sys
sys.path.insert(0, str(OMNIA_ROOT / "src"))
from core.providers.smart_router import SmartModelRouter, ModelMode

# 全局路由器实例
_router_instance = None

def get_router() -> SmartModelRouter:
    """获取路由器单例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartModelRouter()
    return _router_instance

class ModelStatus(BaseModel):
    """模型状态"""
    mode: str
    mode_display: str
    local_available: bool
    local_model: str
    cloud_fast_model: str
    cloud_smart_model: str

class ModelSwitchRequest(BaseModel):
    """模型切换请求"""
    mode: str  # "local_only" | "cloud_only" | "auto"

@app.get("/api/model/status", response_model=ModelStatus)
async def get_model_status():
    """获取当前模型状态"""
    router = get_router()
    
    # 检查本地模型可用性
    local_available = await router.is_local_available()
    
    # 模式显示名称
    mode_display_map = {
        "local_only": "🖥️ 本地 GPU",
        "cloud_only": "☁️ 云端模型",
        "auto": "🤖 智能选择"
    }
    
    return ModelStatus(
        mode=router.mode.value,
        mode_display=mode_display_map.get(router.mode.value, router.mode.value),
        local_available=local_available,
        local_model=router.config.local_model,
        cloud_fast_model=router.config.cloud_fast_model,
        cloud_smart_model=router.config.cloud_smart_model
    )

@app.post("/api/model/switch")
async def switch_model(request: ModelSwitchRequest):
    """切换模型模式"""
    router = get_router()
    
    try:
        router.set_mode(request.mode)
        return {
            "status": "success",
            "mode": router.mode.value,
            "message": f"已切换到 {router.mode.value} 模式"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/model/test")
async def test_model():
    """测试当前模型连接"""
    router = get_router()
    
    # 测试本地模型
    if router.mode == ModelMode.LOCAL_ONLY or router.mode == ModelMode.AUTO:
        local_ok = await router.is_local_available()
    else:
        local_ok = False
    
    return {
        "mode": router.mode.value,
        "local_available": local_ok,
        "recommendation": "本地模型可用" if local_ok else "建议启动本地模型服务"
    }
