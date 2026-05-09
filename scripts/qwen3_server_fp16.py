#!/usr/bin/env python3
"""
Qwen3-8B 推理服务器（FP16）
适配 AMD ROCm
"""

import os
import json
import torch
from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer

app = Flask(__name__)

# 模型路径
MODEL_PATH = "/home/shan/models/Qwen3-8B"

print("=" * 60)
print("Qwen3-8B 推理服务器（FP16）")
print("=" * 60)

# 检查 GPU
print(f"\n[GPU] 检测到 {torch.cuda.device_count()} 个 GPU")
if torch.cuda.is_available():
    print(f"[GPU] 设备名称: {torch.cuda.get_device_name(0)}")
    print(f"[GPU] 显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# 加载 tokenizer
print(f"\n[Tokenizer] 加载中...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True
)
print(f"[Tokenizer] ✓ 加载完成")

# 加载模型（FP16）
print(f"\n[Model] 加载中（FP16）...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)
print(f"[Model] ✓ 加载完成")

# 显存使用
if torch.cuda.is_available():
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"\n[显存] 已分配: {allocated:.2f} GB")
    print(f"[显存] 已预留: {reserved:.2f} GB")

print("\n" + "=" * 60)
print("服务器启动在 http://localhost:8080")
print("=" * 60 + "\n")


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """OpenAI 兼容的聊天 API"""
    try:
        data = request.json
        messages = data.get("messages", [])
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 2048)
        stream = data.get("stream", False)
        
        # 构建提示词
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
                top_p=0.9,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # 解码
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 提取助手回复
        if "<|im_start|>assistant" in response:
            response = response.split("<|im_start|>assistant")[-1].strip()
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0].strip()
        
        # 返回 OpenAI 格式
        import time
        result = {
            "id": "chatcmpl-qwen3-8b",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "qwen3-8b-fp16",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(inputs["input_ids"][0]),
                "completion_tokens": len(outputs[0]) - len(inputs["input_ids"][0]),
                "total_tokens": len(outputs[0])
            }
        }
        
        return jsonify(result)
    
    except Exception as e:
        print(f"[Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "model": "qwen3-8b-fp16",
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
