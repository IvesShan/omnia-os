"""
渐进式能力解锁系统
Progressive Capability Unlocking System

功能：
- 根据用户需求和使用频率，逐步解锁新功能
- 避免一次性暴露所有功能造成认知负担
- 提供个性化的功能发现体验
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


class CapabilityLevel(Enum):
    """能力等级"""
    NOVICE = 1          # 新手：基础功能
    BEGINNER = 2        # 初学者：常用功能
    INTERMEDIATE = 3    # 中级：进阶功能
    ADVANCED = 4        # 高级：专业功能
    EXPERT = 5          # 专家：高级功能
    MASTER = 6          # 大师：实验性功能
    LEGENDARY = 7       # 传奇：隐藏功能
    MYTHIC = 8          # 神话：极客功能
    DIVINE = 9          # 神圣：开发者功能
    ULTIMATE = 10       # 终极：完全解锁


class CapabilityCategory(Enum):
    """能力类别"""
    CHAT = "chat"               # 对话能力
    MEMORY = "memory"           # 记忆能力
    TOOLS = "tools"             # 工具能力
    WORKFLOW = "workflow"       # 工作流能力
    KNOWLEDGE = "knowledge"     # 知识能力
    AUTOMATION = "automation"   # 自动化能力
    ANALYTICS = "analytics"     # 分析能力
    INTEGRATION = "integration" # 集成能力
    DEVELOPER = "developer"     # 开发者能力
    EXPERIMENTAL = "experimental" # 实验性能力


@dataclass
class Capability:
    """能力定义"""
    id: str
    name: str
    description: str
    category: CapabilityCategory
    level: CapabilityLevel
    prerequisites: List[str] = field(default_factory=list)
    usage_count: int = 0
    last_used: Optional[datetime] = None
    unlocked: bool = False
    unlock_date: Optional[datetime] = None
    auto_unlock: bool = True  # 是否自动解锁
    unlock_conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['category'] = self.category.value
        data['level'] = self.level.value
        data['last_used'] = self.last_used.isoformat() if self.last_used else None
        data['unlock_date'] = self.unlock_date.isoformat() if self.unlock_date else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Capability':
        """从字典创建"""
        data['category'] = CapabilityCategory(data['category'])
        data['level'] = CapabilityLevel(data['level'])
        data['last_used'] = datetime.fromisoformat(data['last_used']) if data['last_used'] else None
        data['unlock_date'] = datetime.fromisoformat(data['unlock_date']) if data['unlock_date'] else None
        return cls(**data)


@dataclass
class UserProgress:
    """用户进度"""
    user_id: str
    current_level: CapabilityLevel = CapabilityLevel.NOVICE
    total_usage: int = 0
    experience_points: int = 0
    unlocked_capabilities: Set[str] = field(default_factory=set)
    capability_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_activity: Optional[datetime] = None
    achievements: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'current_level': self.current_level.value,
            'total_usage': self.total_usage,
            'experience_points': self.experience_points,
            'unlocked_capabilities': list(self.unlocked_capabilities),
            'capability_usage': dict(self.capability_usage),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'achievements': self.achievements
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserProgress':
        """从字典创建"""
        data['current_level'] = CapabilityLevel(data['current_level'])
        data['unlocked_capabilities'] = set(data['unlocked_capabilities'])
        data['capability_usage'] = defaultdict(int, data['capability_usage'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity']) if data['last_activity'] else None
        return cls(**data)


class ProgressiveCapabilitySystem:
    """渐进式能力解锁系统"""
    
    # 经验值配置
    XP_PER_USE = 10
    XP_PER_LEVEL = 1000
    XP_MULTIPLIER = {
        CapabilityLevel.NOVICE: 1.0,
        CapabilityLevel.BEGINNER: 1.2,
        CapabilityLevel.INTERMEDIATE: 1.5,
        CapabilityLevel.ADVANCED: 2.0,
        CapabilityLevel.EXPERT: 2.5,
        CapabilityLevel.MASTER: 3.0,
        CapabilityLevel.LEGENDARY: 4.0,
        CapabilityLevel.MYTHIC: 5.0,
        CapabilityLevel.DIVINE: 6.0,
        CapabilityLevel.ULTIMATE: 7.0,
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        """初始化
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir or Path.home() / ".omnia" / "progressive"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.capabilities_file = self.data_dir / "capabilities.json"
        self.progress_file = self.data_dir / "progress.json"
        
        # 加载数据
        self.capabilities: Dict[str, Capability] = {}
        self.user_progress: Dict[str, UserProgress] = {}
        
        self._load_capabilities()
        self._load_progress()
        
        # 初始化默认能力
        if not self.capabilities:
            self._initialize_default_capabilities()
    
    def _load_capabilities(self):
        """加载能力定义"""
        if self.capabilities_file.exists():
            try:
                with open(self.capabilities_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.capabilities = {
                        k: Capability.from_dict(v) for k, v in data.items()
                    }
                logger.info(f"已加载 {len(self.capabilities)} 个能力定义")
            except Exception as e:
                logger.error(f"加载能力定义失败: {e}")
    
    def _save_capabilities(self):
        """保存能力定义"""
        try:
            data = {k: v.to_dict() for k, v in self.capabilities.items()}
            with open(self.capabilities_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存能力定义失败: {e}")
    
    def _load_progress(self):
        """加载用户进度"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_progress = {
                        k: UserProgress.from_dict(v) for k, v in data.items()
                    }
                logger.info(f"已加载 {len(self.user_progress)} 个用户进度")
            except Exception as e:
                logger.error(f"加载用户进度失败: {e}")
    
    def _save_progress(self):
        """保存用户进度"""
        try:
            data = {k: v.to_dict() for k, v in self.user_progress.items()}
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户进度失败: {e}")
    
    def _initialize_default_capabilities(self):
        """初始化默认能力"""
        default_capabilities = [
            # Level 1: 新手 - 基础对话
            Capability(
                id="basic_chat",
                name="基础对话",
                description="与 AI 进行基本的对话交流",
                category=CapabilityCategory.CHAT,
                level=CapabilityLevel.NOVICE,
                unlocked=True,
                unlock_date=datetime.now()
            ),
            Capability(
                id="memory_recall",
                name="记忆回忆",
                description="回忆之前对话的内容",
                category=CapabilityCategory.MEMORY,
                level=CapabilityLevel.NOVICE,
                unlocked=True,
                unlock_date=datetime.now()
            ),
            
            # Level 2: 初学者 - 常用功能
            Capability(
                id="file_operations",
                name="文件操作",
                description="读取、写入和编辑文件",
                category=CapabilityCategory.TOOLS,
                level=CapabilityLevel.BEGINNER,
                prerequisites=["basic_chat"],
                unlock_conditions={"usage": 10}
            ),
            Capability(
                id="web_search",
                name="网络搜索",
                description="搜索互联网获取信息",
                category=CapabilityCategory.KNOWLEDGE,
                level=CapabilityLevel.BEGINNER,
                prerequisites=["basic_chat"],
                unlock_conditions={"usage": 15}
            ),
            
            # Level 3: 中级 - 进阶功能
            Capability(
                id="memory_palace",
                name="记忆宫殿",
                description="使用记忆宫殿系统存储和检索信息",
                category=CapabilityCategory.MEMORY,
                level=CapabilityLevel.INTERMEDIATE,
                prerequisites=["memory_recall"],
                unlock_conditions={"usage": 30, "xp": 500}
            ),
            Capability(
                id="workflow_basic",
                name="基础工作流",
                description="创建和执行简单的工作流",
                category=CapabilityCategory.WORKFLOW,
                level=CapabilityLevel.INTERMEDIATE,
                prerequisites=["file_operations"],
                unlock_conditions={"usage": 25}
            ),
            
            # Level 4: 高级 - 专业功能
            Capability(
                id="skill_forge",
                name="技能锻造",
                description="从对话模式中自动生成新技能",
                category=CapabilityCategory.AUTOMATION,
                level=CapabilityLevel.ADVANCED,
                prerequisites=["workflow_basic"],
                unlock_conditions={"usage": 50, "xp": 2000}
            ),
            Capability(
                id="neural_graph",
                name="神经图谱",
                description="可视化和分析知识网络",
                category=CapabilityCategory.ANALYTICS,
                level=CapabilityLevel.ADVANCED,
                prerequisites=["memory_palace"],
                unlock_conditions={"usage": 40}
            ),
            
            # Level 5: 专家 - 高级功能
            Capability(
                id="agent_swarm",
                name="Agent 集群",
                description="协调多个 AI Agent 协同工作",
                category=CapabilityCategory.WORKFLOW,
                level=CapabilityLevel.EXPERT,
                prerequisites=["skill_forge", "workflow_basic"],
                unlock_conditions={"usage": 80, "xp": 5000}
            ),
            Capability(
                id="auto_learner",
                name="自动学习",
                description="自动从对话中学习新知识",
                category=CapabilityCategory.AUTOMATION,
                level=CapabilityLevel.EXPERT,
                prerequisites=["skill_forge"],
                unlock_conditions={"usage": 70}
            ),
            
            # Level 6: 大师 - 实验性功能
            Capability(
                id="reasoning_engine",
                name="推理引擎",
                description="使用逻辑推理解决复杂问题",
                category=CapabilityCategory.KNOWLEDGE,
                level=CapabilityLevel.MASTER,
                prerequisites=["neural_graph"],
                unlock_conditions={"usage": 100, "xp": 10000}
            ),
            Capability(
                id="vector_search",
                name="向量搜索",
                description="使用语义搜索查找相关信息",
                category=CapabilityCategory.MEMORY,
                level=CapabilityLevel.MASTER,
                prerequisites=["memory_palace"],
                unlock_conditions={"usage": 90}
            ),
            
            # Level 7: 传奇 - 隐藏功能
            Capability(
                id="plan_generator",
                name="计划生成器",
                description="自动生成复杂任务的执行计划",
                category=CapabilityCategory.WORKFLOW,
                level=CapabilityLevel.LEGENDARY,
                prerequisites=["agent_swarm", "reasoning_engine"],
                unlock_conditions={"usage": 150, "xp": 20000}
            ),
            
            # Level 8: 神话 - 极客功能
            Capability(
                id="gateway_multi",
                name="多通道网关",
                description="同时连接多个外部平台",
                category=CapabilityCategory.INTEGRATION,
                level=CapabilityLevel.MYTHIC,
                prerequisites=["agent_swarm"],
                unlock_conditions={"usage": 200, "xp": 50000}
            ),
            
            # Level 9: 神圣 - 开发者功能
            Capability(
                id="mcp_custom",
                name="自定义 MCP",
                description="创建和管理自定义 MCP 服务器",
                category=CapabilityCategory.DEVELOPER,
                level=CapabilityLevel.DIVINE,
                prerequisites=["gateway_multi"],
                unlock_conditions={"usage": 300, "xp": 100000}
            ),
            
            # Level 10: 终极 - 完全解锁
            Capability(
                id="ultimate_power",
                name="终极力量",
                description="解锁所有功能和隐藏选项",
                category=CapabilityCategory.EXPERIMENTAL,
                level=CapabilityLevel.ULTIMATE,
                prerequisites=["mcp_custom", "plan_generator"],
                unlock_conditions={"usage": 500, "xp": 500000}
            ),
        ]
        
        for cap in default_capabilities:
            self.capabilities[cap.id] = cap
        
        self._save_capabilities()
        logger.info(f"已初始化 {len(default_capabilities)} 个默认能力")
    
    def get_or_create_user(self, user_id: str) -> UserProgress:
        """获取或创建用户进度"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = UserProgress(user_id=user_id)
            self._save_progress()
        return self.user_progress[user_id]
    
    def record_usage(self, user_id: str, capability_id: str):
        """记录能力使用
        
        Args:
            user_id: 用户 ID
            capability_id: 能力 ID
        """
        if capability_id not in self.capabilities:
            logger.warning(f"未知能力: {capability_id}")
            return
        
        user = self.get_or_create_user(user_id)
        capability = self.capabilities[capability_id]
        
        # 检查是否已解锁
        if not capability.unlocked and capability_id not in user.unlocked_capabilities:
            logger.warning(f"能力未解锁: {capability_id}")
            return
        
        # 更新使用统计
        user.total_usage += 1
        user.capability_usage[capability_id] += 1
        user.last_activity = datetime.now()
        
        capability.usage_count += 1
        capability.last_used = datetime.now()
        
        # 计算经验值
        xp_gain = int(self.XP_PER_USE * self.XP_MULTIPLIER[capability.level])
        user.experience_points += xp_gain
        
        # 检查升级
        self._check_level_up(user)
        
        # 检查自动解锁
        self._check_auto_unlock(user)
        
        # 保存
        self._save_capabilities()
        self._save_progress()
        
        logger.info(f"记录使用: {user_id} -> {capability_id}, XP +{xp_gain}")
    
    def _check_level_up(self, user: UserProgress):
        """检查是否升级"""
        xp_needed = self.XP_PER_LEVEL * user.current_level.value
        
        if user.experience_points >= xp_needed:
            # 升级
            next_level = CapabilityLevel(min(user.current_level.value + 1, 10))
            if next_level != user.current_level:
                user.current_level = next_level
                logger.info(f"用户 {user.user_id} 升级到 {next_level.name}")
                
                # 触发升级奖励
                self._grant_level_rewards(user)
    
    def _grant_level_rewards(self, user: UserProgress):
        """授予升级奖励"""
        # 解锁该等级的所有基础能力
        for cap_id, cap in self.capabilities.items():
            if cap.level == user.current_level and not cap.unlocked:
                if self._check_prerequisites(user, cap_id):
                    self.unlock_capability(user.user_id, cap_id, auto=True)
    
    def _check_auto_unlock(self, user: UserProgress):
        """检查自动解锁"""
        for cap_id, cap in self.capabilities.items():
            if not cap.unlocked and cap.auto_unlock and cap_id not in user.unlocked_capabilities:
                if self._check_unlock_conditions(user, cap_id):
                    self.unlock_capability(user.user_id, cap_id, auto=True)
    
    def _check_prerequisites(self, user: UserProgress, capability_id: str) -> bool:
        """检查前置条件"""
        cap = self.capabilities[capability_id]
        
        for prereq_id in cap.prerequisites:
            if prereq_id not in user.unlocked_capabilities:
                return False
        
        return True
    
    def _check_unlock_conditions(self, user: UserProgress, capability_id: str) -> bool:
        """检查解锁条件"""
        cap = self.capabilities[capability_id]
        
        # 检查前置能力
        if not self._check_prerequisites(user, capability_id):
            return False
        
        # 检查使用次数
        if "usage" in cap.unlock_conditions:
            if user.total_usage < cap.unlock_conditions["usage"]:
                return False
        
        # 检查经验值
        if "xp" in cap.unlock_conditions:
            if user.experience_points < cap.unlock_conditions["xp"]:
                return False
        
        return True
    
    def unlock_capability(self, user_id: str, capability_id: str, auto: bool = False) -> bool:
        """解锁能力
        
        Args:
            user_id: 用户 ID
            capability_id: 能力 ID
            auto: 是否自动解锁
            
        Returns:
            是否成功解锁
        """
        if capability_id not in self.capabilities:
            logger.warning(f"未知能力: {capability_id}")
            return False
        
        user = self.get_or_create_user(user_id)
        capability = self.capabilities[capability_id]
        
        if capability_id in user.unlocked_capabilities:
            logger.info(f"能力已解锁: {capability_id}")
            return True
        
        # 检查前置条件
        if not auto and not self._check_prerequisites(user, capability_id):
            logger.warning(f"前置条件不满足: {capability_id}")
            return False
        
        # 解锁
        capability.unlocked = True
        capability.unlock_date = datetime.now()
        user.unlocked_capabilities.add(capability_id)
        
        # 添加成就
        achievement = f"解锁能力: {capability.name}"
        if achievement not in user.achievements:
            user.achievements.append(achievement)
        
        self._save_capabilities()
        self._save_progress()
        
        logger.info(f"解锁能力: {user_id} -> {capability_id} ({'自动' if auto else '手动'})")
        return True
    
    def get_available_capabilities(self, user_id: str) -> List[Capability]:
        """获取用户可用的能力"""
        user = self.get_or_create_user(user_id)
        
        available = []
        for cap_id, cap in self.capabilities.items():
            if cap_id in user.unlocked_capabilities:
                available.append(cap)
        
        return sorted(available, key=lambda c: (c.level.value, c.name))
    
    def get_locked_capabilities(self, user_id: str) -> List[Capability]:
        """获取用户未解锁的能力"""
        user = self.get_or_create_user(user_id)
        
        locked = []
        for cap_id, cap in self.capabilities.items():
            if cap_id not in user.unlocked_capabilities:
                locked.append(cap)
        
        return sorted(locked, key=lambda c: (c.level.value, c.name))
    
    def get_unlock_candidates(self, user_id: str) -> List[Capability]:
        """获取可以解锁的能力（满足条件但未解锁）"""
        user = self.get_or_create_user(user_id)
        
        candidates = []
        for cap_id, cap in self.capabilities.items():
            if cap_id not in user.unlocked_capabilities:
                if self._check_unlock_conditions(user, cap_id):
                    candidates.append(cap)
        
        return sorted(candidates, key=lambda c: (c.level.value, c.name))
    
    def get_progress_summary(self, user_id: str) -> Dict:
        """获取用户进度摘要"""
        user = self.get_or_create_user(user_id)
        
        xp_for_next = self.XP_PER_LEVEL * user.current_level.value
        xp_progress = user.experience_points / xp_for_next if xp_for_next > 0 else 1.0
        
        return {
            "user_id": user_id,
            "current_level": user.current_level.name,
            "level_number": user.current_level.value,
            "total_usage": user.total_usage,
            "experience_points": user.experience_points,
            "xp_for_next_level": xp_for_next,
            "xp_progress": min(xp_progress, 1.0),
            "unlocked_count": len(user.unlocked_capabilities),
            "total_capabilities": len(self.capabilities),
            "unlock_progress": len(user.unlocked_capabilities) / len(self.capabilities),
            "achievements_count": len(user.achievements),
            "last_activity": user.last_activity.isoformat() if user.last_activity else None
        }
    
    def get_capability_recommendations(self, user_id: str, limit: int = 5) -> List[Dict]:
        """获取能力推荐"""
        user = self.get_or_create_user(user_id)
        
        recommendations = []
        
        # 推荐可以解锁的能力
        candidates = self.get_unlock_candidates(user_id)
        for cap in candidates[:limit]:
            recommendations.append({
                "type": "unlockable",
                "capability_id": cap.id,
                "name": cap.name,
                "description": cap.description,
                "level": cap.level.name,
                "category": cap.category.value,
                "reason": "已满足解锁条件"
            })
        
        # 推荐常用但未解锁的能力
        if len(recommendations) < limit:
            locked = self.get_locked_capabilities(user_id)
            for cap in locked:
                if len(recommendations) >= limit:
                    break
                
                # 计算推荐分数（基于前置能力的使用频率）
                prereq_usage = sum(
                    user.capability_usage.get(p, 0) 
                    for p in cap.prerequisites
                )
                
                if prereq_usage > 0:
                    recommendations.append({
                        "type": "suggested",
                        "capability_id": cap.id,
                        "name": cap.name,
                        "description": cap.description,
                        "level": cap.level.name,
                        "category": cap.category.value,
                        "reason": f"与您常用的功能相关",
                        "prerequisites": cap.prerequisites
                    })
        
        return recommendations
    
    def force_unlock_all(self, user_id: str):
        """强制解锁所有能力（调试用）"""
        user = self.get_or_create_user(user_id)
        
        for cap_id, cap in self.capabilities.items():
            if cap_id not in user.unlocked_capabilities:
                cap.unlocked = True
                cap.unlock_date = datetime.now()
                user.unlocked_capabilities.add(cap_id)
        
        user.current_level = CapabilityLevel.ULTIMATE
        
        self._save_capabilities()
        self._save_progress()
        
        logger.info(f"强制解锁所有能力: {user_id}")
    
    def reset_progress(self, user_id: str):
        """重置用户进度"""
        if user_id in self.user_progress:
            del self.user_progress[user_id]
            self._save_progress()
            logger.info(f"重置用户进度: {user_id}")
    
    def add_custom_capability(self, capability: Capability):
        """添加自定义能力"""
        self.capabilities[capability.id] = capability
        self._save_capabilities()
        logger.info(f"添加自定义能力: {capability.id}")
    
    def remove_capability(self, capability_id: str):
        """移除能力"""
        if capability_id in self.capabilities:
            del self.capabilities[capability_id]
            self._save_capabilities()
            logger.info(f"移除能力: {capability_id}")
    
    def get_stats(self) -> Dict:
        """获取系统统计"""
        total_unlocked = sum(1 for cap in self.capabilities.values() if cap.unlocked)
        
        level_distribution = defaultdict(int)
        for cap in self.capabilities.values():
            level_distribution[cap.level.name] += 1
        
        category_distribution = defaultdict(int)
        for cap in self.capabilities.values():
            category_distribution[cap.category.value] += 1
        
        return {
            "total_capabilities": len(self.capabilities),
            "total_unlocked": total_unlocked,
            "total_users": len(self.user_progress),
            "level_distribution": dict(level_distribution),
            "category_distribution": dict(category_distribution)
        }


# 全局实例
_progressive_system: Optional[ProgressiveCapabilitySystem] = None


def get_progressive_capability() -> ProgressiveCapabilitySystem:
    """获取渐进式能力系统实例"""
    global _progressive_system
    if _progressive_system is None:
        _progressive_system = ProgressiveCapabilitySystem()
    return _progressive_system


class CapabilityStatus:
    """能力状态枚举"""
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    IN_PROGRESS = "in_progress"
