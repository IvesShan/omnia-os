#!/usr/bin/env python3
"""
OpenMythos Performance Benchmarks

性能基准测试
"""

import sys
import time
from pathlib import Path
from typing import Callable
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.openmythos import (
    ACTPlanner,
    RecurrentReasoning,
    MLACompression,
    IntegrationBridge
)


class PerformanceBenchmark:
    """性能基准测试套件"""
    
    def __init__(self):
        self.results = {}
    
    def benchmark_act_planner(self, iterations: int = 1000):
        """测试 ACT Planner 性能"""
        print(f"\n=== ACT Planner 性能测试 ({iterations} 次) ===")
        
        planner = ACTPlanner()
        
        test_queries = [
            "你好",
            "解释一下机器学习",
            "设计一个分布式系统架构",
            "帮我分析一下这个代码的性能问题",
            "什么是量子计算"
        ]
        
        start = time.time()
        for _ in range(iterations):
            for query in test_queries:
                planner.analyze(query)
        elapsed = time.time() - start
        
        avg_time = elapsed / (iterations * len(test_queries)) * 1000
        qps = (iterations * len(test_queries)) / elapsed
        
        print(f"  总耗时: {elapsed:.3f}s")
        print(f"  平均耗时: {avg_time:.3f}ms")
        print(f"  QPS: {qps:.1f}")
        
        self.results['act_planner'] = {
            'iterations': iterations * len(test_queries),
            'total_time': elapsed,
            'avg_time_ms': avg_time,
            'qps': qps
        }
    
    def benchmark_mla_compression(self, batch_sizes=[10, 100, 1000]):
        """测试 MLA 压缩性能"""
        print(f"\n=== MLA Compression 性能测试 ===")
        
        compression = MLACompression()
        
        for batch_size in batch_sizes:
            vectors = np.random.randn(batch_size, 768)
            
            # 压缩
            start = time.time()
            compressed = compression.compress(vectors)
            compress_time = time.time() - start
            
            # 解压
            start = time.time()
            decompressed = compression.decompress(compressed)
            decompress_time = time.time() - start
            
            print(f"\n  批次大小: {batch_size}")
            print(f"    压缩耗时: {compress_time*1000:.3f}ms")
            print(f"    解压耗时: {decompress_time*1000:.3f}ms")
            print(f"    压缩比: {vectors.nbytes / compressed.nbytes:.1f}x")
        
        self.results['mla_compression'] = {
            'batch_sizes': batch_sizes,
            'last_compress_time_ms': compress_time * 1000,
            'last_decompress_time_ms': decompress_time * 1000
        }
    
    def benchmark_recurrent_engine(self, iterations_list=[1, 3, 5]):
        """测试循环推理引擎性能"""
        print(f"\n=== Recurrent Engine 性能测试 ===")
        
        def mock_model_call(prompt, context):
            time.sleep(0.01)  # 模拟网络延迟
            return "思考：分析完成。\n置信度：0.88"
        
        for max_iterations in iterations_list:
            engine = RecurrentReasoning(
                model_call=mock_model_call,
                max_iterations=max_iterations,
                confidence_threshold=0.99  # 强制达到最大迭代
            )
            
            start = time.time()
            result = engine.reason("测试查询")
            elapsed = time.time() - start
            
            print(f"\n  最大迭代: {max_iterations}")
            print(f"    实际迭代: {result.total_iterations}")
            print(f"    总耗时: {elapsed*1000:.1f}ms")
            print(f"    平均每轮: {elapsed/max_iterations*1000:.1f}ms")
        
        self.results['recurrent_engine'] = {
            'iterations_tested': iterations_list,
            'last_total_time_ms': elapsed * 1000
        }
    
    def benchmark_full_pipeline(self, queries_count: int = 10):
        """测试完整流程性能"""
        print(f"\n=== 完整流程性能测试 ({queries_count} 查询) ===")
        
        def mock_model_call(prompt, context):
            time.sleep(0.01)  # 模拟延迟
            return "思考：完成。\n置信度：0.9"
        
        bridge = IntegrationBridge(
            model_call=mock_model_call,
            config={'max_iterations': 3}
        )
        
        queries = [
            "你好",
            "解释机器学习",
            "设计系统架构"
        ] * (queries_count // 3 + 1)
        
        start = time.time()
        for query in queries[:queries_count]:
            bridge.process(query)
        elapsed = time.time() - start
        
        avg_time = elapsed / queries_count * 1000
        
        print(f"  总耗时: {elapsed:.3f}s")
        print(f"  平均耗时: {avg_time:.1f}ms")
        print(f"  QPS: {queries_count / elapsed:.1f}")
        
        self.results['full_pipeline'] = {
            'queries_count': queries_count,
            'total_time': elapsed,
            'avg_time_ms': avg_time,
            'qps': queries_count / elapsed
        }
    
    def print_summary(self):
        """打印总结"""
        print("\n" + "=" * 60)
        print("性能测试总结")
        print("=" * 60)
        
        if 'act_planner' in self.results:
            r = self.results['act_planner']
            print(f"\nACT Planner:")
            print(f"  QPS: {r['qps']:.1f}")
            print(f"  平均耗时: {r['avg_time_ms']:.3f}ms")
        
        if 'mla_compression' in self.results:
            r = self.results['mla_compression']
            print(f"\nMLA Compression:")
            print(f"  压缩耗时: {r['last_compress_time_ms']:.3f}ms")
            print(f"  解压耗时: {r['last_decompress_time_ms']:.3f}ms")
        
        if 'recurrent_engine' in self.results:
            r = self.results['recurrent_engine']
            print(f"\nRecurrent Engine:")
            print(f"  总耗时: {r['last_total_time_ms']:.1f}ms")
        
        if 'full_pipeline' in self.results:
            r = self.results['full_pipeline']
            print(f"\n完整流程:")
            print(f"  QPS: {r['qps']:.1f}")
            print(f"  平均耗时: {r['avg_time_ms']:.1f}ms")
        
        print("\n" + "=" * 60)


def main():
    print("=" * 60)
    print("OpenMythos Performance Benchmarks")
    print("=" * 60)
    
    benchmark = PerformanceBenchmark()
    
    # 运行所有测试
    benchmark.benchmark_act_planner(iterations=100)
    benchmark.benchmark_mla_compression(batch_sizes=[10, 100, 500])
    benchmark.benchmark_recurrent_engine(iterations_list=[1, 3, 5])
    benchmark.benchmark_full_pipeline(queries_count=10)
    
    # 打印总结
    benchmark.print_summary()


if __name__ == "__main__":
    main()
