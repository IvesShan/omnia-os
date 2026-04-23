#!/usr/bin/env python3
"""
持续优化与功能扩展测试脚本
测试所有新实现的模块
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from monitoring.conversation_monitor import ConversationMonitor, get_monitor
from monitoring.performance_monitor import PerformanceMonitor, get_performance_monitor
from monitoring.anomaly_detector import AnomalyDetector, AnomalyType, get_anomaly_detector
from core.context_extractor import ContextExtractor, get_context_extractor
from core.topic_recognizer import TopicRecognizer, get_topic_recognizer
from core.reminder_engine import ReminderEngine, ReminderType, get_reminder_engine


def test_conversation_monitor():
    """测试对话质量监控"""
    print("\n" + "="*60)
    print("📊 测试对话质量监控")
    print("="*60)
    
    monitor = get_monitor()
    
    # 模拟会话
    session_id = "test_session_001"
    monitor.start_session(session_id)
    
    # 记录对话轮次
    monitor.record_turn(session_id, response_time=150.5)
    monitor.record_turn(session_id, response_time=200.3)
    monitor.record_turn(session_id, response_time=180.7)
    
    # 记录上下文命中
    monitor.record_context_hit(session_id, hit=True)
    monitor.record_context_hit(session_id, hit=True)
    monitor.record_context_hit(session_id, hit=False)
    
    # 记录主题切换
    monitor.record_topic_shift(session_id, "技术", "业务")
    
    # 结束会话
    metrics = monitor.end_session(session_id)
    
    print(f"✅ 会话 ID: {metrics.session_id}")
    print(f"✅ 对话轮次: {metrics.turn_count}")
    print(f"✅ 持续时间: {metrics.duration_seconds:.2f}s")
    print(f"✅ 上下文命中率: {metrics.context_hit_rate:.2%}")
    print(f"✅ 主题切换: {metrics.topic_shifts} 次")
    print(f"✅ 平均响应时间: {metrics.avg_response_time:.2f}ms")
    
    # 获取统计
    stats = monitor.get_session_stats()
    print(f"\n📈 总会话数: {stats.total_sessions}")
    print(f"📈 平均轮次: {stats.avg_turn_count:.2f}")
    print(f"📈 平均命中率: {stats.avg_context_hit_rate:.2%}")
    
    return True


def test_performance_monitor():
    """测试性能监控"""
    print("\n" + "="*60)
    print("⚡ 测试性能监控")
    print("="*60)
    
    monitor = get_performance_monitor()
    
    # 记录性能指标
    monitor.record_response_time(150.5)
    monitor.record_response_time(200.3)
    monitor.record_response_time(180.7)
    monitor.record_response_time(5000.0)  # 慢响应
    
    monitor.record_db_query_time(25.3, "SELECT")
    monitor.record_db_query_time(150.0, "INSERT")  # 慢查询
    
    monitor.record_vector_search_time(45.2)
    monitor.record_vector_search_time(50.8)
    
    # 获取当前指标
    metrics = monitor.get_current_metrics()
    print(f"✅ 平均响应时间: {metrics.response_time_ms:.2f}ms")
    print(f"✅ 内存使用: {metrics.memory_usage_mb:.2f}MB")
    print(f"✅ CPU 使用: {metrics.cpu_usage_percent:.1f}%")
    print(f"✅ 平均 DB 查询: {metrics.db_query_time_ms:.2f}ms")
    print(f"✅ 平均向量搜索: {metrics.vector_search_time_ms:.2f}ms")
    
    # 获取统计
    stats = monitor.get_stats()
    print(f"\n📈 总请求数: {stats.total_requests}")
    print(f"📈 P95 响应时间: {stats.p95_response_time_ms:.2f}ms")
    
    # 获取慢查询
    slow_queries = monitor.get_slow_queries(limit=3)
    if slow_queries:
        print(f"\n🐢 慢查询 ({len(slow_queries)} 个):")
        for query in slow_queries:
            print(f"  - {query['query_type']}: {query['duration_ms']:.2f}ms")
    
    return True


def test_anomaly_detector():
    """测试异常检测"""
    print("\n" + "="*60)
    print("🚨 测试异常检测")
    print("="*60)
    
    detector = get_anomaly_detector()
    
    # 模拟健康检查
    metrics = {
        'avg_response_time': 6000,  # 超过阈值
        'error_rate': 0.15,  # 超过阈值
        'memory_usage_mb': 1200  # 超过阈值
    }
    
    anomalies = detector.run_health_check(metrics)
    
    print(f"✅ 检测到 {len(anomalies)} 个异常:")
    for anomaly in anomalies:
        print(f"  - [{anomaly.severity.upper()}] {anomaly.anomaly_type.value}: {anomaly.description}")
    
    # 获取统计
    stats = detector.get_anomaly_stats()
    print(f"\n📈 异常总数: {stats['total']}")
    print(f"📈 未解决: {stats['unresolved']}")
    
    return True


def test_context_extractor():
    """测试上下文提取"""
    print("\n" + "="*60)
    print("🔍 测试上下文提取")
    print("="*60)
    
    extractor = get_context_extractor()
    
    # 测试消息
    message = "我决定使用 Python 来实现 Omnia 的监控功能，下一步需要设计数据库架构"
    history = [
        {"role": "user", "content": "我们开始实现监控系统吧"},
        {"role": "assistant", "content": "好的，我建议使用 Python 和 SQLite"},
        {"role": "user", "content": message}
    ]
    
    # 提取完整上下文
    context = extractor.extract_full_context(message, history)
    
    print(f"✅ 主题: {context.topic}")
    print(f"✅ 摘要: {context.summary[:80]}...")
    print(f"✅ 关键决策: {context.key_decisions[:2]}")
    print(f"✅ 活动项目: {context.active_project}")
    print(f"✅ 下一步: {context.next_steps[:2]}")
    print(f"✅ 实体: {context.entities}")
    print(f"✅ 情感: {context.sentiment}")
    print(f"✅ 重要性: {context.importance}/5")
    
    return True


def test_topic_recognizer():
    """测试主题识别"""
    print("\n" + "="*60)
    print("🎯 测试主题识别")
    print("="*60)
    
    recognizer = get_topic_recognizer()
    
    # 测试主题识别
    messages = [
        "我们开始开发 Omnia 的监控功能",
        "需要实现性能监控和异常检测",
        "对了，明天的培训课程准备好了吗？",  # 主题切换
        "课程内容已经完成，接下来要准备教材"
    ]
    
    print("✅ 主题识别:")
    for i, msg in enumerate(messages):
        topic, confidence = recognizer.recognize_topic(msg)
        print(f"  {i+1}. {msg[:30]}... -> {topic} ({confidence:.2f})")
    
    # 测试主题切换检测
    history = [{"role": "user", "content": msg} for msg in messages]
    shift = recognizer.detect_topic_shift(history)
    
    if shift:
        print(f"\n✅ 检测到主题切换:")
        print(f"  {shift.from_topic} -> {shift.to_topic}")
        print(f"  类型: {shift.shift_type}")
    
    # 获取热门主题
    hot_topics = recognizer.get_hot_topics(limit=5)
    if hot_topics:
        print(f"\n📈 热门主题:")
        for topic in hot_topics:
            print(f"  - {topic['topic']}: {topic['count']} 次")
    
    return True


def test_reminder_engine():
    """测试智能提醒"""
    print("\n" + "="*60)
    print("⏰ 测试智能提醒")
    print("="*60)
    
    engine = get_reminder_engine()
    
    # 测试上下文分析
    context = {
        'message': '明天需要完成监控系统的测试，下周再优化性能',
        'session_id': 'test_session_001',
        'next_steps': ['完成测试', '优化性能']
    }
    
    reminders = engine.analyze_context(context)
    print(f"✅ 从上下文提取到 {len(reminders)} 个提醒:")
    for reminder in reminders:
        print(f"  - [{reminder.reminder_type.value}] {reminder.content[:50]}...")
        print(f"    触发时间: {reminder.trigger_time.strftime('%Y-%m-%d %H:%M')}")
    
    # 创建自定义提醒
    custom_reminder = engine.create_reminder(
        content="测试提醒：检查监控系统运行状态",
        trigger_time=datetime.now() + timedelta(hours=1),  # 1小时后
        reminder_type=ReminderType.CONTEXT_BASED,
        priority=3
    )
    print(f"\n✅ 创建自定义提醒: {custom_reminder.reminder_id}")
    
    # 获取待处理提醒
    pending = engine.get_pending_reminders(limit=5)
    print(f"\n📋 待处理提醒: {len(pending)} 个")
    
    # 获取统计
    stats = engine.get_reminder_stats()
    print(f"\n📈 提醒统计:")
    print(f"  总数: {stats['total']}")
    print(f"  待处理: {stats['pending']}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 Omnia 持续优化与功能扩展测试")
    print("="*60)
    
    tests = [
        ("对话质量监控", test_conversation_monitor),
        ("性能监控", test_performance_monitor),
        ("异常检测", test_anomaly_detector),
        ("上下文提取", test_context_extractor),
        ("主题识别", test_topic_recognizer),
        ("智能提醒", test_reminder_engine)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}")
        if error:
            print(f"  错误: {error}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！持续优化与功能扩展已完成。")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
