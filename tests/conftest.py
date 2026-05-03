"""
测试夹具 - 提供共享的测试资源
"""
import pytest
import sys
import os
import tempfile
import sqlite3

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


@pytest.fixture
def temp_memory_db():
    """临时内存数据库，测试后自动清理"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建表结构
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            frequency REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    yield conn, db_path
    
    # 清理
    conn.close()
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def sample_facts():
    """示例事实数据"""
    return [
        ('preference', '颜色', '蓝色', 0.9),
        ('preference', '编程语言', 'Python', 0.95),
        ('fact', '项目', 'Omnia', 1.0),
    ]


@pytest.fixture
def sample_relations():
    """示例关系数据"""
    return [
        ('用户', '创建了', 'Omnia项目'),
        ('Omnia', '包含', 'MemoryPalace'),
        ('MemoryPalace', '存储', '记忆'),
    ]
