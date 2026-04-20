"""Omnia Chat — Terminal conversational interface."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent  # src/omnia/chat.py -> src/ -> project_root
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omnia.wake import assemble_wake_prompt
from omnia.kimi_anthropic import call_kimi_anthropic


def _aws_signature_v4(
    method: str,
    url: str,
    headers: dict,
    body: str,
    access_key_id: str,
    secret_key: str,
    service: str = "coding",
    region: str = "bj"
) -> dict:
    """Generate BCE Auth V1 signature for Baidu Qianfan IAM auth."""
    import urllib.parse
    
    # Parse URL
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc
    path = parsed.path or "/"
    
    # Timestamp - use local time for Baidu
    now = datetime.utcnow()
    amz_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_stamp = now.strftime("%Y%m%d")
    
    # Step 1: Create canonical request (simpler for Baidu)
    http_method = method.upper()
    
    # Baidu uses URL-encoded path
    canonical_uri = path
    
    # No query string for POST to /v2/coding
    canonical_querystring = ""
    
    # Headers - only host is required
    signed_headers_list = ["host"]
    canonical_headers = f"host:{host}\n"
    signed_headers = ";".join(signed_headers_list)
    
    # Payload hash
    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    
    # Canonical request string
    canonical_request = "\n".join([
        http_method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash
    ])
    
    # Step 2: Create string to sign (BCE format)
    algorithm = "bce-auth-v1"
    # Baidu format: bce-auth-v1/{accessKeyId}/{timestamp}/{expirationPeriod}
    expiration = "3600"  # 1 hour
    
    # Signing key is just the secret key for Baidu's simpler auth
    signing_key = secret_key.encode("utf-8")
    
    # String to sign includes canonical request hash
    string_to_sign = canonical_request
    
    # Step 3: Calculate signature
    signature = hmac.new(
        signing_key,
        string_to_sign.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # Step 4: Build Authorization header (BCE format)
    # bce-auth-v1/{accessKeyId}/{timestamp}/{expirationPeriod}/{signedHeaders}/{signature}
    auth_header = (
        f"bce-auth-v1/{access_key_id}/{amz_date}/{expiration}/"
        f"{signed_headers}/{signature}"
    )
    
    # Return updated headers
    return {
        **headers,
        "Authorization": auth_header,
    }


def _load_api_key(prefer_provider: str | None = None) -> Tuple[Optional[str], Optional[str]]:
    """Try to load API key from .env file first, then environment variables.
    
    This ensures user configuration in .env takes precedence over system env.
    """
    # Priority 1: .env file in project root (user explicit config)
    env_file = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key] = val.strip().strip('"').strip("'")
    
    # Check .env first
    for key in ["QIANFAN_API_KEY", "QIANFAN_ACCESS_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if key in env_vars:
            return key, env_vars[key]
    
    # Priority 2: Environment variables (fallback)
    for key in ["QIANFAN_API_KEY", "QIANFAN_ACCESS_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        val = os.environ.get(key)
        if val:
            return key, val
    
    return None, None


def _try_chat_with_fallback(message: str, system_prompt: str, primary_key: str, primary_name: str) -> str | None:
    """Try to chat with primary provider, fallback to others if fails."""
    # Try primary first
    try:
        key_name, api_key = _load_api_key()
        if api_key:
            provider = "kimi"
            if key_name in ("QIANFAN_API_KEY", "QIANFAN_ACCESS_KEY"):
                provider = "qianfan"
            elif key_name == "OPENAI_API_KEY":
                provider = "openai"
            
            reply = _chat_openai_compatible_requests(api_key, provider, system_prompt, message)
            return f"[{provider}] {reply}"
    except Exception as e:
        print(f"[Omnia] Primary provider failed: {e}")
    
    # Fallback: try all configured providers
    fallback_order = [
        ("MOONSHOT_API_KEY", "kimi", "Moonshot"),
        ("OPENAI_API_KEY", "openai", "OpenAI"),
    ]
    
    for env_key, provider, name in fallback_order:
        api_key = os.environ.get(env_key)
        if api_key:
            try:
                reply = _chat_openai_compatible_requests(api_key, provider, system_prompt, message)
                return f"[{provider}] {reply}"
            except Exception as e:
                print(f"[Omnia] Fallback {name} failed: {e}")
                continue
    
    return None


def chat(message: str) -> None:
    key_name, api_key = _load_api_key()
    if not api_key:
        print(
            "[Omnia] No API key found.\n"
            "Please set one of the following in your environment or in omnia-os/.env:\n"
            "  QIANFAN_API_KEY=your_key_here      # Baidu Qianfan (Recommended)\n"
            "  MOONSHOT_API_KEY=your_key_here     # Moonshot/Kimi\n"
            "  KIMI_API_KEY=your_key_here         # Kimi Legacy\n"
            "  OPENAI_API_KEY=your_key_here       # OpenAI\n"
            "  ANTHROPIC_API_KEY=your_key_here    # Anthropic Claude"
        )
        return

    # Build system prompt via wake cycle
    print("[Omnia] Waking up...\n")
    system_prompt = assemble_wake_prompt(message)

    # Detect provider
    provider = "kimi"
    if key_name in ("QIANFAN_API_KEY", "QIANFAN_ACCESS_KEY"):
        # Use OpenClaw-compatible provider ID
        provider = "baiduqianfancodingplan"
    elif key_name in ("MOONSHOT_API_KEY", "KIMI_API_KEY"):
        provider = "kimi"
    elif key_name == "OPENAI_API_KEY":
        provider = "openai"
    elif key_name == "ANTHROPIC_API_KEY":
        provider = "anthropic"

    try:
        if provider == "anthropic":
            _chat_anthropic(api_key, system_prompt, message)
        else:
            reply = _chat_openai_compatible_requests(api_key, provider, system_prompt, message)
            print("[Omnia] " + reply + "\n")
    except Exception as e:
        print(f"[Omnia] Chat failed: {e}")


def _build_model_config(provider: str) -> tuple[str, str]:
    print(f"[_build_model_config] provider={provider}")
    if provider in ("qianfan", "baiduqianfancodingplan"):
        # Qianfan Coding Plan - 实测可用：/v2/coding/chat/completions + messages 格式
        base_url = "https://qianfan.baidubce.com/v2/coding"
        url = f"{base_url}/chat/completions"
        model = "qianfan-code-latest"
        print(f"[_build_model_config] Using Qianfan Coding: url={url}, model={model}")
    elif provider == "kimi":
        # Kimi Coding API - 与 OpenClaw 配置一致
        url = "https://api.kimi.com/coding/v1/messages"
        model = "kimi-code"  # 使用 OpenClaw 相同的模型名
        print(f"[_build_model_config] Using Kimi Coding: url={url}, model={model}")
    else:
        url = "https://api.openai.com/v1/chat/completions"
        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        print(f"[_build_model_config] Using OpenAI default: url={url}, model={model}")
    return url, model


def _call_model_messages(api_key: str, provider: str, messages: list, tools: list | None = None) -> dict:
    """调用模型，支持 OpenAI 和 Anthropic 格式"""
    import requests

    # Kimi 使用 Anthropic Messages API 格式
    if provider == "kimi":
        model = os.environ.get("KIMI_MODEL", "K2.6-code-preview")
        return call_kimi_anthropic(api_key, messages, tools, model)
    
    # 其他 provider 使用 OpenAI 格式
    url, model = _build_model_config(provider)
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Omnia-Agent/1.0",
        "Accept": "application/json",
    }
    
    if provider in ("baiduqianfancodingplan", "qianfan"):
        # Qianfan Coding Plan - 使用 Bearer token + messages 格式
        headers["Authorization"] = f"Bearer {api_key}"
        
        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        
        print(f"[_call_model_messages] Qianfan chat with {len(messages)} messages")
    else:
        # Standard chat completions format
        headers["Authorization"] = f"Bearer {api_key}"
        payload: dict = {
            "model": model,
            "messages": messages,
        }
    
    if tools:
        payload["tools"] = tools
        print(f"[_call_model_messages] Tools included: {len(tools)} tools")
        print(f"[_call_model_messages] First tool: {tools[0]['function']['name'] if tools else 'N/A'}")
    else:
        print(f"[_call_model_messages] No tools passed")

    print(f"[_call_model_messages] POST {url}")
    print(f"[_call_model_messages] Headers: {list(headers.keys())}")
    response = requests.post(url, headers=headers, json=payload, timeout=300)

    print(f"[_call_model_messages] Response status: {response.status_code}")
    
    if response.status_code != 200:
        error_text = response.text
        print(f"[_call_model_messages] Error response: {error_text[:500]}")
        raise RuntimeError(f"API error {response.status_code}: {error_text}")

    data = response.json()
    print(f"[_call_model_messages] Response keys: {list(data.keys())}")
    
    return data


def _chat_openai_compatible_requests(api_key: str, provider: str, system_prompt: str, message: str) -> str:
    data = _call_model_messages(
        api_key,
        provider,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )
    # All providers use standard chat completions response format
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected response format: {data}")


def _chat_anthropic(api_key: str, system_prompt: str, message: str) -> None:
    try:
        import anthropic
    except ImportError:
        print("[Omnia] The 'anthropic' package is required. Run: pip install anthropic")
        return

    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        print("[Omnia] ", end="", flush=True)
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print("\n")
