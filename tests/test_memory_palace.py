"""
Memory Palace 单元测试
"""
import pytest
import sys
import os
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from core.memory_palace.memory_palace import MemoryPalace


class TestMemoryPalace:
    """Memory Palace 测试套件"""
    
    @pytest.fixture
    def memory_palace(self):
        """创建临时 MemoryPalace 实例"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        mp = MemoryPalace(db_path=db_path)
        yield mp
        
        # 清理
        try:
            os.unlink(db_path)
        except:
            pass
    
    def test_remember_fact(self, memory_palace):
        """测试添加事实"""
        result = memory_palace.remember_fact(
            category='preference',
            key='测试键',
            value='测试值',
            strength=0.9
        )
        assert result is not None
        assert 'id' in result  # 返回 dict
    
    def test_relate(self, memory_palace):
        """测试添加关系"""
        result = memory_palace.relate(
            subject='实体A',
            predicate='关联',
            object='实体B',  # 注意是 object 不是 obj
            strength=0.8
        )
        assert result is not None
        assert 'id' in result
    
    def test_observe_habit(self, memory_palace):
        """测试添加习惯"""
        result = memory_palace.observe_habit(
            domain='coding',
            pattern='深夜写代码',
            evidence='用户多次在深夜提交代码',
            certainty=0.7  # 注意是 certainty 不是 strength
        )
        assert result is not None
        assert 'id' in result
    
    def test_record_event(self, memory_palace):
        """测试添加时间线"""
        result = memory_palace.record_event(
            event_date=date.today(),
            event_type='test_event',
            title='这是一个测试事件'  # 注意是 title 不是 content
        )
        assert result is not None
        assert result > 0  # 返回 int
    
    def test_recall_facts(self, memory_palace):
        """测试查询事实"""
        # 添加测试数据
        memory_palace.remember_fact('preference', '颜色', '蓝色', strength=0.9)
        memory_palace.remember_fact('preference', '语言', 'Python', strength=0.95)
        
        # 测试查询
        results = memory_palace.recall_facts(category='preference')
        assert len(results) >= 2
        
        results = memory_palace.recall_facts(key='颜色')
        assert len(results) >= 1
    
    def test_recall_relations(self, memory_palace):
        """测试查询关系"""
        # 添加测试数据
        memory_palace.relate('用户', '创建了', 'Omnia项目')
        memory_palace.relate('Omnia', '包含', 'MemoryPalace')
        
        # 测试查询
        results = memory_palace.recall_relations(entity="用户")
        assert len(results) >= 2
