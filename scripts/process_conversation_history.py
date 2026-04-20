#!/usr/bin/env python3
"""处理历史对话，构建神经图谱

用法:
    python3 scripts/process_conversation_history.py [--batch-size 100] [--limit 1000] [--use-llm]
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.neural_graph.conversation_processor import process_conversation_history
from core.neural_graph import NeuralGraph
from core.config import MEMORY_PALACE_DB


def main():
    parser = argparse.ArgumentParser(description="处理历史对话，构建神经图谱")
    parser.add_argument("--batch-size", type=int, default=100, help="每批处理数量")
    parser.add_argument("--limit", type=int, default=None, help="限制处理数量（用于测试）")
    parser.add_argument("--use-llm", action="store_true", help="使用 LLM 补充提取")
    parser.add_argument("--stats", action="store_true", help="只显示统计信息")
    
    args = parser.parse_args()
    
    # 显示统计
    graph = NeuralGraph(str(MEMORY_PALACE_DB))
    stats = graph.get_stats()
    
    print("=" * 60)
    print("📊 当前神经图谱统计")
    print("=" * 60)
    print(f"节点数: {stats['nodes']}")
    print(f"边数: {stats['edges']}")
    
    if stats.get('nodes_by_type'):
        print("\n节点类型分布:")
        for t, c in stats['nodes_by_type'].items():
            print(f"  {t}: {c}")
    
    if stats.get('edges_by_relation'):
        print("\n关系类型分布:")
        for r, c in stats['edges_by_relation'].items():
            print(f"  {r}: {c}")
    
    if args.stats:
        return
    
    print("\n" + "=" * 60)
    print("🔄 开始处理历史对话...")
    print("=" * 60)
    
    if args.limit:
        print(f"⚠️  限制处理: {args.limit} 条")
    
    result = process_conversation_history(
        batch_size=args.batch_size,
        use_llm=args.use_llm,
        limit=args.limit,
    )
    
    print("\n" + "=" * 60)
    print("✅ 处理完成！")
    print("=" * 60)
    
    # 更新统计
    stats = graph.get_stats()
    print(f"节点数: {stats['nodes']}")
    print(f"边数: {stats['edges']}")
    
    if stats.get('nodes_by_type'):
        print("\n节点类型分布:")
        for t, c in stats['nodes_by_type'].items():
            print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
