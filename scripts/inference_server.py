#!/usr/bin/env python3
"""
本地 LLM 推理服务器 - CPU 模式
支持 Qwen3-8B 等模型
"""

import os

# 强制使用 CPU
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import json
import torch
from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer

app = Flask(__name__)

# 全局模型和 tokenizer
model = None
tokenizer = None
MODEL_PATH = "/home/shan/models/Qwen3-8B"

def load_model():
    """加载模型（CPU 模式）"""
    global model, tokenizer
    
    print(f"[INFO] 加载模型: {MODEL_PATH}")
    print(f"[INFO] 使用设备: CPU（GPU 模式不稳定）")
    
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True
    )
    
    # 加载模型到 CPU
    try:
        print("[INFO] 开始加载模型权重到 CPU...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float32,  # CPU 用 float32
            device_map="cpu",
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        print(f"[INFO] 模型加载成功")
        print(f"[INFO] 模型设备: {model.device}")
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        raise

@app.route('/v1/models', methods=['GET'])
def list_models():
    """列出可用模型"""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "qwen3-8b",
                "object": "model",
                "owned_by": "local"
            }
        ]
    })

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """聊天补全 API"""
    global model, tokenizer
    
    try:
        data = request.json
        messages = data.get('messages', [])
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1024)  # CPU 模式减少默认值
        
        # 构建提示词
        prompt = ""
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == 'user':
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == 'assistant':
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        prompt += "<|im_start|>assistant\n"
        
        # 编码
        inputs = tokenizer(prompt, return_tensors="pt")
        
        # 生成
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # 解码
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 提取助手回复
        if "<|im_start|>assistant" in response:
            response = response.split("<|im_start|>assistant")[-1].strip()
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0].strip()
        
        # 返回 OpenAI 格式
        result = {
            "id": "chatcmpl-local",
            "object": "chat.completion",
            "model": "qwen3-8b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }
            ]
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[ERROR] 推理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "model": "qwen3-8b", "device": "cpu"})

if __name__ == '__main__':
    print("[INFO] 启动推理服务器（CPU 模式）...")
    load_model()
    print("[INFO] 服务器运行在 http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
