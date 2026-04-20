#!/usr/bin/env python3
"""
Auto Memory Extraction - 自动从 Verbatim 提取记忆到 Memory Palace

这个脚本会：
1. 从 verbatim_db 读取最新的对话
2. 使用 LLM 提取重要信息
3. 存储到 memory_palace.db

建议 cron 配置：
  0 */4 * * * /usr/bin/python3 /home/shan/.openclaw/workspace/omnia-os/scripts/auto_memory_extraction.py >> /tmp/memory_extraction.log 2>&1
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.memory_palace.memory_palace import MemoryPalace

# 配置
WORKSPACE = PROJECT_ROOT.parent
VERBATIM_DB = WORKSPACE / "verbatim_db"
MEMORY_PALACE_DB = WORKSPACE / ".omnia" / "memory_palace.db"
LAST_EXTRACTION_FILE = WORKSPACE / ".omnia" / ".last_memory_extraction"
LOG_FILE = WORKSPACE / ".omnia" / "memory_extraction.log"

# API 配置
API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
if not API_KEY:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("MOONSHOT_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip().strip('"')
                break


def log(msg: str):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    print(line, end="")
    try:
        LAST_EXTRACTION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except:
        pass


def get_last_extraction_time() -> datetime:
    """获取上次提取时间"""
    if LAST_EXTRACTION_FILE.exists():
        try:
            timestamp = float(LAST_EXTRACTION_FILE.read_text().strip())
            return datetime.fromtimestamp(timestamp)
        except:
            pass
    # 默认：4小时前
    return datetime.now() - timedelta(hours=4)


def save_extraction_time():
    """保存提取时间"""
    LAST_EXTRACTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_EXTRACTION_FILE.write_text(str(datetime.now().timestamp()))


def load_verbatim_messages(since: datetime) -> list:
    """从 verbatim 加载指定时间后的消息"""
    messages = []
    embeddings_dir = VERBATIM_DB / "embeddings"
    
    if not embeddings_dir.exists():
        return []
    
    for date_file in sorted(embeddings_dir.glob("*.json"), reverse=True):
        try:
            day_data = json.loads(date_file.read_text(encoding="utf-8"))
            for msg in day_data.get("messages", []):
                # 解析时间戳
                msg_time_str = msg.get("timestamp", "")
                try:
                    msg_time = datetime.fromisoformat(msg_time_str.replace("Z", "+00:00"))
                    if msg_time.replace(tzinfo=None) > since:
                        messages.append(msg)
                except:
                    # 如果时间解析失败，包含这条消息
                    messages.append(msg)
        except Exception as e:
            log(f"Error reading {date_file}: {e}")
    
    return messages


def extract_memories_with_llm(messages: list) -> dict:
    """使用 LLM 从消息中提取记忆"""
    if not messages:
        return {"facts": [], "habits": [], "relations": [], "timeline": []}
    
    if not API_KEY:
        log("⚠️ No API key, using rule-based extraction")
        return extract_memories_rules(messages)
    
    # 构建提示
    conversation_text = []
    for msg in messages[-50:]:  # 最多50条
        msg_type = msg.get("type", "unknown")
        content = msg.get("content", "")[:500]
        if content:
            conversation_text.append(f"[{msg_type}] {content}")
    
    if not conversation_text:
        return {"facts": [], "habits": [], "relations": [], "timeline": []}
    
    prompt = f"""分析以下对话，提取重要的记忆信息。

对话内容：
{chr(10).join(conversation_text)}

请提取：
1. **重要事实**（用户偏好、项目信息、决策、配置等）
2. **用户习惯**（工作模式、使用模式等）
3. **重要关系**（人、项目、概念之间的关联）
4. **时间线事件**（重要里程碑、决策点）

输出 JSON 格式：
{{
  "facts": [
    {{"category": "preference|project|decision|config", "key": "...", "value": "..."}}
  ],
  "habits": [
    {{"domain": "work|coding|communication", "pattern": "...", "evidence": "..."}}
  ],
  "relations": [
    {{"subject": "...", "predicate": "...", "object": "...", "context": "..."}}
  ],
  "timeline": [
    {{"event_type": "milestone|decision|discovery", "title": "...", "description": "..."}}
  ]
}}

