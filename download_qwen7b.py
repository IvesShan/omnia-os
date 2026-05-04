#!/usr/bin/env python3
"""下载并测试 Qwen2.5-7B-Instruct 模型"""

import os
os.environ['HSA_OVERRIDE_GFX_VERSION'] = '10.3.0'
os.environ['HIP_VISIBLE_DEVICES'] = '0'

import torch
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU 设备: {torch.cuda.get_device_name(0)}")
    print(f"GPU 内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

print("\n" + "="*50)
print("下载 Qwen2.5-7B-Instruct")
print("="*50)

from modelscope import snapshot_download

model_dir = snapshot_download(
    'Qwen/Qwen2.5-7B-Instruct',
    cache_dir='/home/shan/.cache/modelscope',
    revision='master'
)

print(f"模型下载完成: {model_dir}")

# 测试模型
print("\n" + "="*50)
print("测试模型")
print("="*50)

from transformers import AutoModelForCausalLM, AutoTokenizer

print("加载 tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)

print("加载模型...")
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    device_map="auto",
    torch_dtype=torch.float16,
    trust_remote_code=True
)

print("模型加载成功！")

# 测试思考能力
test_prompts = [
    "用户昨天说今天有重要会议。现在是早上8点。作为 AI 助手，你应该主动做什么？",
]

for i, prompt in enumerate(test_prompts):
    print(f"\n{'='*50}")
    print(f"测试 {i+1}: {prompt[:50]}...")
    print("="*50)
    
    messages = [
        {"role": "system", "content": "你是一个具有主动思考能力的 AI 助手。你不仅要回答用户的问题，还要主动思考用户可能需要什么，并主动提供帮助。"},
        {"role": "user", "content": prompt}
    ]
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
        do_sample=True
    )
    
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    print(f"回复:\n{response}")
    print("-"*50)

print("\n测试完成！")
