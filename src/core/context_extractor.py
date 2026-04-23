"""
上下文提取器
智能提取对话主题、摘要、关键决策等
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ExtractedContext:
    """提取的上下文"""
    topic: str
    summary: str
    key_decisions: List[str]
    active_project: Optional[str]
    next_steps: List[str]
    entities: Dict[str, List[str]]
    sentiment: str  # positive, neutral, negative
    importance: int  # 1-5


class ContextExtractor:
    """上下文提取器"""
    
    def __init__(self):
        # 项目关键词
        self.project_keywords = [
            'omnia', '喵修匠', '懂机帝', 'openclaw',
            '无人机', '维修', '培训', '课程'
        ]
        
        # 决策关键词
        self.decision_keywords = [
            '决定', '选择', '采用', '使用', '方案',
            '决定要', '选择了', '确定了', '敲定'
        ]
        
        # 下一步关键词
        self.next_step_keywords = [
            '下一步', '接下来', '然后', '之后',
            '需要', '要', '计划', '准备'
        ]
        
        # 主题关键词权重
        self.topic_weights = {
            '技术': ['代码', 'bug', '功能', '实现', '开发', '优化'],
            '业务': ['客户', '订单', '收入', '市场', '推广'],
            '学习': ['学习', '课程', '培训', '知识', '理解'],
            '生活': ['生活', '休息', '健康', '家庭', '朋友']
        }
    
    def extract_topic(self, message: str, history: List[Dict] = None) -> str:
        """提取对话主题"""
        # 合并消息
        text = message
        if history:
            text = ' '.join([h.get('content', '') for h in history[-5:]]) + ' ' + text
        
        # 计算各主题得分
        scores = {}
        for topic, keywords in self.topic_weights.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[topic] = score
        
        # 返回得分最高的主题
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # 默认主题
        return '日常对话'
    
    def extract_summary(self, messages: List[Dict], max_length: int = 200) -> str:
        """生成对话摘要"""
        if not messages:
            return ""
        
        # 提取关键句子
        key_sentences = []
        
        for msg in messages:
            content = msg.get('content', '')
            role = msg.get('role', '')
            
            # 用户消息优先
            if role == 'user':
                # 提取问句和陈述句
                sentences = re.split(r'[。！？\n]', content)
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) > 5 and any(kw in sent for kw in self.decision_keywords + self.next_step_keywords):
                        key_sentences.append(sent)
        
        # 如果关键句子不够，添加用户消息
        if len(key_sentences) < 3:
            for msg in messages:
                if msg.get('role') == 'user':
                    content = msg.get('content', '').strip()
                    if len(content) > 5:
                        key_sentences.append(content[:100])
        
        # 合并成摘要
        summary = '；'.join(key_sentences[:3])
        
        # 截断
        if len(summary) > max_length:
            summary = summary[:max_length] + '...'
        
        return summary or "对话内容"
    
    def extract_key_decisions(self, messages: List[Dict]) -> List[str]:
        """提取关键决策"""
        decisions = []
        
        for msg in messages:
            content = msg.get('content', '')
            
            # 查找决策关键词
            for keyword in self.decision_keywords:
                if keyword in content:
                    # 提取包含关键词的句子
                    sentences = re.split(r'[。！？\n]', content)
                    for sent in sentences:
                        if keyword in sent and len(sent) > 5:
                            decisions.append(sent.strip())
                            break
        
        # 去重并限制数量
        return list(dict.fromkeys(decisions))[:5]
    
    def detect_active_project(self, message: str) -> Optional[str]:
        """检测活动项目"""
        message_lower = message.lower()
        
        for project in self.project_keywords:
            if project in message_lower:
                return project
        
        return None
    
    def extract_next_steps(self, messages: List[Dict]) -> List[str]:
        """提取下一步行动"""
        next_steps = []
        
        for msg in reversed(messages):  # 从最新消息开始
            content = msg.get('content', '')
            
            # 查找下一步关键词
            for keyword in self.next_step_keywords:
                if keyword in content:
                    # 提取包含关键词的句子
                    sentences = re.split(r'[。！？\n]', content)
                    for sent in sentences:
                        if keyword in sent and len(sent) > 5:
                            next_steps.append(sent.strip())
                            break
        
        # 去重并限制数量
        return list(dict.fromkeys(next_steps))[:3]
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取实体（人名、地名、时间、项目等）"""
        entities = {
            'projects': [],
            'dates': [],
            'names': [],
            'technologies': []
        }
        
        # 提取项目名
        for project in self.project_keywords:
            if project in text.lower():
                entities['projects'].append(project)
        
        # 提取日期
        date_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{1,2}月\d{1,2}日',
            r'今天|明天|后天|下周|下个月'
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            entities['dates'].extend(matches)
        
        # 提取技术关键词
        tech_keywords = [
            'python', 'javascript', 'react', 'vue', 'node',
            'docker', 'kubernetes', 'sql', 'mongodb', 'redis'
        ]
        for tech in tech_keywords:
            if tech in text.lower():
                entities['technologies'].append(tech)
        
        return entities
    
    def analyze_sentiment(self, text: str) -> str:
        """分析情感倾向"""
        # 简单的情感分析（基于关键词）
        positive_words = ['好', '棒', '喜欢', '开心', '成功', '完成', '解决']
        negative_words = ['不好', '问题', '错误', '失败', '讨厌', '麻烦', '困难']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def calculate_importance(self, message: str, has_decision: bool, has_next_step: bool) -> int:
        """计算重要性（1-5）"""
        score = 3  # 默认中等
        
        # 有决策 +1
        if has_decision:
            score += 1
        
        # 有下一步 +1
        if has_next_step:
            score += 1
        
        # 包含项目关键词 +1
        if any(kw in message.lower() for kw in self.project_keywords):
            score += 1
        
        # 包含时间关键词 +1
        time_keywords = ['今天', '明天', '下周', '月底', '截止']
        if any(kw in message for kw in time_keywords):
            score += 1
        
        return min(score, 5)
    
    def extract_full_context(self, message: str, history: List[Dict] = None) -> ExtractedContext:
        """提取完整上下文"""
        messages = history or []
        
        # 提取各部分
        topic = self.extract_topic(message, messages)
        summary = self.extract_summary(messages)
        key_decisions = self.extract_key_decisions(messages)
        active_project = self.detect_active_project(message)
        next_steps = self.extract_next_steps(messages)
        entities = self.extract_entities(message)
        sentiment = self.analyze_sentiment(message)
        importance = self.calculate_importance(
            message,
            has_decision=len(key_decisions) > 0,
            has_next_step=len(next_steps) > 0
        )
        
        return ExtractedContext(
            topic=topic,
            summary=summary,
            key_decisions=key_decisions,
            active_project=active_project,
            next_steps=next_steps,
            entities=entities,
            sentiment=sentiment,
            importance=importance
        )
    
    def to_dict(self, context: ExtractedContext) -> Dict:
        """转换为字典"""
        return asdict(context)
    
    def to_json(self, context: ExtractedContext) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(context), ensure_ascii=False, indent=2)


# 全局提取器实例
_extractor_instance: Optional[ContextExtractor] = None


def get_context_extractor() -> ContextExtractor:
    """获取全局提取器实例"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = ContextExtractor()
    return _extractor_instance
