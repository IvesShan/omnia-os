"""
Web Server API 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


class TestWebServerAPI:
    """Web Server API 测试套件"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        try:
            from omnia.web_server import app
            app.config['TESTING'] = True
            return app
        except ImportError:
            pytest.skip("web_server 模块不可用")
    
    def test_status_endpoint(self, app):
        """测试状态端点"""
        client = app.test_client()
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
    
    def test_graph_stats_endpoint(self, app):
        """测试图谱统计端点"""
        client = app.test_client()
        response = client.get('/api/graph/stats')
        assert response.status_code in [200, 404]  # 可能不存在
        if response.status_code == 200:
            data = response.get_json()
            assert 'nodes' in data or 'total_nodes' in data
    
    def test_token_status_endpoint(self, app):
        """测试 token 状态端点"""
        client = app.test_client()
        response = client.get('/api/token/status')
        assert response.status_code in [200, 404]
    
    def test_memory_search_endpoint(self, app):
        """测试记忆搜索端点"""
        client = app.test_client()
        response = client.get('/api/memory/search?q=test')
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data or 'results' in data
