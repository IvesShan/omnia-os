"""Collaboration Protocol — 无限 ↔ Omnia 协作协议

定义双方通信的消息格式、协议和状态机
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """消息类型"""
    # 任务相关
    TASK_REQUEST = "task_request"           # 请求对方执行任务
    TASK_ACCEPT = "task_accept"             # 接受任务
    TASK_REJECT = "task_reject"             # 拒绝任务（附带原因）
    TASK_PROGRESS = "task_progress"         # 任务进度更新
    TASK_RESULT = "task_result"             # 任务结果
    TASK_QUESTION = "task_question"         # 执行中遇到问题，询问
    
    # 讨论相关
    DISCUSSION_START = "discussion_start"   # 开始讨论
    DISCUSSION_REPLY = "discussion_reply"   # 讨论回复
    CONSENSUS_REACHED = "consensus_reached" # 达成共识
    CONSENSUS_FAILED = "consensus_failed"   # 无法达成共识，需要用户
    
    # 同步相关
    SYNC_STATUS = "sync_status"             # 同步状态
    SYNC_MEMORY = "sync_memory"             # 同步记忆
    HEARTBEAT = "heartbeat"                 # 心跳
    
    # 控制相关
    DELEGATE = "delegate"                   # 委托执行
    TAKEOVER = "takeover"                   # 接管执行
    PAUSE = "pause"                         # 暂停
    RESUME = "resume"                       # 恢复
    CANCEL = "cancel"                       # 取消


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    RUNNING = "running"
    WAITING = "waiting"        # 等待对方响应
    COMPLETED = "completed"
    FAILED = "failed"
    DELEGATED = "delegated"    # 已委托给对方


class Executor(Enum):
    """执行者"""
    OMNIA = "omnia"
    INFINITE = "infinite"
    BOTH = "both"
    USER = "user"              # 需要用户介入


@dataclass
class CollaborationMessage:
    """协作消息"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    type: MessageType = MessageType.TASK_REQUEST
    sender: str = "unknown"              # omnia / infinite
    receiver: str = "unknown"            # omnia / infinite
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 任务相关
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    task_context: Dict[str, Any] = field(default_factory=dict)
    
    # 执行相关
    executor: Optional[Executor] = None
    status: Optional[TaskStatus] = None
    progress: Optional[float] = None          # 0.0 - 1.0
    result: Optional[Dict[str, Any]] = None
    
    # 讨论相关
    discussion_topic: Optional[str] = None
    discussion_options: List[Dict] = field(default_factory=list)
    consensus: Optional[str] = None
    
    # 错误处理
    error: Optional[str] = None
    needs_user: bool = False
    user_question: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["type"] = self.type.value
        data["executor"] = self.executor.value if self.executor else None
        data["status"] = self.status.value if self.status else None
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CollaborationMessage":
        if "type" in data and isinstance(data["type"], str):
            data["type"] = MessageType(data["type"])
        if "executor" in data and isinstance(data["executor"], str):
            data["executor"] = Executor(data["executor"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "CollaborationMessage":
        return cls.from_dict(json.loads(json_str))


@dataclass
class Task:
    """协作任务"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    created_by: Executor = Executor.OMNIA
    assigned_to: Executor = Executor.OMNIA
    status: TaskStatus = TaskStatus.PENDING
    
    # 任务分解
    steps: List[Dict] = field(default_factory=list)
    current_step: int = 0
    
    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    partial_results: List[Dict] = field(default_factory=list)
    
    # 协作历史
    message_history: List[str] = field(default_factory=list)  # message ids
    
    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["created_by"] = self.created_by.value
        data["assigned_to"] = self.assigned_to.value
        data["status"] = self.status.value
        return data


class CollaborationProtocol:
    """协作协议管理器"""
    
    def __init__(self, identity: str):
        """
        Args:
            identity: "omnia" 或 "infinite"
        """
        self.identity = identity
        self.peer = "infinite" if identity == "omnia" else "omnia"
        self.pending_tasks: Dict[str, Task] = {}
        self.active_task: Optional[Task] = None
    
    # ========== 消息创建 ==========
    
    def create_task_request(self, description: str, context: Dict = None) -> CollaborationMessage:
        """创建任务请求"""
        return CollaborationMessage(
            type=MessageType.TASK_REQUEST,
            sender=self.identity,
            receiver=self.peer,
            task_id=uuid.uuid4().hex[:8],
            task_description=description,
            task_context=context or {},
            executor=Executor(self.peer),
            status=TaskStatus.PENDING,
        )
    
    def create_task_accept(self, task_id: str) -> CollaborationMessage:
        """接受任务"""
        return CollaborationMessage(
            type=MessageType.TASK_ACCEPT,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            status=TaskStatus.ACCEPTED,
        )
    
    def create_task_reject(self, task_id: str, reason: str) -> CollaborationMessage:
        """拒绝任务"""
        return CollaborationMessage(
            type=MessageType.TASK_REJECT,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            error=reason,
        )
    
    def create_task_progress(self, task_id: str, progress: float, message: str = None) -> CollaborationMessage:
        """发送进度更新"""
        return CollaborationMessage(
            type=MessageType.TASK_PROGRESS,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            progress=progress,
            metadata={"message": message} if message else {},
        )
    
    def create_task_result(self, task_id: str, result: Dict, success: bool = True) -> CollaborationMessage:
        """发送任务结果"""
        return CollaborationMessage(
            type=MessageType.TASK_RESULT,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            result=result,
            status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
        )
    
    def create_task_question(self, task_id: str, question: str, options: List[Dict] = None) -> CollaborationMessage:
        """执行中遇到问题，询问对方"""
        return CollaborationMessage(
            type=MessageType.TASK_QUESTION,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            status=TaskStatus.WAITING,
            task_context={"question": question, "options": options or []},
        )
    
    def create_delegate(self, task_id: str, reason: str, partial_result: Dict = None) -> CollaborationMessage:
        """委托对方执行"""
        return CollaborationMessage(
            type=MessageType.DELEGATE,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            task_description=reason,
            result=partial_result,
            executor=Executor(self.peer),
        )
    
    def create_consensus_failed(self, task_id: str, issue: str, user_question: str) -> CollaborationMessage:
        """无法达成共识，需要用户"""
        return CollaborationMessage(
            type=MessageType.CONSENSUS_FAILED,
            sender=self.identity,
            receiver=self.peer,
            task_id=task_id,
            needs_user=True,
            user_question=user_question,
            task_context={"issue": issue},
        )
    
    # ========== 消息处理 ==========
    
    def process_message(self, message: CollaborationMessage) -> Optional[CollaborationMessage]:
        """处理收到的消息，返回响应"""
        if message.type == MessageType.TASK_REQUEST:
            return self._handle_task_request(message)
        elif message.type == MessageType.TASK_ACCEPT:
            return self._handle_task_accept(message)
        elif message.type == MessageType.TASK_REJECT:
            return self._handle_task_reject(message)
        elif message.type == MessageType.TASK_PROGRESS:
            return self._handle_task_progress(message)
        elif message.type == MessageType.TASK_RESULT:
            return self._handle_task_result(message)
        elif message.type == MessageType.TASK_QUESTION:
            return self._handle_task_question(message)
        elif message.type == MessageType.DELEGATE:
            return self._handle_delegate(message)
        elif message.type == MessageType.CONSENSUS_FAILED:
            return self._handle_consensus_failed(message)
        return None
    
    def _handle_task_request(self, msg: CollaborationMessage) -> CollaborationMessage:
        """处理任务请求"""
        # 这里应该由具体实现决定是否接受
        # 默认接受
        task = Task(
            id=msg.task_id,
            description=msg.task_description,
            created_by=Executor(msg.sender),
            assigned_to=Executor(self.identity),
            context=msg.task_context,
        )
        self.pending_tasks[msg.task_id] = task
        return self.create_task_accept(msg.task_id)
    
    def _handle_task_accept(self, msg: CollaborationMessage) -> Optional[CollaborationMessage]:
        """处理任务接受"""
        if self.active_task and self.active_task.id == msg.task_id:
            self.active_task.status = TaskStatus.ACCEPTED
        return None
    
    def _handle_task_reject(self, msg: CollaborationMessage) -> CollaborationMessage:
        """处理任务拒绝"""
        # 需要重新分配或请求用户
        return self.create_consensus_failed(
            msg.task_id,
            issue=f"任务被拒绝: {msg.error}",
            user_question="任务无法自动分配，请指定执行者"
        )
    
    def _handle_task_progress(self, msg: CollaborationMessage) -> Optional[CollaborationMessage]:
        """处理进度更新"""
        # 可以选择响应或静默接收
        return None
    
    def _handle_task_result(self, msg: CollaborationMessage) -> Optional[CollaborationMessage]:
        """处理任务结果"""
        if self.active_task and self.active_task.id == msg.task_id:
            self.active_task.status = msg.status
            self.active_task.partial_results.append(msg.result)
            self.active_task.completed_at = datetime.now().isoformat()
        return None
    
    def _handle_task_question(self, msg: CollaborationMessage) -> CollaborationMessage:
        """处理任务问题"""
        # 这里应该由具体实现分析问题并给出建议
        question = msg.task_context.get("question", "")
        options = msg.task_context.get("options", [])
        
        # 默认建议第一个选项
        if options:
            return CollaborationMessage(
                type=MessageType.DISCUSSION_REPLY,
                sender=self.identity,
                receiver=self.peer,
                task_id=msg.task_id,
                discussion_topic=question,
                consensus=options[0].get("id") if options else None,
            )
        
        return self.create_consensus_failed(
            msg.task_id,
            issue="无法自动决策",
            user_question=question
        )
    
    def _handle_delegate(self, msg: CollaborationMessage) -> CollaborationMessage:
        """处理委托"""
        # 接受委托
        task = Task(
            id=msg.task_id,
            description=msg.task_description,
            created_by=Executor(msg.sender),
            assigned_to=Executor(self.identity),
            context=msg.result or {},
        )
        self.pending_tasks[msg.task_id] = task
        return self.create_task_accept(msg.task_id)
    
    def _handle_consensus_failed(self, msg: CollaborationMessage) -> Optional[CollaborationMessage]:
        """处理共识失败"""
        # 标记任务需要用户介入
        if self.active_task and self.active_task.id == msg.task_id:
            self.active_task.status = TaskStatus.WAITING
        return None
