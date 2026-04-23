#!/usr/bin/env python3
"""简单测试飞书 WebSocket 客户端"""

# 1. 导入模块
try:
    import lark_oapi
    print("✓ lark_oapi 导入成功")
except Exception as e:
    print(f"✗ lark_oapi 导入失败: {e}")

# 2. 查看 ws 模块
print("\n=== 查看 ws 模块 ===")
try:
    import lark_oapi.ws
    print("✓ lark_oapi.ws 导入成功")
    
    # 查看 ws 模块的内容
    print("ws 模块内容:")
    for attr in dir(lark_oapi.ws):
        if not attr.startswith('_'):
            print(f"  - {attr}")
except Exception as e:
    print(f"✗ lark_oapi.ws 导入失败: {e}")

# 3. 查看 ws.client
print("\n=== 查看 ws.client ===")
try:
    import lark_oapi.ws.client as ws_client
    print("✓ ws.client 导入成功")
    
    # 查看 Client 类
    print("Client 类属性:")
    for attr in dir(ws_client.Client):
        if not attr.startswith('_'):
            print(f"  - {attr}")
            
    # 查看 __init__ 方法
    print("\nClient.__init__ 方法:")
    import inspect
    sig = inspect.signature(ws_client.Client.__init__)
    print(f"  签名: {sig}")
    
    # 打印参数详情
    print("\n  参数详情:")
    for param_name, param in sig.parameters.items():
        if param_name != 'self':
            print(f"    {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else '无类型提示'}")
            
except Exception as e:
    print(f"✗ ws.client 导入失败: {e}")

# 4. 查看 ws.model
print("\n=== 查看 ws.model ===")
try:
    import lark_oapi.ws.model as ws_model
    print("✓ ws.model 导入成功")
    
    print("ws.model 内容:")
    for attr in dir(ws_model):
        if not attr.startswith('_'):
            obj = getattr(ws_model, attr)
            print(f"  - {attr}: {type(obj).__name__}")
except Exception as e:
    print(f"✗ ws.model 导入失败: {e}")