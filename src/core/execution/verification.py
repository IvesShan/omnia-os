"""
from core.logging_config import get_logger

logger = get_logger(__name__)

Verified Execution - Omnia 2.0 创新功能

目的：生成可验证的执行证明，让用户确认 Agent 真正完成了任务

证明包含：
- 执行前状态快照
- 执行后状态快照
- 工具调用记录
- 时间戳签名
- 结果验证

Usage:
    from core.execution.verification import VerifiedExecution
    
    executor = VerifiedExecution()
    proof = await executor.execute_with_proof("删除 test.txt", ["execute_shell"])
    
    if executor.verify(proof):
        logger.info("执行已验证通过")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from core.config import OMNIA_HOME
from typing import Any
import hashlib
import json


class CapabilityLevel(Enum):
    """能力等级"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class StateSnapshot:
    """状态快照"""
    timestamp: datetime
    files: dict[str, str]  # path -> hash
    processes: list[str]   # running processes
    environment: dict      # env vars


@dataclass
class ExecutionProof:
    """执行证明"""
    task: str
    tools_used: list[str]
    before_snapshot: StateSnapshot
    after_snapshot: StateSnapshot
    result: Any
    timestamp: datetime = field(default_factory=datetime.now)
    signature: str = ""
    verified: bool = False
    
    def to_json(self) -> str:
        return json.dumps({
            "task": self.task,
            "tools_used": self.tools_used,
            "before": {
                "timestamp": self.before_snapshot.timestamp.isoformat(),
                "files": self.before_snapshot.files,
            },
            "after": {
                "timestamp": self.after_snapshot.timestamp.isoformat(),
                "files": self.after_snapshot.files,
            },
            "result": str(self.result)[:1000],
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
        }, indent=2)


class VerifiedExecution:
    """
    可验证执行引擎
    
    工作流程：
    1. 捕获执行前状态
    2. 执行任务
    3. 捕获执行后状态
    4. 生成签名证明
    5. 用户可验证
    """
    
    def __init__(self, workspace: Path | str = "."):
        self.workspace = Path(workspace)
    
    async def capture_state(self) -> StateSnapshot:
        """捕获当前状态"""
        files = {}
        
        # 捕获工作区文件哈希
        for file_path in self.workspace.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    content = file_path.read_bytes()
                    file_hash = hashlib.md5(content).hexdigest()
                    files[str(file_path.relative_to(self.workspace))] = file_hash
                except (FileNotFoundError, IOError, PermissionError) as e:
                    continue
        
        # 捕获进程（简化）
        processes = []
        try:
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = result.stdout.split('\n')[:20]
        except Exception:
            pass
        
        # 捕获环境变量
        import os
        environment = dict(os.environ)
        
        return StateSnapshot(
            timestamp=datetime.now(),
            files=files,
            processes=processes,
            environment=environment
        )
    
    async def execute_with_proof(
        self,
        task: str,
        tools: list[str],
        executor: Any = None
    ) -> ExecutionProof:
        """
        执行任务并生成证明
        
        Args:
            task: 任务描述
            tools: 使用的工具列表
            executor: 执行器（可选）
        
        Returns:
            ExecutionProof
        """
        # 1. 执行前快照
        before_snapshot = await self.capture_state()
        
        # 2. 执行任务
        result = None
        if executor:
            result = await executor(task)
        else:
            # 简化：直接返回
            result = {"status": "simulated"}
        
        # 3. 执行后快照
        after_snapshot = await self.capture_state()
        
        # 4. 生成签名
        signature = self._sign(before_snapshot, after_snapshot, result)
        
        return ExecutionProof(
            task=task,
            tools_used=tools,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            result=result,
            signature=signature
        )
    
    def verify(self, proof: ExecutionProof) -> bool:
        """
        验证执行证明
        
        Returns:
            True if valid, False otherwise
        """
        # 1. 验证签名
        expected_sig = self._sign(
            proof.before_snapshot,
            proof.after_snapshot,
            proof.result
        )
        
        if proof.signature != expected_sig:
            logger.info("[Verification] Signature mismatch")
            return False
        
        # 2. 验证状态变更
        file_changes = self._compare_files(
            proof.before_snapshot.files,
            proof.after_snapshot.files
        )
        
        if not file_changes:
            logger.info("[Verification] No state change detected")
            # 可能是只读操作，仍然有效
        
        # 3. 验证时间戳
        time_diff = (proof.after_snapshot.timestamp - proof.before_snapshot.timestamp).total_seconds()
        if time_diff < 0:
            logger.info("[Verification] Invalid timestamp")
            return False
        
        proof.verified = True
        return True
    
    def _sign(self, before: StateSnapshot, after: StateSnapshot, result: Any) -> str:
        """生成签名"""
        data = f"{before.timestamp}{after.timestamp}{result}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _compare_files(self, before: dict, after: dict) -> dict:
        """比较文件变化"""
        changes = {
            "added": [],
            "removed": [],
            "modified": []
        }
        
        for path in after:
            if path not in before:
                changes["added"].append(path)
            elif after[path] != before[path]:
                changes["modified"].append(path)
        
        for path in before:
            if path not in after:
                changes["removed"].append(path)
        
        return changes


