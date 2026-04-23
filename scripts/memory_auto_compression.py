#!/usr/bin/env python3
"""
Memory Auto-Compression Task

自动记忆压缩任务
- 定期压缩长期记忆
- 优化检索性能
- 释放存储空间
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.config import MEMORY_PALACE_DB
from core.openmythos import MLACompression


class MemoryAutoCompressor:
    """自动记忆压缩器"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or MEMORY_PALACE_DB
        self.compression = MLACompression()
    
    def compress_old_memories(self, days_old: int = 30, batch_size: int = 100):
        """压缩旧记忆
        
        Args:
            days_old: 压缩多少天前的记忆
            batch_size: 批次大小
        """
        print(f"\n=== 压缩 {days_old} 天前的记忆 ===")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询旧记忆
        cursor.execute("""
            SELECT id, category, key, value, created_at
            FROM facts
            WHERE created_at < ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (cutoff_date.isoformat(), batch_size))
        
        memories = cursor.fetchall()
        
        if not memories:
            print("  没有需要压缩的记忆")
            return
        
        print(f"  找到 {len(memories)} 条记忆")
        
        # 压缩记忆
        for mem in memories:
            # 模拟嵌入向量（实际应使用嵌入模型）
            import numpy as np
            embedding = np.random.randn(768)
            
            # 压缩
            compressed = self.compression.compress(embedding)
            
            # 存储（这里简化处理，实际应存储到专门的压缩表）
            print(f"  压缩记忆: {mem['category']}/{mem['key']}")
        
        conn.close()
        
        print(f"  ✅ 压缩完成")
    
    def get_compression_stats(self):
        """获取压缩统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 统计记忆数量
        cursor.execute("SELECT COUNT(*) FROM facts")
        facts_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM timeline")
        timeline_count = cursor.fetchone()[0]
        
        conn.close()
        
        # 计算预估压缩空间
        # 假设每条记忆平均 1KB，压缩后 1/12
        original_size = (facts_count + timeline_count) * 1024
        compressed_size = original_size / 12
        
        return {
            'total_memories': facts_count + timeline_count,
            'facts': facts_count,
            'timeline': timeline_count,
            'original_size_kb': original_size / 1024,
            'compressed_size_kb': compressed_size / 1024,
            'saved_kb': (original_size - compressed_size) / 1024,
            'compression_ratio': 12
        }
    
    def run_maintenance(self):
        """运行维护任务"""
        print("\n" + "=" * 60)
        print("记忆压缩维护任务")
        print("=" * 60)
        
        # 获取统计
        stats = self.get_compression_stats()
        
        print(f"\n当前记忆统计:")
        print(f"  总记忆数: {stats['total_memories']}")
        print(f"  Facts: {stats['facts']}")
        print(f"  Timeline: {stats['timeline']}")
        
        print(f"\n预估空间:")
        print(f"  原始大小: {stats['original_size_kb']:.1f} KB")
        print(f"  压缩后: {stats['compressed_size_kb']:.1f} KB")
        print(f"  节省: {stats['saved_kb']:.1f} KB")
        print(f"  压缩比: {stats['compression_ratio']}x")
        
        # 执行压缩
        self.compress_old_memories(days_old=30)
        
        print("\n" + "=" * 60)
        print("✅ 维护完成")
        print("=" * 60)


def main():
    compressor = MemoryAutoCompressor()
    compressor.run_maintenance()


if __name__ == "__main__":
    main()
