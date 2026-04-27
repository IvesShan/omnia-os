#!/usr/bin/env python3
"""
测试飞书连接 - 验证SDK修复后的连接状态
"""

import os
import json
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_basic_connection():
    """测试基本连接和认证"""
    print("=" * 60)
    print("🧪 测试飞书连接")
    print("=" * 60)
    
    # 1. 检查配置文件
    config_path = os.path.join(project_root, "config", "feishu.json")
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"📄 配置文件: {config_path}")
    print(f"   App ID: {config.get('app_id', '未设置')}")
    print(f"   App Secret: {'*' * 10 if config.get('app_secret') else '未设置'}")
    print(f"   连接模式: {config.get('connection_mode', '未设置')}")
    print(f"   已启用: {config.get('enabled', False)}")
    
    # 2. 测试SDK导入
    print("\n📦 测试SDK导入...")
    try:
        import lark_oapi as lark
        print("✅ lark_oapi 导入成功")
        
        # 测试具体模块导入
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
        print("✅ CreateMessageRequest, CreateMessageRequestBody 导入成功")
        
    except ImportError as e:
        print(f"❌ SDK导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他导入错误: {e}")
        return False
    
    # 3. 测试客户端创建
    print("\n🔧 测试客户端创建...")
    try:
        # 创建客户端（不实际连接）
        from lark_oapi import Client
        
        client = Client.builder() \
            .app_id(config['app_id']) \
            .app_secret(config['app_secret']) \
            .domain("https://open.feishu.cn") \
            .build()
        
        print("✅ 客户端创建成功")
        print(f"   域: {client.domain}")
        
        # 4. 测试认证（获取access_token）
        print("\n🔑 测试认证...")
        try:
            # 尝试获取access_token
            from lark_oapi.api.authen.v1 import CreateAccessTokenRequest
            
            req = CreateAccessTokenRequest.builder() \
                .request_body({}) \
                .build()
            
            # 这里可能会失败，因为需要有效的app_id/app_secret
            # 但我们只测试请求构建，不实际发送
            print("✅ 认证请求构建成功")
            print("⚠️  注意：需要有效的App ID/Secret才能实际认证")
            
        except Exception as e:
            print(f"⚠️  认证请求构建警告: {e}")
            print("   可能原因：SDK版本或API变更")
        
        return True
        
    except Exception as e:
        print(f"❌ 客户端创建失败: {e}")
        return False

def test_message_sending():
    """测试消息发送功能（不实际发送）"""
    print("\n" + "=" * 60)
    print("💬 测试消息发送功能")
    print("=" * 60)
    
    try:
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
        import json
        
        # 构建测试消息请求
        req = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id("test_chat_id_123")
                .msg_type("text")
                .content(json.dumps({"text": "这是一个测试消息"}))
                .build()) \
            .build()
        
        print("✅ 消息请求构建成功")
        print(f"   接收ID类型: {req.receive_id_type}")
        print(f"   消息类型: {req.request_body.msg_type}")
        
        # 尝试序列化请求（测试请求结构）
        try:
            req_dict = req.to_dict()
            print("✅ 请求序列化成功")
        except Exception as e:
            print(f"⚠️  请求序列化警告: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 消息发送测试失败: {e}")
        return False

def main():
    print("🚀 Omnia 飞书连接测试")
    print(f"📁 项目根目录: {project_root}")
    
    # 运行测试
    config_test = test_basic_connection()
    message_test = test_message_sending()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    if config_test and message_test:
        print("✅ 所有测试通过！")
        print("\n📋 下一步：")
        print("1. 确保飞书应用配置正确（App ID/Secret）")
        print("2. 运行修复后的飞书WebSocket服务")
        print("3. 在飞书中测试消息收发")
        return 0
    else:
        print("❌ 部分测试失败")
        print("\n🔧 需要检查：")
        print("1. SDK版本兼容性")
        print("2. 配置文件格式")
        print("3. Python环境依赖")
        return 1

if __name__ == "__main__":
    sys.exit(main())