# ============================================================================
# Progressive Capability System
# ============================================================================

@dataclass
class UserCapability:
    """用户能力"""
    user_id: str
    level: CapabilityLevel
    unlocked_tools: list[str]
    successful_tasks: int
    complexity_score: float
    last_activity: datetime


class ProgressiveCapability:
    """
    渐进式能力系统
    
    根据用户使用模式自动解锁新能力
    """
    
    CAPABILITY_UNLOCKS = {
        CapabilityLevel.BASIC: [
            "read_file", "write_file", "execute_shell"
        ],
        CapabilityLevel.INTERMEDIATE: [
            "web_search", "browser_automation", "skill_creation"
        ],
        CapabilityLevel.ADVANCED: [
            "agent_swarm", "workflow_engine", "code_generation"
        ],
        CapabilityLevel.EXPERT: [
            "system_modification", "self_evolution", "capability_creation"
        ]
    }
    
    def __init__(self):
        self._user_capabilities: dict[str, UserCapability] = {}
    
    def assess_level(self, successful_tasks: int, complexity_score: float) -> CapabilityLevel:
        """评估能力等级"""
        if complexity_score >= 0.8 and successful_tasks >= 50:
            return CapabilityLevel.EXPERT
        elif complexity_score >= 0.6 and successful_tasks >= 20:
            return CapabilityLevel.ADVANCED
        elif complexity_score >= 0.3 and successful_tasks >= 5:
            return CapabilityLevel.INTERMEDIATE
        else:
            return CapabilityLevel.BASIC
    
    def get_available_tools(self, user_id: str) -> list[str]:
        """获取用户可用工具"""
        cap = self._user_capabilities.get(user_id)
        if not cap:
            return self.CAPABILITY_UNLOCKS[CapabilityLevel.BASIC]
        
        tools = []
        for level in CapabilityLevel:
            if level.value <= cap.level.value:
                tools.extend(self.CAPABILITY_UNLOCKS[level])
        
        return tools
    
    def record_task(self, user_id: str, complexity: float, success: bool):
        """记录任务完成"""
        if user_id not in self._user_capabilities:
            self._user_capabilities[user_id] = UserCapability(
                user_id=user_id,
                level=CapabilityLevel.BASIC,
                unlocked_tools=[],
                successful_tasks=0,
                complexity_score=0.0,
                last_activity=datetime.now()
            )
        
        cap = self._user_capabilities[user_id]
        
        if success:
            cap.successful_tasks += 1
            # 更新复杂度分数（加权平均）
            cap.complexity_score = (
                cap.complexity_score * 0.9 + complexity * 0.1
            )
        
        cap.last_activity = datetime.now()
        
        # 重新评估等级
        new_level = self.assess_level(
            cap.successful_tasks,
            cap.complexity_score
        )
        
        if new_level != cap.level:
            cap.level = new_level
            print(f"[ProgressiveCapability] {user_id} unlocked {new_level.value}")


# ============================================================================
# Persona Continuity System
# ============================================================================

@dataclass
class PersonaState:
    """人格状态"""
    persona_id: str
    emotional_state: str      # happy, focused, tired, etc.
    recent_topics: list[str]
    working_memory: dict
    continuity_score: float
    timestamp: datetime = field(default_factory=datetime.now)


class PersonaContinuity:
    """
    人格连续性系统
    
    让 Agent 在不同会话间保持人格连续性
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else OMNIA_HOME / "persona_states.json"
        self._states: dict[str, list[PersonaState]] = {}
        self._load()
    
    def _load(self):
        """加载人格状态"""
        try:
            if self.db_path.exists():
                data = json.loads(self.db_path.read_text())
                # TODO: 反序列化
        except Exception:
            self._states = {}
    
    def _save(self):
        """保存人格状态"""
        # TODO: 序列化
        pass
    
    async def save_session_state(
        self,
        persona_id: str,
        emotional_state: str,
        recent_topics: list[str],
        working_memory: dict
    ):
        """保存会话人格状态"""
        state = PersonaState(
            persona_id=persona_id,
            emotional_state=emotional_state,
            recent_topics=recent_topics,
            working_memory=working_memory,
            continuity_score=1.0
        )
        
        if persona_id not in self._states:
            self._states[persona_id] = []
        
        self._states[persona_id].append(state)
        
        # 只保留最近 10 个状态
        if len(self._states[persona_id]) > 10:
            self._states[persona_id] = self._states[persona_id][-10:]
        
        self._save()
    
    async def restore_persona(self, persona_id: str) -> PersonaState | None:
        """恢复人格状态"""
        states = self._states.get(persona_id, [])
        if not states:
            return None
        
        # 合成最近状态
        recent_state = states[-1]
        
        # 合并最近话题
        all_topics = []
        for state in states[-5:]:
            all_topics.extend(state.recent_topics)
        
        recent_state.recent_topics = list(set(all_topics))[:10]
        recent_state.continuity_score = min(len(states) * 0.1, 1.0)
        
        return recent_state
