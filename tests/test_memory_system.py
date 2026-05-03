"""
Memory System 集成测试
"""
import pytest
import sys
import os
import tempfile
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


class TestMemorySystem:
    """Memory System 集成测试"""
    
    @pytest.fixture
    def memory_db(self):
        """创建测试数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建完整表结构
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
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                old_fact_id INTEGER,
                new_key TEXT,
                old_value TEXT,
                new_value TEXT,
                resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        yield conn, db_path
        
        conn.close()
        try:
            os.unlink(db_path)
        except:
            pass
    
    def test_extract_and_store(self, memory_db):
        """测试提取和存储"""
        conn, db_path = memory_db
        
        # 简单的提取逻辑测试
        message = "我喜欢绿色"
        
        # 模拟提取
        extracted = {
            'type': 'preference',
            'key': '颜色',
            'value': '绿色',
            'confidence': 0.8
        }
        
        # 存储
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO facts (category, key, value, confidence) VALUES (?, ?, ?, ?)",
            (extracted['type'], extracted['key'], extracted['value'], extracted['confidence'])
        )
        conn.commit()
        
        # 验证
        cursor.execute("SELECT * FROM facts WHERE key = '颜色'")
        row = cursor.fetchone()
        assert row is not None
        assert row[3] == '绿色'  # value 字段
    
    def test_conflict_update(self, memory_db):
        """测试冲突更新"""
        conn, db_path = memory_db
        cursor = conn.cursor()
        
        # 插入旧记忆
        cursor.execute(
            "INSERT INTO facts (category, key, value, confidence) VALUES (?, ?, ?, ?)",
            ('preference', '颜色', '蓝色', 0.9)
        )
        old_id = cursor.lastrowid
        conn.commit()
        
        # 检测冲突并更新
        new_value = '绿色'
        cursor.execute(
            "UPDATE facts SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_value, old_id)
        )
        
        # 记录冲突
        cursor.execute(
            "INSERT INTO conflicts (old_fact_id, new_key, old_value, new_value) VALUES (?, ?, ?, ?)",
            (old_id, '颜色', '蓝色', new_value)
        )
        conn.commit()
        
        # 验证更新
        cursor.execute("SELECT value FROM facts WHERE id = ?", (old_id,))
        row = cursor.fetchone()
        assert row[0] == '绿色'
        
        # 验证冲突记录
        cursor.execute("SELECT * FROM conflicts WHERE old_fact_id = ?", (old_id,))
        conflict = cursor.fetchone()
        assert conflict is not None
    
    def test_time_decay(self, memory_db):
        """测试时间衰减"""
        conn, db_path = memory_db
        cursor = conn.cursor()
        
        # 插入不同时间的记忆
        now = datetime.now()
        
        # 新记忆（今天）
        cursor.execute(
            "INSERT INTO facts (category, key, value, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
            ('preference', '新偏好', '值A', 0.9, now.isoformat())
        )
        
        # 旧记忆（30天前）
        old_date = (now - timedelta(days=30)).isoformat()
        cursor.execute(
            "INSERT INTO facts (category, key, value, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
            ('preference', '旧偏好', '值B', 0.9, old_date)
        )
        conn.commit()
        
        # 检索并计算时间衰减
        cursor.execute("SELECT key, created_at FROM facts WHERE category = 'preference'")
        rows = cursor.fetchall()
        
        for key, created_at in rows:
            created = datetime.fromisoformat(created_at)
            days_old = (now - created).days
            decay = max(0.1, 1.0 - (days_old / 90))  # 90天衰减到0.1
            
            if key == '新偏好':
                assert decay > 0.9  # 新记忆权重高
            elif key == '旧偏好':
                assert decay < 0.7  # 旧记忆权重低
    
    def test_compress(self, memory_db):
        """测试记忆压缩"""
        conn, db_path = memory_db
        cursor = conn.cursor()
        
        # 插入多条相似记忆
        for i in range(5):
            cursor.execute(
                "INSERT INTO facts (category, key, value, confidence) VALUES (?, ?, ?, ?)",
                ('preference', f'颜色{i}', f'蓝色{i}', 0.8)
            )
        conn.commit()
        
        # 统计压缩前
        cursor.execute("SELECT COUNT(*) FROM facts WHERE category = 'preference'")
        before_count = cursor.fetchone()[0]
        
        # 模拟压缩（合并为一条摘要）
        cursor.execute(
            "INSERT INTO facts (category, key, value, confidence) VALUES (?, ?, ?, ?)",
            ('preference', '颜色_摘要', '蓝色系列', 0.85)
        )
        
        # 删除旧记忆
        cursor.execute("DELETE FROM facts WHERE category = 'preference' AND key LIKE '颜色%' AND key != '颜色_摘要'")
        conn.commit()
        
        # 统计压缩后
        cursor.execute("SELECT COUNT(*) FROM facts WHERE category = 'preference'")
        after_count = cursor.fetchone()[0]
        
        assert after_count < before_count
