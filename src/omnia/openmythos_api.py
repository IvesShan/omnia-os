"""
OpenMythos Web API Integration

将循环推理引擎接入 Omnia Web Server
"""

from flask import Blueprint, request, jsonify, Response
from typing import Dict, Optional, Callable, Tuple
import json
import time
import os

from core.openmythos import IntegrationBridge
from core.memory_palace.memory_palace import MemoryPalace

# 创建蓝图
openmythos_bp = Blueprint('openmythos', __name__)

# 全局实例
_bridge: Optional[IntegrationBridge] = None
_model_call_fn: Optional[Callable] = None


def _get_api_config() -> Tuple[str, str]:
    """
    获取当前激活的 API 配置
    
    Returns:
        (api_key, provider) 元组
    """
    # 尝试从 .env 文件加载
    from pathlib import Path
    from dotenv import load_dotenv
    
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    load_dotenv(PROJECT_ROOT / ".env")
    
    # 按优先级检查 API keys
    providers = [
        ("QIANFAN_API_KEY", "qianfan"),
        ("KIMI_API_KEY", "kimi"),
        ("MOONSHOT_API_KEY", "kimi"),
        ("OPENAI_API_KEY", "openai"),
        ("ANTHROPIC_API_KEY", "anthropic"),
    ]
    
    for key_name, provider in providers:
        api_key = os.environ.get(key_name, "")
        if api_key and not api_key.startswith("#"):
            print(f"[OpenMythos Config] Found {key_name} for provider {provider}")
            return api_key, provider
    
    print("[OpenMythos Config] No API key found")
    return "", "unknown"


def _create_model_call_adapter(original_call_fn: Callable) -> Callable:
    """
    创建模型调用适配器
    
    将 Omnia 的 _call_model_messages 签名适配为 IntegrationBridge 期望的签名
    
    原始签名: (api_key: str, provider: str, messages: list, tools: list | None) -> dict
    期望签名: (prompt: str, context: Optional[Dict]) -> str
    """
    def adapter(prompt: str, context: Optional[Dict] = None) -> str:
        """适配器函数"""
        # 动态获取 API 配置（支持运行时切换）
        api_key, provider = _get_api_config()
        
        if not api_key:
            return "Error: No API key configured"
        
        print(f"[OpenMythos Adapter] Calling {provider} with prompt: {prompt[:50]}...")
        
        # 构建消息
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # 添加上下文
        if context and "history" in context:
            messages = context["history"] + messages
        
        try:
            # 调用原始函数
            result = original_call_fn(api_key, provider, messages, tools=None)
            
            print(f"[OpenMythos Adapter] Result type: {type(result)}")
            
            # 提取响应文本
            if isinstance(result, dict):
                # OpenAI 格式
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    print(f"[OpenMythos Adapter] Extracted content: {content[:100]}...")
                    return content
                # Anthropic 格式
                elif "content" in result and len(result["content"]) > 0:
                    content = result["content"][0].get("text", "")
                    print(f"[OpenMythos Adapter] Extracted content: {content[:100]}...")
                    return content
                # 错误响应
                elif "error" in result:
                    error_msg = result.get("error", {}).get("message", str(result))
                    print(f"[OpenMythos Adapter] Error in result: {error_msg}")
                    return f"Error: {error_msg}"
            
            # 降级：返回字符串形式
            print(f"[OpenMythos Adapter] Fallback to string: {str(result)[:100]}")
            return str(result)
        
        except Exception as e:
            error_msg = f"Exception in model call: {str(e)}"
            print(f"[OpenMythos Adapter] {error_msg}")
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}"
    
    return adapter


def init_openmythos(model_call_fn, memory_palace=None):
    """初始化 OpenMythos
    
    Args:
        model_call_fn: 模型调用函数（Omnia 格式）
        memory_palace: 记忆宫殿实例
    """
    global _bridge, _model_call_fn
    
    _model_call_fn = model_call_fn
    
    # 创建适配器
    adapted_call_fn = _create_model_call_adapter(model_call_fn)
    
    _bridge = IntegrationBridge(
        model_call=adapted_call_fn,
        memory_palace=memory_palace
    )
    
    # 显示当前配置
    api_key, provider = _get_api_config()
    key_preview = api_key[:20] + "..." if len(api_key) > 20 else api_key
    print(f"[OpenMythos] Initialized with provider: {provider}, key: {key_preview}")


def get_bridge() -> Optional[IntegrationBridge]:
    """获取 IntegrationBridge 实例"""
    return _bridge


@openmythos_bp.route('/api/openmythos/status', methods=['GET'])
def status():
    """OpenMythos 状态检查"""
    api_key, provider = _get_api_config()
    
    return jsonify({
        "initialized": _bridge is not None,
        "provider": provider,
        "api_key_preview": api_key[:20] + "..." if len(api_key) > 20 else "not configured"
    })


@openmythos_bp.route('/api/openmythos/chat', methods=['POST'])
def chat():
    """循环推理对话接口
    
    Request:
        {
            "message": "用户消息",
            "context": {}  // 可选
        }
    
    Response:
        {
            "answer": "回答",
            "confidence": 0.88,
            "iterations": 3,
            "complexity": "balanced",
            "time_elapsed": 1.23
        }
    """
    if not _bridge:
        return jsonify({'error': 'OpenMythos not initialized'}), 500
    
    data = request.json or {}
    message = data.get('message', '')
    context = data.get('context')
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    print(f"[OpenMythos API] Received message: {message[:50]}...")
    
    # 处理查询
    result = _bridge.process(message, context)
    
    print(f"[OpenMythos API] Result: iterations={result.get('iterations')}, confidence={result.get('confidence')}")
    
    return jsonify(result)


@openmythos_bp.route('/api/openmythos/chat/stream', methods=['POST'])
def chat_stream():
    """流式推理对话接口（SSE）
    
    返回 Server-Sent Events 流
    """
    if not _bridge:
        return jsonify({'error': 'OpenMythos not initialized'}), 500
    
    data = request.json or {}
    message = data.get('message', '')
    context = data.get('context')
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    def generate():
        """生成 SSE 流"""
        try:
            # 使用 bridge 的流式处理
            for event in _bridge.process_stream(message, context):
                yield f"data: {json.dumps(event)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )
