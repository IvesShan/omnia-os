"""
主题识别引擎
自动识别对话主题，支持主题切换检测和主题链追踪
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import re


@dataclass
class Topic:
    """主题"""
    topic_id: str
    name: str
    category: str
    keywords: List[str]
    confidence: float
    created_at: datetime
    message_count: int = 0


@dataclass
class TopicShift:
    """主题切换"""
    from_topic: str
    to_topic: str
    timestamp: datetime
    session_id: str
    trigger_message: str
    shift_type: str  # smooth, abrupt, return


class TopicRecognizer:
    """主题识别器"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(
            Path.home() / ".omnia" / "topics.db"
        )
        self._init_db()
        
        # 预定义主题
        self.predefined_topics = {
            '技术': {
                'keywords': ['代码', 'bug', '功能', '实现', '开发', '优化', '测试', '部署', '架构'],
                'category': 'work'
            },
            '业务': {
                'keywords': ['客户', '订单', '收入', '市场', '推广', '销售', '合作', '谈判'],
                'category': 'work'
            },
            '产品': {
                'keywords': ['产品', '需求', '用户', '体验', '设计', '原型', '迭代'],
                'category': 'work'
            },
            '学习': {
                'keywords': ['学习', '课程', '培训', '知识', '理解', '教程', '文档', '研究'],
                'category': 'growth'
            },
            '生活': {
                'keywords': ['生活', '休息', '健康', '家庭', '朋友', '旅行', '美食'],
                'category': 'personal'
            },
            '项目': {
                'keywords': ['omnia', '喵修匠', '懂机帝', 'openclaw', '项目', '计划'],
                'category': 'work'
            },
            '日常': {
                'keywords': ['今天', '明天', '计划', '安排', '提醒', '待办'],
                'category': 'personal'
            }
        }
        
        # 主题切换检测阈值
        self.shift_threshold = 0.3
    
    def _init_db(self):
        """初始化主题数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                keywords TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS topic_shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_topic TEXT,
                to_topic TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                trigger_message TEXT,
                shift_type TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS message_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                topic_id TEXT,
                confidence REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_id ON topics(topic_id)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id ON topic_shifts(session_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def recognize_topic(self, message: str) -> Tuple[str, float]:
        """识别单条消息的主题"""
        message_lower = message.lower()
        
        # 计算各主题得分
        scores = {}
        
        for topic_name, topic_info in self.predefined_topics.items():
            keywords = topic_info['keywords']
            score = sum(1 for kw in keywords if kw in message_lower)
            
            if score > 0:
                # 归一化得分
                scores[topic_name] = score / len(keywords)
        
        # 返回得分最高的主题
        if scores:
            best_topic = max(scores.items(), key=lambda x: x[1])
            return best_topic[0], best_topic[1]
        
        # 默认主题
        return '日常', 0.5
    
    def detect_topic_shift(self, history: List[Dict], window_size: int = 3) -> Optional[TopicShift]:
        """检测主题切换"""
        if len(history) < window_size * 2:
            return None
        
        # 分析前后窗口的主题
        recent_messages = history[-window_size:]
        previous_messages = history[-window_size*2:-window_size]
        
        # 提取主题
        recent_topics = []
        for msg in recent_messages:
            topic, _ = self.recognize_topic(msg.get('content', ''))
            recent_topics.append(topic)
        
        previous_topics = []
        for msg in previous_messages:
            topic, _ = self.recognize_topic(msg.get('content', ''))
            previous_topics.append(topic)
        
        # 统计最常见主题
        from collections import Counter
        recent_common = Counter(recent_topics).most_common(1)[0][0]
        previous_common = Counter(previous_topics).most_common(1)[0][0]
        
        # 检测切换
        if recent_common != previous_common:
            # 判断切换类型
            shift_type = self._classify_shift_type(
                previous_common,
                recent_common,
                recent_messages[-1].get('content', '')
            )
            
            return TopicShift(
                from_topic=previous_common,
                to_topic=recent_common,
                timestamp=datetime.now(),
                session_id='',  # 需要外部传入
                trigger_message=recent_messages[-1].get('content', ''),
                shift_type=shift_type
            )
        
        return None
    
    def _classify_shift_type(self, from_topic: str, to_topic: str, trigger_message: str) -> str:
        """分类主题切换类型"""
        # 检查是否有过渡词
        transition_words = ['对了', '顺便', '说起来', '话说', '换个话题']
        if any(word in trigger_message for word in transition_words):
            return 'smooth'
        
        # 检查是否是回到之前的话题
        # TODO: 需要会话历史
        return 'abrupt'
    
    def get_topic_chain(self, session_id: str) -> List[Dict]:
        """获取会话的主题链"""
        conn = sqlite3.connect(self.db_path)
        
        rows = conn.execute('''
            SELECT from_topic, to_topic, timestamp, trigger_message, shift_type
            FROM topic_shifts
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,)).fetchall()
        
        conn.close()
        
        chain = []
        for row in rows:
            chain.append({
                'from': row[0],
                'to': row[1],
                'timestamp': row[2],
                'trigger': row[3][:50] if row[3] else '',
                'type': row[4]
            })
        
        return chain
    
    def save_topic_shift(self, shift: TopicShift):
        """保存主题切换记录"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO topic_shifts 
            (from_topic, to_topic, timestamp, session_id, trigger_message, shift_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            shift.from_topic,
            shift.to_topic,
            shift.timestamp.isoformat(),
            shift.session_id,
            shift.trigger_message,
            shift.shift_type
        ))
        conn.commit()
        conn.close()
    
    def get_topic_stats(self, days: int = 7) -> Dict:
        """获取主题统计"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(days=days)
        
        # 主题分布
        topic_dist = conn.execute('''
            SELECT to_topic, COUNT(*) as count
            FROM topic_shifts
            WHERE timestamp >= ?
            GROUP BY to_topic
            ORDER BY count DESC
        ''', (cutoff.isoformat(),)).fetchall()
        
        # 切换类型分布
        shift_types = conn.execute('''
            SELECT shift_type, COUNT(*) as count
            FROM topic_shifts
            WHERE timestamp >= ?
            GROUP BY shift_type
        ''', (cutoff.isoformat(),)).fetchall()
        
        # 平均主题持续时间
        # TODO: 需要更复杂的计算
        
        conn.close()
        
        return {
            'topic_distribution': {row[0]: row[1] for row in topic_dist},
            'shift_types': {row[0]: row[1] for row in shift_types},
            'total_shifts': sum(row[1] for row in topic_dist)
        }
    
    def get_hot_topics(self, limit: int = 10) -> List[Dict]:
        """获取热门主题"""
        conn = sqlite3.connect(self.db_path)
        
        rows = conn.execute('''
            SELECT to_topic, COUNT(*) as count
            FROM topic_shifts
            GROUP BY to_topic
            ORDER BY count DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        
        conn.close()
        
        return [
            {
                'topic': row[0],
                'count': row[1]
            }
            for row in rows
        ]
    
    def export_topic_data(self, output_path: str, days: int = 30):
        """导出主题数据"""
        stats = self.get_topic_stats(days)
        hot = self.get_hot_topics()
        
        data = {
            'stats': stats,
            'hot_topics': hot,
            'exported_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path


# 全局主题识别器实例
_recognizer_instance: Optional[TopicRecognizer] = None


def get_topic_recognizer() -> TopicRecognizer:
    """获取全局主题识别器实例"""
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = TopicRecognizer()
    return _recognizer_instance
