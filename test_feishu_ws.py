#!/usr/bin/env python3
"""测试飞书 WebSocket 客户端的事件类型"""

try:
    import lark_oapi
    print(f"lark_oapi 模块: {lark_oapi}")
except Exception as e:
    print(f"导入 lark_oapi 错误: {e}")

try:
    import lark_oapi.ws
    print(f"lark_oapi.ws 模块: {lark_oapi.ws}")
except Exception as e:
    print(f"导入 lark_oapi.ws 错误: {e}")

# 检查 ws 模块的内容
print("\n=== lark_oapi.ws 模块内容 ===")
try:
    for attr in dir(lark_oapi.ws):
        if not attr.startswith('_'):
            print(f"  {attr}")
except Exception as e:
    print(f"检查 ws 模块错误: {e}")

# 检查 ws.client
print("\n=== lark_oapi.ws.client 模块 ===")
try:
    import lark_oapi.ws.client
    for attr in dir(lark_oapi.ws.client):
        if not attr.startswith('_'):
            print(f"  {attr}")
except Exception as e:
    print(f"检查 ws.client 错误: {e}")

# 检查 ws.model
print("\n=== lark_oapi.ws.model 模块 ===")
try:
    import lark_oapi.ws.model
    for attr in dir(lark_oapi.ws.model):
        if not attr.startswith('_'):
            print(f"  {attr}")
except Exception as e:
    print(f"检查 ws.model 错误: {e}")

# 查看 Client 类
print("\n=== Client 类 ===")
try:
    Client = lark_oapi.ws.client.Client
    print(f"Client 类: {Client}")
    print(f"Client 文档: {Client.__doc__[:200] if Client.__doc__ else '无文档'}")
except Exception as e:
    print(f"获取 Client 类错误: {e}")

# 查看 EventHandler 相关
print("\n=== 查找事件处理器 ===")
try:
    # 查看是否有 EventHandler 或类似的东西
    import inspect
    sig = inspect.signature(lark_oapi.ws.client.Client.__init__)
    print(f"Client.__init__ 签名: {sig}")
except Exception as e:
    print(f"检查签名错误: {e}")