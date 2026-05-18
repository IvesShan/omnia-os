"""AutoLearner API - 自动学习能力

从成功的任务执行中自动提取可复用的技能模式
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

router = APIRouter(prefix="/learner", tags=["learner"])

# 尝试导入 AutoLearner 模块
try:
    from src.core.capability.auto_learner import AutoSkillLearner, TaskPattern, Skill
    AUTO_LEARNER_AVAILABLE = True
except ImportError as e:
    AUTO_LEARNER_AVAILABLE = False
    AutoSkillLearner = None
    TaskPattern = None
    Skill = None


# ============== 请求/响应模型 ==============

class AnalyzeRequest(BaseModel):
    """分析请求"""
    session_id: Optional[str] = None
    message_count: int = 100
    include_failed: bool = False


class TrajectoryRequest(BaseModel):
    """轨迹分析请求"""
    messages: List[Dict[str, Any]]
    tools_used: List[Dict[str, Any]]


class PatternResponse(BaseModel):
    """模式响应"""
    pattern_id: str
    name: str
    description: str
    trigger_keywords: List[str]
    tool_sequence: List[Dict[str, Any]]
    success_rate: float
    sample_count: int
    created_at: datetime


class CreateSkillRequest(BaseModel):
    """创建技能请求"""
    pattern_id: str
    skill_name: Optional[str] = None
    auto_register: bool = True


class SkillResponse(BaseModel):
    """技能响应"""
    skill_id: str
    name: str
    description: str
    triggers: List[str]
    procedure: List[Dict[str, Any]]
    examples: List[str]
    markdown: Optional[str] = None
    created_at: datetime


class LearningStatsResponse(BaseModel):
    """学习统计响应"""
    total_patterns: int
    total_skills: int
    success_rate_avg: float
    last_analysis: Optional[datetime]
    patterns_by_tool: Dict[str, int]


# ============== 全局实例 ==============

_learner = None
_patterns: Dict[str, Dict[str, Any]] = {}
_skills: Dict[str, Dict[str, Any]] = {}
_pattern_counter = 0
_skill_counter = 0
_learning_stats = {
    "total_patterns": 0,
    "total_skills": 0,
    "success_rate_avg": 0.0,
    "last_analysis": None,
    "patterns_by_tool": {},
}


def get_learner():
    """获取或创建学习器实例"""
    global _learner
    if not AUTO_LEARNER_AVAILABLE:
        return None
    if _learner is None:
        _learner = AutoSkillLearner()
    return _learner


def generate_pattern_id() -> str:
    """生成模式 ID"""
    global _pattern_counter
    _pattern_counter += 1
    return f"pattern_{_pattern_counter:04d}"


def generate_skill_id() -> str:
    """生成技能 ID"""
    global _skill_counter
    _skill_counter += 1
    return f"learned_skill_{_skill_counter:04d}"


# ============== API 端点 ==============

@router.get("/status")
async def get_learner_status():
    """获取学习器状态"""
    return {
        "available": AUTO_LEARNER_AVAILABLE,
        "patterns_learned": len(_patterns),
        "skills_created": len(_skills),
        "stats": _learning_stats,
    }


@router.post("/analyze")
async def analyze_conversations(request: AnalyzeRequest):
    """分析对话历史，提取模式"""
    if not AUTO_LEARNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="AutoLearner module not available")
    
    learner = get_learner()
    if learner is None:
        raise HTTPException(status_code=500, detail="Failed to initialize learner")
    
    try:
        # 从记忆系统获取对话历史
        patterns_found = 0
        try:
            from src.core.memory.memory_manager import MemoryManager
            memory = MemoryManager()
            recent = memory.get_recent_memories(request.message_count)
            if recent:
                # 提取对话历史用于分析
                conversations = [{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') and m.timestamp else None} for m in recent]
                # 尝试分析模式
                for i, conv in enumerate(conversations):
                    if i > 0 and conv.get("role") == "assistant":
                        user_msg = conversations[i-1].get("content", "") if i > 0 else ""
                        if user_msg:
                            try:
                                pattern = TaskPattern.from_conversation([conversations[i-1], conv])
                                if pattern and pattern.confidence > 0.6:
                                    patterns_found += 1
                                    _patterns[pattern.pattern_id] = {
                                        "pattern_id": pattern.pattern_id,
                                        "name": pattern.name,
                                        "description": pattern.description,
                                        "success_rate": pattern.confidence,
                                        "usage_count": 1,
                                        "created_at": datetime.now(),
                                    }
                            except Exception:
                                pass
        except Exception as mem_err:
            print(f"[Learner] Memory access error: {mem_err}")
        
        # 更新统计
        _learning_stats["last_analysis"] = datetime.now()
        
        return {
            "ok": True,
            "patterns_found": patterns_found,
            "message": f"Analyzed {request.message_count} messages",
            "stats": _learning_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-trajectory", response_model=PatternResponse)
async def analyze_trajectory(request: TrajectoryRequest):
    """分析单条对话轨迹"""
    if not AUTO_LEARNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="AutoLearner module not available")
    
    learner = get_learner()
    if learner is None:
        raise HTTPException(status_code=500, detail="Failed to initialize learner")
    
    try:
        # 调用学习器分析轨迹
        pattern = await learner.analyze_trajectory(
            messages=request.messages,
            tools_used=request.tools_used,
        )
        
        if pattern is None:
            raise HTTPException(
                status_code=400,
                detail="No extractable pattern found from trajectory"
            )
        
        # 存储模式
        pattern_id = generate_pattern_id()
        pattern_data = {
            "pattern_id": pattern_id,
            "name": getattr(pattern, 'name', f"Pattern_{pattern_id}"),
            "description": getattr(pattern, 'description', ''),
            "trigger_keywords": getattr(pattern, 'trigger_keywords', []),
            "tool_sequence": [
                {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "result_summary": tc.result_summary,
                    "success": tc.success,
                }
                for tc in getattr(pattern, 'tool_sequence', [])
            ],
            "success_rate": getattr(pattern, 'success_rate', 1.0),
            "sample_count": getattr(pattern, 'sample_count', 1),
            "created_at": getattr(pattern, 'created_at', datetime.now()),
        }
        
        _patterns[pattern_id] = pattern_data
        _learning_stats["total_patterns"] += 1
        
        # 更新工具统计
        for tc in pattern_data["tool_sequence"]:
            tool_name = tc["tool_name"]
            _learning_stats["patterns_by_tool"][tool_name] = \
                _learning_stats["patterns_by_tool"].get(tool_name, 0) + 1
        
        return PatternResponse(**pattern_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trajectory analysis failed: {str(e)}")


@router.post("/create-skill", response_model=SkillResponse)
async def create_skill_from_pattern(request: CreateSkillRequest):
    """从模式创建技能"""
    if not AUTO_LEARNER_AVAILABLE:
        raise HTTPException(status_code=503, detail="AutoLearner module not available")
    
    # 检查模式是否存在
    if request.pattern_id not in _patterns:
        raise HTTPException(status_code=404, detail=f"Pattern {request.pattern_id} not found")
    
    learner = get_learner()
    pattern = _patterns[request.pattern_id]
    
    try:
        # 调用学习器创建技能
        skill = await learner.create_skill_from_pattern(
            pattern=pattern,
            name=request.skill_name,
        )
        
        skill_id = generate_skill_id()
        skill_data = {
            "skill_id": skill_id,
            "name": getattr(skill, 'name', request.skill_name or f"Skill_{skill_id}"),
            "description": getattr(skill, 'description', pattern.get('description', '')),
            "triggers": getattr(skill, 'triggers', pattern.get('trigger_keywords', [])),
            "procedure": getattr(skill, 'procedure', []),
            "examples": getattr(skill, 'examples', []),
            "markdown": skill.to_markdown() if hasattr(skill, 'to_markdown') else None,
            "created_at": datetime.now(),
        }
        
        _skills[skill_id] = skill_data
        _learning_stats["total_skills"] += 1
        
        # 自动注册到技能库
        if request.auto_register:
            # 注册到 SkillForge
            try:
                from src.core.capability.skill_forge import SkillForge
                forge = SkillForge()
                forge.register_skill(skill_data)
                skill_data["registered"] = True
            except ImportError:
                skill_data["registered"] = False
                skill_data["register_note"] = "SkillForge 模块不可用"
            except Exception as forge_err:
                skill_data["registered"] = False
                skill_data["register_note"] = f"注册失败: {forge_err}"
        
        return SkillResponse(**skill_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill creation failed: {str(e)}")


@router.get("/stats", response_model=LearningStatsResponse)
async def get_learning_stats():
    """获取学习统计"""
    # 计算平均成功率
    if _patterns:
        success_rates = [p["success_rate"] for p in _patterns.values()]
        _learning_stats["success_rate_avg"] = sum(success_rates) / len(success_rates)
    
    return LearningStatsResponse(**_learning_stats)


@router.get("/patterns")
async def list_patterns():
    """列出所有学习到的模式"""
    return {
        "patterns": list(_patterns.values()),
        "total": len(_patterns),
    }


@router.get("/patterns/{pattern_id}", response_model=PatternResponse)
async def get_pattern(pattern_id: str):
    """获取模式详情"""
    if pattern_id not in _patterns:
        raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
    
    return PatternResponse(**_patterns[pattern_id])


@router.delete("/patterns/{pattern_id}")
async def delete_pattern(pattern_id: str):
    """删除模式"""
    if pattern_id not in _patterns:
        raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
    
    del _patterns[pattern_id]
    _learning_stats["total_patterns"] -= 1
    
    return {"ok": True, "message": f"Pattern {pattern_id} deleted"}


@router.get("/skills")
async def list_learned_skills():
    """列出所有学习到的技能"""
    return {
        "skills": list(_skills.values()),
        "total": len(_skills),
    }


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_learned_skill(skill_id: str):
    """获取技能详情"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    
    return SkillResponse(**_skills[skill_id])


