#!/usr/bin/env python3
"""
批量生成对话记录的向量嵌入
P2 任务：提高向量覆盖率从 14.7% 到 100%
"""

import sys
import time
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.memory_palace import MemoryPalace


def backfill_vectors(batch_size: int = 100, limit: int = None, dry_run: bool = False):
    """
    批量生成对话记录的向量
    
    Args:
        batch_size: 每批处理的记录数
        limit: 最多处理多少条（None = 全部）
        dry_run: 只统计不执行
    """
    mp = MemoryPalace()
    conn = mp._connect()
    
    # 统计当前状态
    total = conn.execute('SELECT COUNT(*) FROM conversation_logs').fetchone()[0]
    with_vector = conn.execute('SELECT COUNT(*) FROM conversation_logs WHERE embedding IS NOT NULL').fetchone()[0]
    without_vector = total - with_vector
    
    print("=" * 60)
    print("📊 对话记录向量生成")
    print("=" * 60)
    print(f"总记录数: {total}")
    print(f"已有向量: {with_vector} ({with_vector/total*100:.1f}%)")
    print(f"待处理: {without_vector} ({without_vector/total*100:.1f}%)")
    print(f"批次大小: {batch_size}")
    print(f"处理限制: {limit if limit else '无限制'}")
    print(f"模式: {'模拟运行' if dry_run else '实际执行'}")
    print("=" * 60)
    
    if dry_run:
        print("\n✅ 模拟运行完成，未实际生成向量")
        return
    
    # 分批处理
    processed = 0
    failed = 0
    start_time = time.time()
    
    while True:
        # 检查是否达到限制
        if limit and processed >= limit:
            print(f"\n⏸️ 已达到处理限制: {limit}")
            break
        
        # 获取一批无向量记录
        batch_limit = min(batch_size, limit - processed) if limit else batch_size
        rows = conn.execute('''
            SELECT id, content 
            FROM conversation_logs 
            WHERE embedding IS NULL 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (batch_limit,)).fetchall()
        
        if not rows:
            print("\n✅ 所有记录已处理完成！")
            break
        
        # 处理这一批
        batch_start = time.time()
        batch_processed = 0
        batch_failed = 0
        
        for row in rows:
            try:
                # 生成向量
                embedding = mp.vector_service.encode(row['content'])
                
                # 更新数据库
                conn.execute(
                    'UPDATE conversation_logs SET embedding = ? WHERE id = ?',
                    (embedding.tobytes(), row['id'])
                )
                
                batch_processed += 1
            except Exception as e:
                print(f"  ⚠️ ID {row['id']} 失败: {e}")
                batch_failed += 1
                failed += 1
        
        # 提交这一批
        conn.commit()
        processed += batch_processed
        
        # 显示进度
        batch_time = time.time() - batch_start
        total_time = time.time() - start_time
        remaining = without_vector - processed
        rate = processed / total_time if total_time > 0 else 0
        eta = remaining / rate if rate > 0 else 0
        
        print(f"✓ 批次完成: {batch_processed} 条 | "
              f"总计: {processed}/{without_vector} ({processed/without_vector*100:.1f}%) | "
              f"速度: {rate:.1f} 条/秒 | "
              f"预计剩余: {eta/60:.1f} 分钟")
        
        # 短暂休息，避免过载
        time.sleep(0.1)
    
    # 最终统计
    total_time = time.time() - start_time
    final_with_vector = conn.execute('SELECT COUNT(*) FROM conversation_logs WHERE embedding IS NOT NULL').fetchone()[0]
    
    print("\n" + "=" * 60)
    print("📈 处理完成统计")
    print("=" * 60)
    print(f"处理成功: {processed} 条")
    print(f"处理失败: {failed} 条")
    print(f"总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    print(f"平均速度: {processed/total_time:.1f} 条/秒")
    print(f"\n最终向量覆盖率: {final_with_vector}/{total} ({final_with_vector/total*100:.1f}%)")
    print("=" * 60)
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='批量生成对话记录的向量嵌入')
    parser.add_argument('--batch-size', type=int, default=100, help='每批处理的记录数 (默认: 100)')
    parser.add_argument('--limit', type=int, default=None, help='最多处理多少条 (默认: 全部)')
    parser.add_argument('--dry-run', action='store_true', help='只统计不执行')
    
    args = parser.parse_args()
    
    backfill_vectors(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
