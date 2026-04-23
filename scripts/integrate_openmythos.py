#!/usr/bin/env python3
"""
OpenMythos Integration Script

将 OpenMythos 接入 Omnia Web Server
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 读取 web_server.py
web_server_path = PROJECT_ROOT / "src" / "omnia" / "web_server.py"
content = web_server_path.read_text(encoding='utf-8')

# 1. 在导入部分添加 OpenMythos
import_insert = """
# OpenMythos Integration
from omnia.openmythos_api import openmythos_bp, init_openmythos
"""

if "from omnia.openmythos_api" not in content:
    # 在 from omnia.wake 之后插入
    content = content.replace(
        "from omnia.wake import assemble_wake_prompt",
        "from omnia.wake import assemble_wake_prompt\n" + import_insert
    )
    print("✅ 添加 OpenMythos 导入")

# 2. 在 create_app 函数中注册蓝图
# 找到 app.register_blueprint 的位置
if "openmythos_bp" not in content:
    # 在 CORS(app) 之后添加
    blueprint_register = """
    # Register OpenMythos blueprint
    app.register_blueprint(openmythos_bp)
    print("[Web Server] OpenMythos API registered")
    
    """
    
    content = content.replace(
        "CORS(app)",
        "CORS(app)\n" + blueprint_register
    )
    print("✅ 注册 OpenMythos 蓝图")

# 3. 在 create_app 函数中初始化 OpenMythos
if "init_openmythos" not in content:
    # 在 return app 之前添加
    init_code = """
    # Initialize OpenMythos with model call function
    def _model_call_for_openmythos(prompt: str, context: dict = None) -> str:
        \"\"\"模型调用适配器\"\"\"
        try:
            # 使用现有的模型调用逻辑
            messages = [{"role": "user", "content": prompt}]
            response = _call_model_messages(messages, context=context or {})
            return response
        except Exception as e:
            return f"Error: {e}"
    
    try:
        init_openmythos(_model_call_for_openmythos, memory_palace=MemoryPalace())
        print("[Web Server] OpenMythos initialized")
    except Exception as e:
        print(f"[Web Server] OpenMythos init failed: {e}")
    
    """
    
    # 在 return app 之前插入
    content = content.replace(
        "    return app",
        init_code + "    return app"
    )
    print("✅ 添加 OpenMythos 初始化")

# 保存修改
web_server_path.write_text(content, encoding='utf-8')
print(f"\n✅ 已更新 {web_server_path}")

# 创建测试脚本
test_script = PROJECT_ROOT / "test_openmythos_web.py"
test_script.write_text("""
#!/usr/bin/env python3
\"\"\"Test OpenMythos Web API\"\"\"

import requests
import json

BASE_URL = "http://localhost:5000"

def test_analyze():
    \"\"\"测试复杂度分析\"\"\"
    print("\\n=== 测试复杂度分析 ===")
    
    response = requests.post(f"{BASE_URL}/api/openmythos/analyze", json={
        "message": "设计一个分布式系统架构"
    })
    
    print(f"状态: {response.status_code}")
    print(f"结果: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_chat():
    \"\"\"测试对话\"\"\"
    print("\\n=== 测试对话 ===")
    
    response = requests.post(f"{BASE_URL}/api/openmythos/chat", json={
        "message": "你好"
    })
    
    print(f"状态: {response.status_code}")
    result = response.json()
    print(f"答案: {result.get('answer', '')[:100]}")
    print(f"置信度: {result.get('confidence')}")
    print(f"迭代次数: {result.get('iterations')}")

def test_stats():
    \"\"\"测试统计信息\"\"\"
    print("\\n=== 测试统计信息 ===")
    
    response = requests.get(f"{BASE_URL}/api/openmythos/stats")
    
    print(f"状态: {response.status_code}")
    print(f"结果: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    print("OpenMythos Web API 测试")
    print("=" * 60)
    
    try:
        test_analyze()
        test_chat()
        test_stats()
        
        print("\\n" + "=" * 60)
        print("✅ 所有测试完成")
    except Exception as e:
        print(f"\\n❌ 测试失败: {e}")
""", encoding='utf-8')

print(f"✅ 创建测试脚本 {test_script}")

print("\n" + "=" * 60)
print("集成完成！")
print("=" * 60)
print("\n下一步:")
print("1. 重启 Web Server: python3 src/omnia/web_server.py")
print("2. 运行测试: python3 test_openmythos_web.py")
print("\nAPI 端点:")
print("  POST /api/openmythos/chat        - 循环推理对话")
print("  POST /api/openmythos/chat/stream - 流式对话 (SSE)")
print("  POST /api/openmythos/analyze     - 复杂度分析")
print("  GET  /api/openmythos/stats       - 统计信息")
