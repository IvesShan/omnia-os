#!/usr/bin/env python3
"""
本地 LLM 推理服务器 - Qwen3-8B
使用 transformers + FastAPI 提供 OpenAI 兼容 API
优化显存使用
"""

import os
import gc
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from transformers import AutoModelForCausalLM, AutoTokenizer

# 配置
MODEL_PATH = os.environ.get("LOCAL_LLM_PATH", "/home/shan/models/Qwen3-8B")
PORT = int(os.environ.get("LOCAL_LLM_PORT", "8080"))

print(f"[local_llm_server] Loading model from {MODEL_PATH}...")

# 清理显存
torch.cuda.empty_cache()
gc.collect()

# 加载 tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

# 加载模型 - 使用 float16 + device_map auto
print("[local_llm_server] Loading model (this may take a minute)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
    low_cpu_mem_usage=True
)

print(f"[local_llm_server] Model loaded successfully!")
print(f"[local_llm_server] Device map: {model.hf_device_map}")
print(f"[local_llm_server] Starting server on port {PORT}...")

# FastAPI 应用
app = FastAPI(title="Local LLM Server")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    tools: Optional[List[Dict[str, Any]]] = None

class ChatChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class ChatResponse(BaseModel):
    id: str
    object: str
    choices: List[ChatChoice]
    model: str

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI 兼容的 chat completions API"""
    
    # 构建对话
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # 如果有工具，添加到系统提示
    if request.tools:
        tools_desc = "\n\n可用工具:\n"
        for tool in request.tools:
            tools_desc += f"- {tool['function']['name']}: {tool['function'].get('description', '')}\n"
        
        # 在第一条消息前添加工具说明
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] += tools_desc
        else:
            messages.insert(0, {"role": "system", "content": f"你是一个有用的AI助手。{tools_desc}"})
    
    # 生成回复
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # 解码回复
    response_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    
    return ChatResponse(
        id="local-" + str(hash(response_text) % 1000000),
        object="chat.completion",
        choices=[
            ChatChoice(
                index=0,
                message=Message(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ],
        model=request.model
    )

@app.get("/health")
async def health():
    return {"status": "ok", "model": "Qwen3-8B"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
