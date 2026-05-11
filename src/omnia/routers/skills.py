"""SkillForge API - 技能锻造系统

自动从对话模式中提取、生成、审核技能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

router = APIRouter(prefix="/skills", tags=["skills"])

# 尝试导入 SkillForge 模块
try:
    from core.skill_forge import (
        PatternDetector,
        SkillGenerator,
        SkillVetter,
        SelfEvolutionEngine,
        EvolutionStats,
    )
    SKILL_FORGE_AVAILABLE = True
except ImportError as e:
    SKILL_FORGE_AVAILABLE = False
    PatternDetector = None
    SkillGenerator = None
    SkillVetter = None
    SelfEvolutionEngine = None


# ============== 请求/响应模型 ==============

class DetectPatternsRequest(BaseModel):
    """检测模式请求"""
    min_occurrences: int = 2
    days_back: int = 30
    pattern_types: Optional[List[str]] = None


class PatternResponse(BaseModel):
    """模式响应"""
    pattern_id: str
    pattern_type: str
    description: str
    occurrences: int
    confidence: float
    examples: List[str]
    created_at: datetime


class GenerateSkillRequest(BaseModel):
    """生成技能请求"""
    pattern_id: str
    skill_name: Optional[str] = None
    description: Optional[str] = None


class SkillResponse(BaseModel):
    """技能响应"""
    skill_id: str
    name: str
    description: str
    triggers: List[str]
    procedure: List[Dict[str, Any]]
    status: str  # pending, approved, rejected
    created_at: datetime
    vetting_score: Optional[float] = None


class VetSkillRequest(BaseModel):
    """审核技能请求"""
    skill_id: str
    approve: bool
    feedback: Optional[str] = None


class EvolutionCycleRequest(BaseModel):
    """进化周期请求"""
    dry_run: bool = False
    auto_approve: bool = False


class EvolutionStatsResponse(BaseModel):
    """进化统计响应"""
    total_patterns_detected: int
    total_skills_generated: int
    total_skills_approved: int
    total_skills_rejected: int
    last_evolution_run: Optional[str]
    evolution_cycles: int


# ============== 全局实例 ==============

_evolution_engine = None
_pattern_detector = None
_skill_generator = None
_skill_vetter = None

# 存储检测结果（实际应使用数据库）
_detected_patterns: Dict[str, Any] = {}
_generated_skills: Dict[str, Any] = {}
_evolution_stats = {
    "total_patterns_detected": 0,
    "total_skills_generated": 0,
    "total_skills_approved": 0,
    "total_skills_rejected": 0,
    "last_evolution_run": None,
    "evolution_cycles": 0,
}


def get_evolution_engine():
    """获取或创建进化引擎实例"""
    global _evolution_engine
    if not SKILL_FORGE_AVAILABLE:
        return None
    if _evolution_engine is None:
        _evolution_engine = SelfEvolutionEngine()
    return _evolution_engine


def get_pattern_detector():
    """获取或创建模式检测器实例"""
    global _pattern_detector
    if not SKILL_FORGE_AVAILABLE:
        return None
    if _pattern_detector is None:
        _pattern_detector = PatternDetector()
    return _pattern_detector


def get_skill_generator():
    """获取或创建技能生成器实例"""
    global _skill_generator
    if not SKILL_FORGE_AVAILABLE:
        return None
    if _skill_generator is None:
        _skill_generator = SkillGenerator()
    return _skill_generator


def get_skill_vetter():
    """获取或创建技能审核器实例"""
    global _skill_vetter
    if not SKILL_FORGE_AVAILABLE:
        return None
    if _skill_vetter is None:
        _skill_vetter = SkillVetter()
    return _skill_vetter


# ============== API 端点 ==============

@router.get("/status")
async def get_skill_forge_status():
    """获取 SkillForge 状态"""
    return {
        "available": SKILL_FORGE_AVAILABLE,
        "patterns_detected": len(_detected_patterns),
        "skills_generated": len(_generated_skills),
        "stats": _evolution_stats,
    }


@router.post("/detect", response_model=List[PatternResponse])
async def detect_patterns(request: DetectPatternsRequest):
    """检测对话模式"""
    if not SKILL_FORGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SkillForge module not available")
    
    detector = get_pattern_detector()
    if detector is None:
        raise HTTPException(status_code=500, detail="Failed to initialize pattern detector")
    
    try:
        # 调用模式检测器
        # 注意：实际实现需要从数据库或记忆系统中获取对话历史
        patterns = await detector.detect_patterns(
            min_occurrences=request.min_occurrences,
            days_back=request.days_back,
        )
        
        # 存储检测结果
        result = []
        for p in patterns:
            pattern_id = f"pattern_{len(_detected_patterns) + 1}"
            pattern_data = {
                "pattern_id": pattern_id,
                "pattern_type": getattr(p, 'pattern_type', 'unknown'),
                "description": getattr(p, 'description', ''),
                "occurrences": getattr(p, 'occurrences', 1),
                "confidence": getattr(p, 'confidence', 0.0),
                "examples": getattr(p, 'examples', []),
                "created_at": datetime.now(),
            }
            _detected_patterns[pattern_id] = pattern_data
            result.append(PatternResponse(**pattern_data))
        
        _evolution_stats["total_patterns_detected"] += len(result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern detection failed: {str(e)}")


@router.post("/generate", response_model=SkillResponse)
async def generate_skill(request: GenerateSkillRequest):
    """从模式生成技能"""
    if not SKILL_FORGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SkillForge module not available")
    
    # 检查模式是否存在
    if request.pattern_id not in _detected_patterns:
        raise HTTPException(status_code=404, detail=f"Pattern {request.pattern_id} not found")
    
    generator = get_skill_generator()
    if generator is None:
        raise HTTPException(status_code=500, detail="Failed to initialize skill generator")
    
    try:
        pattern = _detected_patterns[request.pattern_id]
        
        # 调用技能生成器
        skill = await generator.generate(
            pattern=pattern,
            name=request.skill_name,
            description=request.description,
        )
        
        skill_id = f"skill_{len(_generated_skills) + 1}"
        skill_data = {
            "skill_id": skill_id,
            "name": getattr(skill, 'name', request.skill_name or f"Skill_{skill_id}"),
            "description": getattr(skill, 'description', pattern.get('description', '')),
            "triggers": getattr(skill, 'triggers', []),
            "procedure": getattr(skill, 'procedure', []),
            "status": "pending",
            "created_at": datetime.now(),
            "vetting_score": None,
        }
        
        _generated_skills[skill_id] = skill_data
        _evolution_stats["total_skills_generated"] += 1
        
        return SkillResponse(**skill_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill generation failed: {str(e)}")


@router.post("/vet", response_model=SkillResponse)
async def vet_skill(request: VetSkillRequest):
    """审核技能"""
    if not SKILL_FORGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SkillForge module not available")
    
    # 检查技能是否存在
    if request.skill_id not in _generated_skills:
        raise HTTPException(status_code=404, detail=f"Skill {request.skill_id} not found")
    
    vetter = get_skill_vetter()
    skill = _generated_skills[request.skill_id]
    
    try:
        if vetter:
            # 调用技能审核器
            report = await vetter.vet(skill)
            vetting_score = getattr(report, 'score', 0.8)
        else:
            vetting_score = 0.8  # 默认分数
        
        # 更新技能状态
        skill["status"] = "approved" if request.approve else "rejected"
        skill["vetting_score"] = vetting_score
        
        if request.approve:
            _evolution_stats["total_skills_approved"] += 1
        else:
            _evolution_stats["total_skills_rejected"] += 1
        
        return SkillResponse(**skill)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill vetting failed: {str(e)}")


@router.post("/evolve")
async def run_evolution_cycle(request: EvolutionCycleRequest):
    """运行进化周期"""
    if not SKILL_FORGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SkillForge module not available")
    
    engine = get_evolution_engine()
    if engine is None:
        raise HTTPException(status_code=500, detail="Failed to initialize evolution engine")
    
    try:
        # 运行进化周期
        result = await engine.run_evolution_cycle(dry_run=request.dry_run)
        
        # 更新统计
        _evolution_stats["evolution_cycles"] += 1
        _evolution_stats["last_evolution_run"] = datetime.now().isoformat()
        
        return {
            "ok": True,
            "result": result.to_dict() if hasattr(result, 'to_dict') else str(result),
            "stats": _evolution_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evolution cycle failed: {str(e)}")


@router.get("/stats", response_model=EvolutionStatsResponse)
async def get_evolution_stats():
    """获取进化统计"""
    return EvolutionStatsResponse(**_evolution_stats)


@router.get("/patterns")
async def list_patterns():
    """列出所有检测到的模式"""
    return {
        "patterns": list(_detected_patterns.values()),
        "total": len(_detected_patterns),
    }


@router.get("/skills")
async def list_skills(status: Optional[str] = None):
    """列出所有生成的技能"""
    skills = list(_generated_skills.values())
    
    if status:
        skills = [s for s in skills if s["status"] == status]
    
    return {
        "skills": skills,
        "total": len(skills),
    }


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    """获取技能详情"""
    if skill_id not in _generated_skills:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    
    return SkillResponse(**_generated_skills[skill_id])


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str):
    """删除技能"""
    if skill_id not in _generated_skills:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    
    del _generated_skills[skill_id]
    
    return {"ok": True, "message": f"Skill {skill_id} deleted"}
