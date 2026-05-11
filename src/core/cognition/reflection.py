"""
反思模块
Reflection Module

功能：
- 自我评估和改进
- 分析对话质量
- 生成改进建议
- 追踪学习进度
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReflectionType(Enum):
    """反思类型"""
    CONVERSATION_QUALITY = "conversation_quality"    # 对话质量
    TOOL_USAGE = "tool_usage"                        # 工具使用
    DECISION_MAKING = "decision_making"              # 决策制定
    ERROR_ANALYSIS = "error_analysis"                # 错误分析
    LEARNING_PROGRESS = "learning_progress"          # 学习进度
    USER_SATISFACTION = "user_satisfaction"          # 用户满意度
    EFFICIENCY = "efficiency"                        # 效率分析
    KNOWLEDGE_GAP = "knowledge_gap"                  # 知识缺口


class Severity(Enum):
    """严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReflectionInsight:
    """反思洞察"""
    id: str
    type: ReflectionType
    title: str
    description: str
    severity: Severity
    score: float  # 0.0 - 1.0
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ReflectionInsight':
        """从字典创建"""
        data['type'] = ReflectionType(data['type'])
        data['severity'] = Severity(data['severity'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['resolved_at'] = datetime.fromisoformat(data['resolved_at']) if data['resolved_at'] else None
        return cls(**data)


@dataclass
class ConversationMetrics:
    """对话指标"""
    session_id: str
    message_count: int = 0
    tool_calls: int = 0
    successful_tools: int = 0
    failed_tools: int = 0
    avg_response_time: float = 0.0
    user_feedback_score: Optional[float] = None
    context_switches: int = 0
    clarification_requests: int = 0
    error_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat() if self.start_time else None
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data


class ReflectionEngine:
    """反思引擎"""
    
    # 评分阈值
    QUALITY_THRESHOLDS = {
        "excellent": 0.9,
        "good": 0.7,
        "acceptable": 0.5,
        "poor": 0.3,
        "critical": 0.0
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        """初始化
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir or Path.home() / ".omnia" / "reflection"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.insights_file = self.data_dir / "insights.json"
        self.metrics_file = self.data_dir / "metrics.json"
        
        # 加载数据
        self.insights: List[ReflectionInsight] = []
        self.session_metrics: Dict[str, ConversationMetrics] = {}
        
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        # 加载洞察
        if self.insights_file.exists():
            try:
                with open(self.insights_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.insights = [ReflectionInsight.from_dict(i) for i in data]
                logger.info(f"已加载 {len(self.insights)} 个反思洞察")
            except Exception as e:
                logger.error(f"加载洞察失败: {e}")
        
        # 加载指标
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.session_metrics = {
                        k: ConversationMetrics(**v) for k, v in data.items()
                    }
                logger.info(f"已加载 {len(self.session_metrics)} 个会话指标")
            except Exception as e:
                logger.error(f"加载指标失败: {e}")
    
    def _save_data(self):
        """保存数据"""
        try:
            # 保存洞察
            insights_data = [i.to_dict() for i in self.insights]
            with open(self.insights_file, 'w', encoding='utf-8') as f:
                json.dump(insights_data, f, ensure_ascii=False, indent=2)
            
            # 保存指标
            metrics_data = {k: v.to_dict() for k, v in self.session_metrics.items()}
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    def start_session_tracking(self, session_id: str):
        """开始会话追踪"""
        self.session_metrics[session_id] = ConversationMetrics(
            session_id=session_id,
            start_time=datetime.now()
        )
        self._save_data()
    
    def record_message(self, session_id: str):
        """记录消息"""
        if session_id in self.session_metrics:
            self.session_metrics[session_id].message_count += 1
            self._save_data()
    
    def record_tool_call(self, session_id: str, success: bool):
        """记录工具调用"""
        if session_id in self.session_metrics:
            metrics = self.session_metrics[session_id]
            metrics.tool_calls += 1
            if success:
                metrics.successful_tools += 1
            else:
                metrics.failed_tools += 1
            self._save_data()
    
    def record_error(self, session_id: str):
        """记录错误"""
        if session_id in self.session_metrics:
            self.session_metrics[session_id].error_count += 1
            self._save_data()
    
    def end_session_tracking(self, session_id: str):
        """结束会话追踪"""
        if session_id in self.session_metrics:
            self.session_metrics[session_id].end_time = datetime.now()
            self._save_data()
    
    def analyze_conversation_quality(self, session_id: str) -> Optional[ReflectionInsight]:
        """分析对话质量"""
        if session_id not in self.session_metrics:
            return None
        
        metrics = self.session_metrics[session_id]
        
        # 计算质量分数
        score = self._calculate_quality_score(metrics)
        
        # 生成洞察
        severity = self._get_severity(score)
        
        if severity == Severity.LOW:
            return None  # 质量良好，无需反思
        
        title, description, recommendations = self._generate_quality_insight(metrics, score)
        
        insight = ReflectionInsight(
            id=f"quality_{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=ReflectionType.CONVERSATION_QUALITY,
            title=title,
            description=description,
            severity=severity,
            score=score,
            timestamp=datetime.now(),
            context={"session_id": session_id, "metrics": metrics.to_dict()},
            recommendations=recommendations
        )
        
        self.insights.append(insight)
        self._save_data()
        
        logger.info(f"生成对话质量洞察: {title}")
        return insight
    
    def _calculate_quality_score(self, metrics: ConversationMetrics) -> float:
        """计算质量分数"""
        score = 1.0
        
        # 工具成功率
        if metrics.tool_calls > 0:
            success_rate = metrics.successful_tools / metrics.tool_calls
            score *= success_rate
        
        # 错误率
        if metrics.message_count > 0:
            error_rate = metrics.error_count / metrics.message_count
            score *= (1 - error_rate * 0.5)  # 错误影响较大
        
        # 澄清请求（过多说明理解不足）
        if metrics.message_count > 0:
            clarification_rate = metrics.clarification_requests / metrics.message_count
            if clarification_rate > 0.3:
                score *= 0.8
        
        return max(0.0, min(1.0, score))
    
    def _get_severity(self, score: float) -> Severity:
        """获取严重程度"""
        if score >= self.QUALITY_THRESHOLDS["good"]:
            return Severity.LOW
        elif score >= self.QUALITY_THRESHOLDS["acceptable"]:
            return Severity.MEDIUM
        elif score >= self.QUALITY_THRESHOLDS["poor"]:
            return Severity.HIGH
        else:
            return Severity.CRITICAL
    
    def _generate_quality_insight(
        self, 
        metrics: ConversationMetrics,
        score: float
    ) -> Tuple[str, str, List[str]]:
        """生成质量洞察"""
        issues = []
        recommendations = []
        
        # 分析工具使用
        if metrics.tool_calls > 0:
            success_rate = metrics.successful_tools / metrics.tool_calls
            if success_rate < 0.7:
                issues.append(f"工具成功率较低 ({success_rate:.1%})")
                recommendations.append("检查工具参数验证和错误处理")
        
        # 分析错误
        if metrics.error_count > 0:
            error_rate = metrics.error_count / max(metrics.message_count, 1)
            if error_rate > 0.1:
                issues.append(f"错误率较高 ({error_rate:.1%})")
                recommendations.append("增强错误处理和恢复机制")
        
        # 分析澄清请求
        if metrics.clarification_requests > 2:
            issues.append(f"需要多次澄清 ({metrics.clarification_requests} 次)")
            recommendations.append("改进意图理解能力")
        
        # 生成标题和描述
        if score < 0.3:
            title = "对话质量严重不足"
            description = f"会话 {metrics.session_id} 质量分数: {score:.2f}。问题: {', '.join(issues)}"
        elif score < 0.5:
            title = "对话质量需要改进"
            description = f"会话 {metrics.session_id} 质量分数: {score:.2f}。问题: {', '.join(issues)}"
        else:
            title = "对话质量有待提升"
            description = f"会话 {metrics.session_id} 质量分数: {score:.2f}。建议优化: {', '.join(issues)}"
        
        return title, description, recommendations
    
    def analyze_tool_usage_patterns(self) -> Optional[ReflectionInsight]:
        """分析工具使用模式"""
        if not self.session_metrics:
            return None
        
        # 统计工具使用情况
        total_calls = sum(m.tool_calls for m in self.session_metrics.values())
        total_success = sum(m.successful_tools for m in self.session_metrics.values())
        
        if total_calls == 0:
            return None
        
        success_rate = total_success / total_calls
        
        if success_rate >= 0.9:
            return None  # 工具使用良好
        
        severity = self._get_severity(success_rate)
        
        insight = ReflectionInsight(
            id=f"tool_usage_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=ReflectionType.TOOL_USAGE,
            title="工具使用效率分析",
            description=f"工具调用成功率: {success_rate:.1%} ({total_success}/{total_calls})",
            severity=severity,
            score=success_rate,
            timestamp=datetime.now(),
            context={
                "total_calls": total_calls,
                "success_rate": success_rate
            },
            recommendations=[
                "检查失败工具的参数验证",
                "增加工具使用的容错机制",
                "优化工具选择策略"
            ]
        )
        
        self.insights.append(insight)
        self._save_data()
        
        return insight
    
    def identify_knowledge_gaps(self) -> List[ReflectionInsight]:
        """识别知识缺口"""
        gaps = []
        
        # 分析错误模式
        error_sessions = [
            (sid, m) for sid, m in self.session_metrics.items()
            if m.error_count > 0
        ]
        
        if len(error_sessions) > 3:
            insight = ReflectionInsight(
                id=f"knowledge_gap_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                type=ReflectionType.KNOWLEDGE_GAP,
                title="知识缺口识别",
                description=f"发现 {len(error_sessions)} 个会话存在错误，可能存在知识缺口",
                severity=Severity.MEDIUM,
                score=0.5,
                timestamp=datetime.now(),
                context={
                    "error_sessions": len(error_sessions),
                    "total_sessions": len(self.session_metrics)
                },
                recommendations=[
                    "分析错误会话的共同模式",
                    "补充相关知识库内容",
                    "增强错误恢复能力"
                ]
            )
            
            gaps.append(insight)
            self.insights.append(insight)
        
        self._save_data()
        return gaps
    
    def generate_improvement_report(self) -> Dict:
        """生成改进报告"""
        # 按类型分组洞察
        by_type = defaultdict(list)
        for insight in self.insights:
            if not insight.resolved:
                by_type[insight.type.value].append(insight)
        
        # 计算总体分数
        total_score = 0.0
        count = 0
        for insight in self.insights[-100:]:  # 最近 100 个
            total_score += insight.score
            count += 1
        
        avg_score = total_score / count if count > 0 else 1.0
        
        # 统计严重程度
        severity_count = defaultdict(int)
        for insight in self.insights:
            if not insight.resolved:
                severity_count[insight.severity.value] += 1
        
        return {
            "generated_at": datetime.now().isoformat(),
            "overall_score": avg_score,
            "total_insights": len(self.insights),
            "unresolved_insights": sum(1 for i in self.insights if not i.resolved),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "by_severity": dict(severity_count),
            "recommendations": self._get_top_recommendations()
        }
    
    def _get_top_recommendations(self, limit: int = 10) -> List[Dict]:
        """获取最重要的建议"""
        recommendations = []
        
        for insight in self.insights:
            if not insight.resolved:
                for rec in insight.recommendations:
                    recommendations.append({
                        "insight_id": insight.id,
                        "insight_title": insight.title,
                        "severity": insight.severity.value,
                        "recommendation": rec,
                        "score": insight.score
                    })
        
        # 按严重程度和分数排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: (severity_order.get(x["severity"], 4), x["score"]))
        
        return recommendations[:limit]
    
    def resolve_insight(self, insight_id: str):
        """标记洞察为已解决"""
        for insight in self.insights:
            if insight.id == insight_id:
                insight.resolved = True
                insight.resolved_at = datetime.now()
                self._save_data()
                logger.info(f"已解决洞察: {insight_id}")
                return True
        return False
    
    def get_recent_insights(self, limit: int = 20) -> List[ReflectionInsight]:
        """获取最近的洞察"""
        return sorted(self.insights, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_insights_by_type(self, insight_type: ReflectionType) -> List[ReflectionInsight]:
        """按类型获取洞察"""
        return [i for i in self.insights if i.type == insight_type]
    
    def get_insights_by_severity(self, severity: Severity) -> List[ReflectionInsight]:
        """按严重程度获取洞察"""
        return [i for i in self.insights if i.severity == severity and not i.resolved]
    
    def cleanup_old_insights(self, days: int = 30):
        """清理旧洞察"""
        cutoff = datetime.now() - timedelta(days=days)
        
        self.insights = [
            i for i in self.insights
            if i.timestamp > cutoff or not i.resolved
        ]
        
        self._save_data()
        logger.info(f"已清理 {days} 天前的已解决洞察")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        resolved = sum(1 for i in self.insights if i.resolved)
        
        type_distribution = defaultdict(int)
        for insight in self.insights:
            type_distribution[insight.type.value] += 1
        
        return {
            "total_insights": len(self.insights),
            "resolved_insights": resolved,
            "unresolved_insights": len(self.insights) - resolved,
            "total_sessions_tracked": len(self.session_metrics),
            "type_distribution": dict(type_distribution)
        }