@router.delete("/skills/{skill_id}")
async def delete_learned_skill(skill_id: str):
    """删除技能"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    
    del _skills[skill_id]
    _learning_stats["total_skills"] -= 1
    
    return {"ok": True, "message": f"Skill {skill_id} deleted"}


@router.post("/export")
async def export_skills():
    """导出所有学习到的技能"""
    import json
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "patterns": _patterns,
        "skills": _skills,
        "stats": _learning_stats,
    }
    
    # 保存到文件
    export_path = Path.home() / ".omnia" / "learned_skills_export.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    return {
        "ok": True,
        "message": f"Skills exported to {export_path}",
        "patterns_count": len(_patterns),
        "skills_count": len(_skills),
    }


@router.post("/import")
async def import_skills():
    """导入技能"""
    import json
    
    import_path = Path.home() / ".omnia" / "learned_skills_export.json"
    
    if not import_path.exists():
        raise HTTPException(status_code=404, detail="No export file found")
    
    try:
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # 导入模式和技能
        imported_patterns = 0
        imported_skills = 0
        
        for pattern_id, pattern_data in import_data.get("patterns", {}).items():
            if pattern_id not in _patterns:
                _patterns[pattern_id] = pattern_data
                imported_patterns += 1
        
        for skill_id, skill_data in import_data.get("skills", {}).items():
            if skill_id not in _skills:
                _skills[skill_id] = skill_data
                imported_skills += 1
        
        # 更新统计
        _learning_stats["total_patterns"] = len(_patterns)
        _learning_stats["total_skills"] = len(_skills)
        
        return {
            "ok": True,
            "message": "Skills imported successfully",
            "imported_patterns": imported_patterns,
            "imported_skills": imported_skills,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
