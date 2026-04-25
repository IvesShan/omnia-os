#!/usr/bin/env python3
"""
更新脚本：将所有 MemoryManager 导入替换为 MemoryManagerV2
"""

import re
from pathlib import Path


def update_file(file_path: Path) -> bool:
    """
    更新单个文件的导入语句
    
    Returns:
        是否进行了修改
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 替换导入语句
    content = re.sub(
        r'from \.\.memory\.memory_manager import MemoryManager',
        'from ..memory.memory_manager_v2 import MemoryManagerV2',
        content
    )
    
    content = re.sub(
        r'from core\.memory\.memory_manager import MemoryManager',
        'from core.memory.memory_manager_v2 import MemoryManagerV2',
        content
    )
    
    # 替换类名使用
    content = re.sub(
        r'\bMemoryManager\(',
        'MemoryManagerV2(',
        content
    )
    
    content = re.sub(
        r'memory_manager:\s*Optional\[MemoryManager\]',
        'memory_manager: Optional[MemoryManagerV2]',
        content
    )
    
    content = re.sub(
        r'memory_manager:\s*MemoryManager\s*=',
        'memory_manager: MemoryManagerV2 =',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("更新 MemoryManager 导入")
    print("=" * 60)
    
    src_path = Path(__file__).parent.parent / "src"
    
    # 查找所有 Python 文件
    python_files = list(src_path.rglob("*.py"))
    
    updated_files = []
    
    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue
        
        if update_file(file_path):
            updated_files.append(file_path)
            print(f"✓ 更新: {file_path.relative_to(src_path)}")
    
    print("\n" + "=" * 60)
    print(f"更新完成！共更新 {len(updated_files)} 个文件")
    print("=" * 60)
    
    if updated_files:
        print("\n更新的文件:")
        for file_path in updated_files:
            print(f"  - {file_path.relative_to(src_path)}")


if __name__ == "__main__":
    main()
