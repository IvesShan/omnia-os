"""Collaboration Manager — 无限 ↔ Omnia 协作管理器

实现：
- HTTP API 端点
- 任务路由
- 状态同步
"""

from __future__ import annotations

import json
import requests
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from flask import Blueprint, request, jsonify

from ..config import COLLABORATION_STATE_FILE

from .protocol import (
    CollaborationMessage, 
    CollaborationProtocol,
    Task,
    MessageType,
    TaskStatus,
    Executor,
)


@dataclass
class PeerInfo:
    """对端信息"""
    name: str
    url: str
    identity: str  # omnia / infinite
    capabilities: List[str]
    status: str = "unknown"  # online, offline, busy


class CollaborationManager:
    """协作管理器"""
    
    def __init__(self, identity: str = "omnia"):
        """
        Args:
            identity: "omnia" 或 "infinite"
        """
        self.identity = identity
        self.protocol = CollaborationProtocol(identity)
        
        # 对端信息
        self.peer: Optional[PeerInfo] = None
        
        # 任务管理
        self.active_tasks: Dict[str, Task] = {}
        self.current_task: Optional[Task] = None
        
        # 回调
        self.on_message: Optional[Callable] = None
        self.on_task_assigned: Optional[Callable] = None
        self.on_task_result: Optional[Callable] = None
        
        # 状态文件
        self.state_file = COLLABORATION_STATE_FILE
    
    # ========== 对端管理 ==========
    
    def register_peer(self, url: str, name: str = "infinite", capabilities: List[str] = None):
        """注册对端"""
        self.peer = PeerInfo(
            name=name,
            url=url,
            identity="infinite" if self.identity == "omnia" else "omnia",
            capabilities=capabilities or [],
            status="unknown",
        )
        
        # 测试连接
        try:
            response = requests.get(f"{url}/api/collaboration/status", timeout=5)
            if response.status_code == 200:
                self.peer.status = "online"
                print(f"[Collaboration] ✅ 已连接到 {name}: {url}")
            else:
                self.peer.status = "offline"
        except:
            self.peer.status = "offline"
            print(f"[Collaboration] ⚠️ 无法连接到 {name}: {url}")
    
    def check_peer_status(self) -> str:
        """检查对端状态"""
        if not self.peer:
            return "not_configured"
        
        try:
            response = requests.get(f"{self.peer.url}/api/collaboration/status", timeout=3)
            self.peer.status = "online" if response.status_code == 200 else "offline"
        except:
            self.peer.status = "offline"
        
        return self.peer.status
    
    # ========== 消息发送 ==========
    
    def send_message(self, message: CollaborationMessage) -> Optional[CollaborationMessage]:
        """发送消息到对端"""
        if not self.peer or self.peer.status == "offline":
            print(f"[Collaboration] ⚠️ 对端离线，无法发送消息")
            return None
        
        try:
            response = requests.post(
                f"{self.peer.url}/api/collaboration/message",
                json=message.to_dict(),
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                return CollaborationMessage.from_dict(data) if data else None
            else:
                print(f"[Collaboration] ❌ 消息发送失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[Collaboration] ❌ 发送错误: {e}")
            return None
    
    # ========== 任务路由 ==========
    
    def analyze_task_best_executor(self, task_description: str, context: Dict = None) -> Executor:
        """分析任务，决定最佳执行者"""
        context = context or {}
        
        # Omnia 的优势
        omnia_keywords = [
            "本地", "文件", "目录", "读取", "写入", "执行命令",
            "shell", "硬件", "摄像头", "设备"
        ]
        
        # 无限的优势
        infinite_keywords = [
            "搜索", "网络", "API", "云", "远程", "推理",
            "分析", "总结", "生成", "飞书", "邮件"
        ]
        
        # 双方都能做
        both_keywords = [
            "列出", "检查", "测试", "验证"
        ]
        
        text = task_description.lower()
        
        omnia_score = sum(1 for kw in omnia_keywords if kw in text)
        infinite_score = sum(1 for kw in infinite_keywords if kw in text)
        
        # 检查对端可用性
        if self.peer and self.peer.status == "offline":
            # 对端离线，只能自己执行
            return Executor(self.identity)
        
        # 根据分数决定
        if omnia_score > infinite_score:
            return Executor.OMNIA
        elif infinite_score > omnia_score:
            return Executor.INFINITE
        else:
            # 默认由发起者执行
            return Executor(self.identity)
    
    def create_and_delegate_task(self, description: str, context: Dict = None) -> Optional[str]:
        """创建任务并委托给最佳执行者"""
        # 分析最佳执行者
        best_executor = self.analyze_task_best_executor(description, context)
        
        # 创建任务
        task = Task(
            description=description,
            created_by=Executor(self.identity),
            assigned_to=best_executor,
            context=context or {},
        )
        self.active_tasks[task.id] = task
        
        # 如果是自己，直接执行
        if best_executor.value == self.identity:
            self.current_task = task
            return task.id
        
        # 否则发送给对端
        message = self.protocol.create_task_request(description, context)
        message.task_id = task.id
        message.executor = best_executor
        
        response = self.send_message(message)
        
        if response and response.type == MessageType.TASK_ACCEPT:
            task.status = TaskStatus.ACCEPTED
            print(f"[Collaboration] ✅ 任务 {task.id} 已被 {best_executor.value} 接受")
            return task.id
        else:
            print(f"[Collaboration] ❌ 任务 {task.id} 被拒绝")
            task.status = TaskStatus.FAILED
            return None
    
    # ========== 任务执行 ==========
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        task.status = TaskStatus.RUNNING
        self.current_task = task
        
        # 通知对端
        msg = self.protocol.create_task_progress(task_id, 0.0, "开始执行")
        self.send_message(msg)
        
        return True
    
    def update_task_progress(self, task_id: str, progress: float, message: str = None):
        """更新任务进度"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.progress = progress
            
            # 通知对端
            msg = self.protocol.create_task_progress(task_id, progress, message)
            self.send_message(msg)
    
    def complete_task(self, task_id: str, result: Dict, success: bool = True):
        """完成任务"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.partial_results.append(result)
            task.completed_at = datetime.now().isoformat()
            
            # 通知对端
            msg = self.protocol.create_task_result(task_id, result, success)
            self.send_message(msg)
            
            if self.current_task and self.current_task.id == task_id:
                self.current_task = None
    
    def ask_peer_for_help(self, task_id: str, question: str, options: List[Dict] = None):
        """向对端求助"""
        msg = self.protocol.create_task_question(task_id, question, options)
        return self.send_message(msg)
    
    def delegate_to_peer(self, task_id: str, reason: str, partial_result: Dict = None):
        """委托给对端"""
        msg = self.protocol.create_delegate(task_id, reason, partial_result)
        return self.send_message(msg)
    
    def request_user_intervention(self, task_id: str, issue: str, question: str):
        """请求用户介入"""
        msg = self.protocol.create_consensus_failed(task_id, issue, question)
        self.send_message(msg)
        
        # 同时触发本地通知
        print(f"\n⚠️ 需要用户决策:\n{question}\n")
    
    # ========== 消息处理 ==========
    
    def handle_incoming_message(self, message_data: Dict) -> Optional[Dict]:
        """处理收到的消息"""
        message = CollaborationMessage.from_dict(message_data)
        
        # 触发回调
        if self.on_message:
            self.on_message(message)
        
        # 处理消息
        response = self.protocol.process_message(message)
        
        # 特殊处理
        if message.type == MessageType.TASK_REQUEST:
            # 任务分配
            if self.on_task_assigned:
                self.on_task_assigned(message)
        
        elif message.type == MessageType.TASK_RESULT:
            # 任务结果
            if self.on_task_result:
                self.on_task_result(message)
        
        return response.to_dict() if response else None
    
    # ========== Flask Blueprint ==========
    
    def create_blueprint(self) -> Blueprint:
        """创建 Flask Blueprint"""
        bp = Blueprint('collaboration', __name__, url_prefix='/api/collaboration')
        
        @bp.route('/status', methods=['GET'])
        def status():
            """协作状态"""
            return jsonify({
                "identity": self.identity,
                "peer": {
                    "name": self.peer.name if self.peer else None,
                    "url": self.peer.url if self.peer else None,
                    "status": self.peer.status if self.peer else "not_configured",
                } if self.peer else None,
                "active_tasks": len(self.active_tasks),
                "current_task": self.current_task.id if self.current_task else None,
            })
        
        @bp.route('/message', methods=['POST'])
        def receive_message():
            """接收消息"""
            data = request.get_json(force=True)
            response = self.handle_incoming_message(data)
            return jsonify(response) if response else jsonify({"status": "ok"})
        
        @bp.route('/register', methods=['POST'])
        def register_peer():
            """注册对端"""
            data = request.get_json(force=True)
            self.register_peer(
                url=data.get("url"),
                name=data.get("name", "peer"),
                capabilities=data.get("capabilities", [])
            )
            return jsonify({"status": "ok", "peer": self.peer.url if self.peer else None})
        
        @bp.route('/tasks', methods=['GET'])
        def list_tasks():
            """列出任务"""
            return jsonify({
                "tasks": [
                    {"id": t.id, "description": t.description, "status": t.status.value}
                    for t in self.active_tasks.values()
                ]
            })
        
        @bp.route('/task/<task_id>', methods=['GET'])
        def get_task(task_id):
            """获取任务详情"""
            if task_id in self.active_tasks:
                return jsonify(self.active_tasks[task_id].to_dict())
            return jsonify({"error": "Task not found"}), 404
        
        return bp


# 全局实例
_manager: Optional[CollaborationManager] = None

def get_collaboration_manager() -> CollaborationManager:
    """获取全局协作管理器"""
    global _manager
    if _manager is None:
        _manager = CollaborationManager()
    return _manager
