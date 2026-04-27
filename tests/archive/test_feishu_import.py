#!/usr/bin/env python3
# 测试飞书 SDK 1.5.3 的正确导入方式

import lark_oapi.ws

# 查看 Client 类的参数
print("lark_oapi.ws.Client 的签名:")
import inspect
try:
    sig = inspect.signature(lark_oapi.ws.Client)
    print(f"构造函数参数: {sig}")
except Exception as e:
    print(f"获取签名失败: {e}")

# 查看 model 模块的内容
print("\nlark_oapi.ws.model 的内容:")
import lark_oapi.ws.model as model
for item in dir(model):
    if not item.startswith('_'):
        print(f"  {item}")

# 检查是否有事件相关的类
print("\n检查是否有 Event 或 Message 相关的类:")
for item in dir(model):
    if 'event' in item.lower() or 'message' in item.lower():
        print(f"  找到: {item}")
        try:
            cls = getattr(model, item)
            print(f"    类型: {type(cls)}")
        except:
            pass

# 查看 ws.const 模块
print("\nlark_oapi.ws.const 的内容:")
import lark_oapi.ws.const as const
for item in dir(const):
    if not item.startswith('_'):
        print(f"  {item}")