注意：
- 只提取重要、有价值的信息
- 忽略闲聊和临时性内容
- 保持简洁准确"""

    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "kimi-k2-0711-preview",
            "messages": [
                {"role": "system", "content": "你是记忆提取专家，从对话中提取结构化信息。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }
        
        resp = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        
        content = resp.json()["choices"][0]["message"]["content"]
        
        # 提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        
        return {"facts": [], "habits": [], "relations": [], "timeline": []}
        
    except Exception as e:
        log(f"LLM extraction failed: {e}")
        return extract_memories_rules(messages)


def extract_memories_rules(messages: list) -> dict:
    """基于规则的记忆提取（fallback）"""
    import re
    
    facts = []
    habits = []
    relations = []
    timeline = []
    
    # 合并所有消息
    all_text = "\n".join(m.get("content", "") for m in messages)
    
    # 提取偏好
    preference_patterns = [
        r"我(喜欢|偏好|想要|希望)([^\n。]{5,50})",
        r"我的([^\s]+)是([^\n。]{5,50})",
    ]
    
    for pattern in preference_patterns:
        matches = re.findall(pattern, all_text)
        for match in matches:
            if isinstance(match, tuple):
                key = match[0]
                value = match[1] if len(match) > 1 else ""
            else:
                key = "偏好"
                value = match
            
            facts.append({
                "category": "preference",
                "key": key,
                "value": value
            })
    
    # 提取项目信息
    project_keywords = ["项目", "开发", "正在做", "工作"]
    for kw in project_keywords:
        if kw in all_text:
            # 简单提取
            sentences = all_text.split("。")
            for sent in sentences:
                if kw in sent and len(sent) > 10:
                    facts.append({
                        "category": "project",
                        "key": kw,
                        "value": sent[:100]
                    })
                    break
    
    # 提取决策
    decision_keywords = ["决定", "选择", "采用", "确定"]
    for kw in decision_keywords:
        if kw in all_text:
            timeline.append({
                "event_type": "decision",
                "title": f"用户{kw}",
                "description": f"在对话中做出{kw}"
            })
            break
    
    return {
        "facts": facts[:10],  # 限制数量
        "habits": habits[:5],
        "relations": relations[:5],
        "timeline": timeline[:5]
    }


def store_memories(data: dict):
    """存储记忆到 Memory Palace"""
    mp = MemoryPalace(str(MEMORY_PALACE_DB))
    mp.initialize()
    
    stats = {"facts": 0, "habits": 0, "relations": 0, "timeline": 0}
    
    # 存储 facts
    for fact in data.get("facts", []):
        try:
            mp.remember_fact(
                category=fact.get("category", "general"),
                key=fact.get("key", ""),
                value=fact.get("value", ""),
                source="auto_extraction",
                strength=0.8
            )
            stats["facts"] += 1
        except Exception as e:
            log(f"Failed to store fact: {e}")
    
    # 存储 habits
    for habit in data.get("habits", []):
        try:
            mp.observe_habit(
                domain=habit.get("domain", "general"),
                pattern=habit.get("pattern", ""),
                evidence=habit.get("evidence", ""),
                certainty=0.7
            )
            stats["habits"] += 1
        except Exception as e:
            log(f"Failed to store habit: {e}")
    
    # 存储 relations
    for relation in data.get("relations", []):
        try:
            mp.relate(
                subject=relation.get("subject", ""),
                predicate=relation.get("predicate", ""),
                object=relation.get("object", ""),
                context=relation.get("context", ""),
                strength=0.8
            )
            stats["relations"] += 1
        except Exception as e:
            log(f"Failed to store relation: {e}")
    
    # 存储 timeline
    for event in data.get("timeline", []):
        try:
            mp.record_event(
                event_date=datetime.now().date(),
                event_type=event.get("event_type", "milestone"),
                title=event.get("title", ""),
                description=event.get("description", ""),
                tags=["auto_extracted"]
            )
            stats["timeline"] += 1
        except Exception as e:
            log(f"Failed to store timeline: {e}")
    
    return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Memory Extraction")
    parser.add_argument("--since", help="提取指定时间后的消息 (YYYY-MM-DD HH:MM)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()
    
    log("=== 开始记忆提取 ===")
    
    # 获取时间范围
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d %H:%M")
    else:
        since = get_last_extraction_time()
    
    log(f"提取时间范围: {since} 之后")
    
    # 加载消息
    messages = load_verbatim_messages(since)
    log(f"找到 {len(messages)} 条新消息")
    
    if not messages:
        log("无需提取")
        return
    
    # 提取记忆
    log("正在提取记忆...")
    memories = extract_memories_with_llm(messages)
    
    log(f"提取结果: {len(memories.get('facts', []))} facts, "
        f"{len(memories.get('habits', []))} habits, "
        f"{len(memories.get('relations', []))} relations, "
        f"{len(memories.get('timeline', []))} timeline")
    
    if args.dry_run:
        log("=== 预览模式 ===")
        print(json.dumps(memories, ensure_ascii=False, indent=2))
        return
    
    # 存储记忆
    log("正在存储记忆...")
    stats = store_memories(memories)
    
    log(f"存储完成: {stats}")
    
    # 保存提取时间
    save_extraction_time()
    
    log("=== 记忆提取完成 ===")


if __name__ == "__main__":
    main()
