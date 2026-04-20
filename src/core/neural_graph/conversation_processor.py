"""Conversation Processor - 从对话日志提取实体和关系，构建神经图谱"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .graph import NeuralGraph, Entity, Relation
from .extractor import EntityExtractor
from .inferencer import RelationInferencer
from core.config import MEMORY_PALACE_DB


class ConversationProcessor:
    """从 conversation_logs 提取实体和关系，构建神经图谱
    
    这是缺失的一环！连接 conversation_logs → neural_graph
    """
    
    def __init__(self, db_path: str = None, api_key: str = None, provider: str = None):
        self.db_path = db_path or str(MEMORY_PALACE_DB)
        self.graph = NeuralGraph(self.db_path)
        self.extractor = EntityExtractor(api_key, provider)
        self.inferencer = RelationInferencer()
        
        # 统计
        self.stats = {
            "processed": 0,
            "nodes_added": 0,
            "edges_added": 0,
            "errors": 0,
        }
    
    def process_all_conversations(
        self, 
        batch_size: int = 100, 
        use_llm: bool = False,
        limit: int = None,
    ) -> Dict:
        """处理所有历史对话
        
        Args:
            batch_size: 每批处理数量
            use_llm: 是否使用 LLM 补充（空闲时为 True）
            limit: 限制处理数量（用于测试）
        
        Returns:
            处理统计
        """
        print(f"[ConversationProcessor] 开始处理历史对话...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有对话，按 session 分组
        query = """
            SELECT id, session_id, turn_number, role, content, created_at
            FROM conversation_logs
            ORDER BY created_at ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        print(f"[ConversationProcessor] 找到 {len(rows)} 条对话记录")
        
        # 按 session 分组
        sessions = {}
        for row in rows:
            sid = row['session_id']
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(dict(row))
        
        print(f"[ConversationProcessor] 共 {len(sessions)} 个会话")
        
        # 处理每个 session
        for i, (session_id, turns) in enumerate(sessions.items()):
            if i % 100 == 0:
                print(f"  进度: {i}/{len(sessions)} sessions, nodes={self.stats['nodes_added']}, edges={self.stats['edges_added']}")
            
            self._process_session(session_id, turns, use_llm)
        
        print(f"\n[ConversationProcessor] 完成！")
        print(f"  - 处理对话: {self.stats['processed']} 条")
        print(f"  - 添加节点: {self.stats['nodes_added']} 个")
        print(f"  - 添加边: {self.stats['edges_added']} 条")
        print(f"  - 错误: {self.stats['errors']} 个")
        
        return self.stats
    
    def _process_session(self, session_id: str, turns: List[Dict], use_llm: bool):
        """处理单个会话"""
        # 合并用户和助手消息
        user_messages = []
        assistant_messages = []
        
        for turn in turns:
            if turn['role'] == 'user':
                user_messages.append(turn['content'])
            else:
                assistant_messages.append(turn['content'])
        
        # 合并文本
        full_text = "\n".join(user_messages + assistant_messages)
        
        # 提取实体
        entities = self.extractor.extract(full_text, use_llm=use_llm)
        
        # 添加节点（修正调用方式）
        for entity in entities:
            try:
                self.graph.add_node(
                    entity_type=entity.type,
                    entity_name=entity.name,
                    canonical_name=entity.canonical_name,
                    properties=entity.properties,
                )
                self.stats['nodes_added'] += 1
            except Exception as e:
                self.stats['errors'] += 1
        
        # 推断关系
        relations = self.inferencer.infer_batch(entities, full_text)
        
        # 添加边（修正调用方式）
        for relation in relations:
            try:
                self.graph.add_edge(
                    source_name=relation.source,
                    target_name=relation.target,
                    relation_type=relation.type,
                    weight=relation.weight,
                )
                self.stats['edges_added'] += 1
            except Exception as e:
                self.stats['errors'] += 1
        
        self.stats['processed'] += len(turns)
    
    def process_single_turn(
        self,
        user_message: str,
        assistant_message: str,
        session_id: str = None,
        use_llm: bool = False,
    ) -> Dict:
        """处理单轮对话（实时处理用）
        
        Args:
            user_message: 用户消息
            assistant_message: 助手回复
            session_id: 会话 ID
            use_llm: 是否使用 LLM
        
        Returns:
            提取结果
        """
        full_text = f"{user_message}\n{assistant_message}"
        
        # 提取实体
        entities = self.extractor.extract(full_text, use_llm=use_llm)
        
        # 添加节点
        nodes_added = 0
        for entity in entities:
            try:
                self.graph.add_node(
                    entity_type=entity.type,
                    entity_name=entity.name,
                    canonical_name=entity.canonical_name,
                    properties=entity.properties,
                )
                nodes_added += 1
            except Exception:
                pass
        
        # 推断关系
        relations = self.inferencer.infer_batch(entities, full_text)
        
        # 添加边
        edges_added = 0
        for relation in relations:
            try:
                self.graph.add_edge(
                    source_name=relation.source,
                    target_name=relation.target,
                    relation_type=relation.type,
                    weight=relation.weight,
                )
                edges_added += 1
            except Exception:
                pass
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relations": [r.to_dict() for r in relations],
            "nodes_added": nodes_added,
            "edges_added": edges_added,
        }
    
    def get_unprocessed_count(self) -> int:
        """获取未处理的对话数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否有处理标记
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conversation_processed'
        """)
        
        if not cursor.fetchone():
            # 没有标记表，所有对话都未处理
            cursor.execute("SELECT COUNT(*) FROM conversation_logs")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        
        # 有标记表，统计未处理的
        cursor.execute("""
            SELECT COUNT(*) FROM conversation_logs cl
            WHERE NOT EXISTS (
                SELECT 1 FROM conversation_processed cp
                WHERE cp.conversation_id = cl.id
            )
        """)
        count = cursor.fetchone()[0]
        conn.close()
        return count


def process_conversation_history(
    batch_size: int = 100,
    use_llm: bool = False,
    limit: int = None,
) -> Dict:
    """处理所有历史对话（便捷函数）"""
    processor = ConversationProcessor()
    return processor.process_all_conversations(batch_size, use_llm, limit)


def process_single_turn(
    user_message: str,
    assistant_message: str,
    session_id: str = None,
    use_llm: bool = False,
) -> Dict:
    """处理单轮对话（便捷函数）"""
    processor = ConversationProcessor()
    return processor.process_single_turn(user_message, assistant_message, session_id, use_llm)
