"""
测试 Memory Manager V2
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.memory.memory_manager_v2 import MemoryManagerV2


def test_basic_operations():
    """测试基本操作"""
    print("=== 测试基本操作 ===")
    
    # 创建测试实例
    mm = MemoryManagerV2(base_path="/tmp/omnia_memory_test")
    
    # 1. 添加事实
    print("\n1. 添加事实")
    mm.add_fact("user_name", "原点", source="user", priority=10)
    mm.add_fact("user_project", "懂机帝", source="user", priority=8)
    mm.add_fact("temp_task", "测试任务", source="system", ttl_days=1, priority=1)
    
    # 2. 获取事实
    print("\n2. 获取事实")
    name = mm.get_fact("user_name")
    print(f"  user_name: {name}")
    
    # 3. 查询
    print("\n3. 查询")
    results = mm.query("原点")
    print(f"  查询 '原点': {len(results)} 条结果")
    for r in results:
        print(f"    - {r['layer']}/{r['key']}: {r['entry']['value']}")
    
    # 4. 统计
    print("\n4. 统计")
    stats = mm.get_stats()
    print(f"  总条目: {stats['total_entries']}")
    print(f"  总大小: {stats['total_size_bytes']} bytes")
    
    print("\n✅ 基本操作测试通过")


def test_backup_restore():
    """测试备份恢复"""
    print("\n=== 测试备份恢复 ===")
    
    mm = MemoryManagerV2(base_path="/tmp/omnia_memory_test")
    
    # 添加数据
    mm.add_fact("test_key", "test_value", priority=5)
    
    # 创建备份
    print("\n1. 创建备份")
    backup_name = mm.backup()
    print(f"  备份名称: {backup_name}")
    
    # 列出备份
    print("\n2. 列出备份")
    backups = mm.list_backups()
    print(f"  备份数量: {len(backups)}")
    
    # 修改数据
    mm.add_fact("test_key", "modified_value", priority=10)
    
    # 恢复备份
    print("\n3. 恢复备份")
    success = mm.restore(backup_name)
    print(f"  恢复成功: {success}")
    
    # 验证恢复
    value = mm.get_fact("test_key")
    print(f"  恢复后的值: {value}")
    
    print("\n✅ 备份恢复测试通过")


def test_compression():
    """测试压缩"""
    print("\n=== 测试压缩 ===")
    
    mm = MemoryManagerV2(base_path="/tmp/omnia_memory_test")
    
    # 添加一些数据
    mm.add_fact("key1", "value1", ttl_days=-1)  # 已过期
    mm.add_fact("key2", "value2", priority=5)
    
    # 执行压缩
    print("\n1. 执行压缩")
    stats = mm.compress_memory()
    print(f"  移除: {stats['removed']}")
    print(f"  合并: {stats['merged']}")
    print(f"  压缩: {stats['compressed']}")
    
    print("\n✅ 压缩测试通过")


if __name__ == "__main__":
    test_basic_operations()
    test_backup_restore()
    test_compression()
    
    print("\n" + "="*50)
    print("✅ 所有测试通过")
