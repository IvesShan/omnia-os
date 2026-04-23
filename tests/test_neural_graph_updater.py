#!/usr/bin/env python3
"""测试 Neural Graph Updater 的混合更新机制"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.neural_graph.graph import NeuralGraph, Entity
from core.neural_graph.extractor import EntityExtractor
from core.neural_graph.inferencer import RelationInferencer
from core.neural_graph.updater import NeuralGraphUpdater
from core.memory_palace.memory_palace_with_graph import MemoryPalace


def test_basic_flow():
    """测试基本流程：Hook 收集 + 心跳处理"""
    print("\n=== 测试基本流程 ===\n")
    
    # 1. 初始化组件
    print("1. 初始化组件...")
    graph = NeuralGraph()
    extractor = EntityExtractor()
    inferencer = RelationInferencer()
    updater = NeuralGraphUpdater(
        graph=graph,
        extractor=extractor,
        inferencer=inferencer,
    )
    memory = MemoryPalace(graph_updater=updater)
    memory.initialize()
    print("   ✓ 组件初始化完成")
    
    # 2. 测试 Hook: 写入记忆
    print("\n2. 写入记忆（触发 Hook）...")
    memory.remember_fact("user", "name", "原点")
    memory.remember_fact("user", "project", "喵修匠")
    memory.remember_fact("user", "project", "懂机帝")
    memory.relate("原点", "created", "Omnia", context="2026年4月")
    memory.relate("原点", "owns", "喵修匠")
    
    # 检查队列
    status = updater.get_status()
    print(f"   ✓ 写入完成，队列大小: {status['queue_size']}")
    
    # 3. 测试心跳: 强制处理
    print("\n3. 心跳触发处理...")
    result = updater.on_heartbeat(force=True)
    print(f"   ✓ 处理完成:")
    print(f"     - 处理记忆数: {result['processed']}")
    print(f"     - 提取实体数: {result['entities']}")
    print(f"     - 推断关系数: {result['relations']}")
    
    # 4. 查询图谱
    print("\n4. 查询神经图谱...")
    
    # 查询节点
    nodes = graph.query_nodes("原点")
    print(f"   节点 '原点': {len(nodes)} 个结果")
    for node in nodes:
        print(f"     - {node['entity_type']}: {node['entity_name']}")
    
    # 查询关系
    edges = graph.query_edges("原点")
    print(f"   关系 '原点': {len(edges)} 条")
    for edge in edges:
        print(f"     - {edge['source_name']} --[{edge['relation_type']}]--> {edge['target_name']}")
    
    # 5. 统计
    print("\n5. 最终统计...")
    stats = graph.get_stats()
    print(f"   总节点数: {stats['total_nodes']}")
    print(f"   总边数: {stats['total_edges']}")
    print(f"   Updater 统计: {updater.stats}")
    
    print("\n✅ 测试完成！")


def test_queue_threshold():
    """测试队列阈值触发"""
    print("\n=== 测试队列阈值触发 ===\n")
    
    # 初始化
    graph = NeuralGraph()
    extractor = EntityExtractor()
    updater = NeuralGraphUpdater(
        graph=graph,
        extractor=extractor,
    )
    
    print(f"队列阈值: {updater.QUEUE_THRESHOLD}")
    print(f"当前队列大小: {updater.get_pending_count()}")
    
    # 连续写入，超过阈值
    print("\n连续写入记忆...")
    for i in range(updater.QUEUE_THRESHOLD + 5):
        updater.on_memory_write(
            memory_id=f"test_{i}",
            text=f"测试记忆 {i}: 原点在开发 Omnia 项目",
            layer="facts",
        )
        print(f"  写入 {i+1}, 队列大小: {updater.get_pending_count()}")
    
    # 等待异步处理
    time.sleep(1)
    
    print(f"\n处理后队列大小: {updater.get_pending_count()}")
    print(f"Updater 统计: {updater.stats}")
    
    print("\n✅ 队列阈值测试完成！")


def test_idle_processing():
    """测试空闲时处理"""
    print("\n=== 测试空闲时处理 ===\n")
    
    # 初始化
    graph = NeuralGraph()
    extractor = EntityExtractor()
    updater = NeuralGraphUpdater(
        graph=graph,
        extractor=extractor,
    )
    updater.IDLE_THRESHOLD = 2  # 设置为 2 秒（测试用）
    
    print(f"空闲阈值: {updater.IDLE_THRESHOLD} 秒")
    
    # 写入一些记忆
    print("\n写入记忆...")
    for i in range(5):
        updater.on_memory_write(
            memory_id=f"idle_test_{i}",
            text=f"测试 {i}: 喵修匠是一个无人机维修平台",
            layer="facts",
        )
    
    print(f"队列大小: {updater.get_pending_count()}")
    
    # 立即触发心跳（不满足空闲条件）
    print("\n立即触发心跳（不满足空闲条件）...")
    result = updater.on_heartbeat()
    print(f"  结果: {result}")
    
    # 等待空闲
    print(f"\n等待 {updater.IDLE_THRESHOLD + 1} 秒...")
    time.sleep(updater.IDLE_THRESHOLD + 1)
    
    # 再次触发心跳（满足空闲条件）
    print("触发心跳（满足空闲条件）...")
    result = updater.on_heartbeat()
    print(f"  结果: {result}")
    print(f"  队列大小: {updater.get_pending_count()}")
    
    print("\n✅ 空闲处理测试完成！")


def test_integration_with_memory_palace():
    """测试与 MemoryPalace 的集成"""
    print("\n=== 测试与 MemoryPalace 集成 ===\n")
    
    # 初始化
    graph = NeuralGraph()
    extractor = EntityExtractor()
    inferencer = RelationInferencer()
    updater = NeuralGraphUpdater(
        graph=graph,
        extractor=extractor,
        inferencer=inferencer,
    )
    
    # 使用测试数据库
    test_db = Path("/tmp/test_memory_palace.db")
    if test_db.exists():
        test_db.unlink()
    
    memory = MemoryPalace(
        db_path=test_db,
        graph_updater=updater,
    )
    memory.initialize()
    
    print("✓ MemoryPalace 初始化完成（带 Graph Updater）")
    
    # 写入各种类型的记忆
    print("\n写入不同类型的记忆...")
    
    # Facts
    memory.remember_fact("project", "name", "Omnia OS")
    memory.remember_fact("project", "creator", "原点")
    memory.remember_fact("tech", "stack", "Python + Tauri")
    
    # Relations
    memory.relate("Omnia", "created_by", "原点", context="2026年")
    memory.relate("Omnia", "includes", "Memory Palace")
    memory.relate("Omnia", "includes", "Neural Graph")
    
    # Habits
    memory.observe_habit(
        pattern="daily_review",
        trigger="每天早上",
        action="检查待办事项",
        domain="productivity",
    )
    
    # Timeline
    from datetime import date
    memory.record_event(
        event_date=date.today(),
        event_type="milestone",
        title="Omnia 神经图谱系统上线",
        description="实现了混合更新机制",
        tags=["milestone", "neural-graph"],
    )
    
    print(f"✓ 写入完成，队列大小: {updater.get_pending_count()}")
    
    # 强制处理
    print("\n触发处理...")
    result = updater.on_heartbeat(force=True)
    print(f"✓ 处理完成: {result}")
    
    # 查询图谱
    print("\n查询神经图谱...")
    
    # 查询所有项目相关节点
    nodes = graph.query_nodes_by_type("PROJECT")
    print(f"项目节点: {len(nodes)} 个")
    for node in nodes:
        print(f"  - {node['entity_name']}")
    
    # 查询关系
    edges = graph.query_edges("Omnia")
    print(f"\nOmnia 的关系: {len(edges)} 条")
    for edge in edges:
        print(f"  - {edge['source_name']} --[{edge['relation_type']}]--> {edge['target_name']}")
    
    # 统计
    stats = graph.get_stats()
    print(f"\n图谱统计:")
    print(f"  节点数: {stats['total_nodes']}")
    print(f"  边数: {stats['total_edges']}")
    
    # 清理
    test_db.unlink()
    print("\n✅ 集成测试完成！")


if __name__ == "__main__":
    print("=" * 60)
    print("Neural Graph Updater 测试套件")
    print("=" * 60)
    
    try:
        test_basic_flow()
        test_queue_threshold()
        test_idle_processing()
        test_integration_with_memory_palace()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
