#!/usr/bin/env python3
"""
Omnia 记忆巩固脚本 - 每日自动晋升
适配 Omnia 的记忆系统架构

运行时间: 每天 03:00
功能:
  1. 分析昨天的事件日志
  2. 提取重要内容（决策、教训、关键信息）
  3. 分类到对应记忆层级
  4. 更新 Memory Palace

使用:
  python3 scripts/omnia_consolidate.py [--dry-run]
"""

import os
import re
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Omnia 路径
OMNIA_ROOT = Path(__file__).parent.parent
MEMORY_DIR = OMNIA_ROOT / "seeds" / "omnia" / "memory"

# 项目关键词映射
PROJECT_KEYWORDS = {
    "miaoxiujiang": ["喵修匠", "维修", "工单", "商家", "发货", "miaoxiujiang"],
    "dongjidi": ["懂机帝", "社区", "内容", "发布", "dongjidi"],
    "omnia": ["omnia", "Omnia", "agent", "记忆", "HUD"],
    "system": ["openclaw", "OpenClaw", "系统", "配置", "cron"]
}

# 晋升评分
SCORE_WEIGHTS = {
    "decision": 0.30,
    "lesson": 0.25,
    "milestone": 0.20,
    "preference": 0.15,
    "context": 0.10
}

# 阈值
FACT_THRESHOLD = 0.35
RELATION_THRESHOLD = 0.30
HABIT_THRESHOLD = 0.25


def load_memory_palace() -> Dict:
    """加载记忆宫殿数据"""
    db_path = MEMORY_DIR / "palace.json"
    if db_path.exists():
        return json.loads(db_path.read_text(encoding="utf-8"))
    return {
        "facts": [],
        "relations": [],
        "habits": [],
        "timeline": [],
        "last_updated": None
    }


def save_memory_palace(data: Dict):
    """保存记忆宫殿数据"""
    db_path = MEMORY_DIR / "palace.json"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    db_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_memories_from_text(text: str) -> List[Dict]:
    """从文本提取记忆项"""
    items = []
    lines = text.split("\n")
    
    patterns = {
        "decision": [r"决策[：:]", r"决定[：:]", r"选择[：:]", r"下一步[：:]"],
        "lesson": [r"教训[：:]", r"注意[：:]", r"问题[：:]", r"修复[：:]", r"错误[：:]"],
        "milestone": [r"完成[：:]", r"✅", r"上线[：:]", r"成功[：:]"],
        "preference": [r"偏好[：:]", r"习惯[：:]", r"风格[：:]"]
    }
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        item = None
        for item_type, pats in patterns.items():
            for pat in pats:
                if re.search(pat, line, re.IGNORECASE):
                    item = {
                        "type": item_type,
                        "content": line,
                        "score": SCORE_WEIGHTS[item_type],
                        "line": i
                    }
                    break
            if item:
                break
        
        if item:
            items.append(item)
    
    return items


def classify_item(item: Dict) -> str:
    """分类记忆项到项目"""
    content = item.get("content", "").lower()
    
    for project, keywords in PROJECT_KEYWORDS.items():
        if any(kw.lower() in content for kw in keywords):
            return project
    return "general"


def promote_memories(items: List[Dict], palace: Dict) -> Dict:
    """晋升记忆到宫殿"""
    new_facts = []
    new_habits = []
    new_timeline = []
    
    for item in items:
        score = item.get("score", 0.3)
        item_type = item.get("type", "context")
        content = item.get("content", "")
        project = classify_item(item)
        
        # 添加时间戳和项目标签
        entry = {
            "content": content,
            "type": item_type,
            "project": project,
            "score": score,
            "created_at": datetime.now().isoformat()
        }
        
        if score >= FACT_THRESHOLD:
            entry["category"] = "fact"
            new_facts.append(entry)
        elif score >= HABIT_THRESHOLD:
            entry["category"] = "habit"
            new_habits.append(entry)
        
        # 所有内容都加入时间线
        new_timeline.append(entry)
    
    # 合并到宫殿
    palace["facts"].extend(new_facts)
    palace["habits"].extend(new_habits)
    palace["timeline"].extend(new_timeline)
    
    # 去重
    seen = set()
    for key in ["facts", "habits", "timeline"]:
        unique = []
        for item in palace[key]:
            content = item.get("content", "")
            if content not in seen:
                seen.add(content)
                unique.append(item)
        palace[key] = unique
    
    # 限制大小
    palace["facts"] = palace["facts"][-500:]
    palace["habits"] = palace["habits"][-100:]
    palace["timeline"] = palace["timeline"][-1000:]
    
    return {
        "new_facts": len(new_facts),
        "new_habits": len(new_habits),
        "new_timeline": len(new_timeline)
    }


def generate_dream_report(stats: Dict, items: List[Dict]) -> str:
    """生成梦境报告"""
    report = f"""# Omnia 梦境报告 - {datetime.now().strftime("%Y-%m-%d")}

## 晋升统计

| 类别 | 新增数量 |
|------|---------|
| 事实 | {stats['new_facts']} |
| 习惯 | {stats['new_habits']} |
| 时间线 | {stats['new_timeline']} |

## 新增事实
"""
    for item in items:
        if item.get("score", 0) >= FACT_THRESHOLD:
            report += f"- [{item['type']}] {item['content']}\n"
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Omnia 记忆巩固")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--input", help="输入文本文件")
    args = parser.parse_args()
    
    print("[Omnia Dream] 开始记忆巩固...")
    
    # 加载记忆宫殿
    palace = load_memory_palace()
    print(f"[Omnia Dream] 当前记忆: {len(palace.get('facts', []))} 事实, {len(palace.get('habits', []))} 习惯")
    
    # 提取记忆
    items = []
    
    if args.input:
        input_path = Path(args.input)
        if input_path.exists():
            text = input_path.read_text(encoding="utf-8")
            items = extract_memories_from_text(text)
    
    print(f"[Omnia Dream] 发现 {len(items)} 个候选项目")
    
    if not items:
        print("[Omnia Dream] 无需晋升")
        return
    
    # 晋升记忆
    stats = promote_memories(items, palace)
    
    print(f"[Omnia Dream] 晋升: {stats['new_facts']} 事实, {stats['new_habits']} 习惯")
    
    if not args.dry_run:
        save_memory_palace(palace)
        print("[Omnia Dream] 记忆宫殿已更新")
        
        # 生成报告
        report = generate_dream_report(stats, items)
        report_path = MEMORY_DIR / f"dream_{datetime.now().strftime('%Y-%m-%d')}.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"[Omnia Dream] 报告已保存")
    else:
        print("\n[Omnia Dream] === 预览模式 ===")
        report = generate_dream_report(stats, items)
        print(report)


if __name__ == "__main__":
    main()
