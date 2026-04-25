#!/usr/bin/env python3
"""
迁移脚本：MemoryManager V1 -> V2
将现有的记忆数据迁移到新的 V2 格式
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.memory.memory_manager import MemoryManager
from core.memory.memory_manager_v2 import MemoryManagerV2


def migrate_memories(old_mm: MemoryManager, new_mm: MemoryManagerV2) -> dict:
    """
    迁移记忆数据
    
    Args:
        old_mm: 旧的 MemoryManager
        new_mm: 新的 MemoryManagerV2
    
    Returns:
        迁移统计信息
    """
    stats = {
        "total_memories": len(old_mm.memories),
        "migrated": 0,
        "skipped": 0,
        "errors": []
    }
    
    print(f"开始迁移 {stats['total_memories']} 条记忆...")
    
    for memory in old_mm.memories:
        try:
            # 从旧格式提取数据
            key = memory.id
            value = memory.content
            role = memory.role
            timestamp = memory.timestamp
            keywords = memory.keywords
            importance = memory.importance
            metadata = memory.metadata
            
            # 转换为 V2 格式
            # 将记忆内容作为事实存储
            success = new_mm.add_fact(
                key=f"memory_{key}",
                value={
                    "content": value,
                    "role": role,
                    "keywords": keywords,
                    "importance": importance,
                    "metadata": metadata
                },
                source="migration_v1",
                priority=int(importance * 10)  # 将 importance 转换为 priority
            )
            
            if success:
                stats["migrated"] += 1
            else:
                stats["skipped"] += 1
                
        except Exception as e:
            stats["errors"].append({
                "memory_id": memory.id,
                "error": str(e)
            })
    
    return stats


def main():
    """主函数"""
    print("=" * 60)
    print("Memory Manager V1 -> V2 迁移工具")
    print("=" * 60)
    
    # 创建旧的 MemoryManager
    old_mm = MemoryManager()
    print(f"\n✓ 旧 MemoryManager 已加载")
    print(f"  - 总记忆数: {len(old_mm.memories)}")
    
    # 创建新的 MemoryManagerV2
    memory_path = Path(__file__).parent.parent / "memory"
    new_mm = MemoryManagerV2(base_path=str(memory_path))
    print(f"\n✓ 新 MemoryManagerV2 已创建")
    print(f"  - 存储路径: {memory_path}")
    
    # 检查是否需要迁移
    if len(old_mm.memories) == 0:
        print("\n⚠ 没有需要迁移的记忆数据")
        return
    
    # 执行迁移
    print("\n开始迁移...")
    stats = migrate_memories(old_mm, new_mm)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print(f"总记忆数: {stats['total_memories']}")
    print(f"成功迁移: {stats['migrated']}")
    print(f"跳过: {stats['skipped']}")
    
    if stats['errors']:
        print(f"\n错误 ({len(stats['errors'])} 个):")
        for error in stats['errors'][:5]:  # 只显示前5个错误
            print(f"  - {error['memory_id']}: {error['error']}")
    
    # 显示新系统统计
    new_stats = new_mm.get_stats()
    print(f"\n新系统统计:")
    print(f"  - 总条目数: {new_stats['total_entries']}")
    print(f"  - 总大小: {new_stats['total_size_bytes']} bytes")
    
    # 创建备份
    print("\n创建备份...")
    backup_name = new_mm.create_backup()
    print(f"✓ 备份已创建: {backup_name}")


if __name__ == "__main__":
    main()
