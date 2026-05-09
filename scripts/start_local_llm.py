#!/usr/bin/env python3
"""
本地 LLM 推理服务器 - 使用 transformers + Flask
支持 Qwen3-8B 模型
"""

import os
import json
import torch
from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局变量
model = None
tokenizer = None

def load_model():
    """加载模型"""
    global model, tokenizer
    
    model_path = os.environ.get("LOCAL_MODEL_PATH", "/home/shan/models/Qwen3-8B")
    logger.info(f"正在加载模型: {model_path}")
    
    # 加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    
    # 加载模型 - 使用 bfloat16 节省显存
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    
    model.eval()
    logger.info("模型加载完成")

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """OpenAI 兼容的 chat completions API"""
    try:
        data = request.get_json()
        messages = data.get("messages", [])
        max_tokens = data.get("max_tokens", 512)
        temperature = data.get("temperature", 0.7)
        stream = data.get("stream", False)
        
        # 构建 prompt
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        prompt += "<|im_start|>assistant\n"
        
        # 编码
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # 生成
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # 解码
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        
        # 返回 OpenAI 格式
        result = {
            "id": "local-qwen3-8b",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "model": "Qwen3-8B"
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"推理错误: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "model": "Qwen3-8B"})

if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=8080, threaded=False)
