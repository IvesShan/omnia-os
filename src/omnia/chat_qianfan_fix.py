#!/usr/bin/env python3
import re

# Read the file
with open('/home/shan/.openclaw/workspace/omnia-os/src/omnia/chat.py', 'r') as f:
    content = f.read()

# Find and replace the problematic section
old_code = '''    if provider in ("baiduqianfancodingplan", "qianfan"):
        # Coding Plan API Key starts with "bce-v3/" - use IAM auth format
        # Parse bce-v3/AccessKeyId/SecretKey format
        if api_key.startswith("bce-v3/"):
            parts = api_key.split("/")
            if len(parts) >= 3:
                iam_access_key = f"bce-v3/{parts[1]}"
                iam_secret_key = parts[2]
                use_iam_auth = True
                print(f"[_call_model_messages] Using IAM auth with AccessKeyId: {iam_access_key[:30]}...")
            else:
                headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Convert messages to prompt format for completions API
        prompt_parts = []
        system_content = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_content = content
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Build final prompt
        if system_content:
            prompt = f"System: {system_content}\\n\\n" + "\\n".join(prompt_parts) + "\\nAssistant:"
        else:
            prompt = "\\n".join(prompt_parts) + "\\nAssistant:"
        
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        
        # Apply IAM auth if needed
        if use_iam_auth and iam_access_key and iam_secret_key:
            body = json.dumps(payload, separators=(",", ":"))
            headers = _aws_signature_v4(
                "POST", url, headers, body,
                iam_access_key, iam_secret_key,
                service="coding", region="bj"
            )
            print(f"[_call_model_messages] IAM auth headers added")
            print(f"[_call_model_messages] Auth header: {headers.get('Authorization', '')[:80]}...")
        
        print(f"[_call_model_messages] Qianfan completions payload: {json.dumps(payload)[:200]}...")
    else:'''

new_code = '''    if provider in ("baiduqianfancodingplan", "qianfan"):
        # Use standard Bearer token auth
        headers["Authorization"] = f"Bearer {api_key}"
        
        # Standard chat completions format (same as OpenAI)
        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        
        if tools:
            payload["tools"] = tools
        
        print(f"[_call_model_messages] Qianfan chat with {len(messages)} messages")
    else:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/home/shan/.openclaw/workspace/omnia-os/src/omnia/chat.py', 'w') as f:
        f.write(content)
    print("✓ chat.py patched successfully")
else:
    print("✗ Could not find the exact code to replace")
    # Try to find similar pattern
    if 'bce-v3/' in content and '_aws_signature_v4' in content:
        print("  Found bce-v3 and _aws_signature_v4 in file")
