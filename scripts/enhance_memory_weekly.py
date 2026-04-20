#!/usr/bin/env python3
"""
记忆增强脚本（每周运行）
从对话日志中推断更多 Habits、Timeline、Relations
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import re

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.memory_palace import MemoryPalace
from core.config import MEMORY_PALACE_DB

LOG_FILE = PROJECT_ROOT.parent / ".omnia" / "memory_enhance.log"

def log(msg: str):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    print(line, end="")
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except:
        pass

def enhance_timeline(mp: MemoryPalace):
    """从对话日志中提取重要事件"""
    logs = mp.recall_conversations(limit=5000)
    
    # 事件类型关键词
    event_patterns = {
        "项目启动": ["开始做", "启动", "新建项目", "开始开发", "开始写", "开始构建"],
        "错误修复": ["修复了", "解决了", "bug", "错误", "问题已解决", "修好了"],
        "里程碑": ["完成了", "实现了", "上线了", "做好了", "搞定了", "成功了"],
        "决策": ["决定", "选择", "采用", "确定", "同意", "确认", "最终方案"],
        "学习探索": ["学习了", "研究了", "探索了", "尝试了", "了解了", "发现"],
        "优化改进": ["优化了", "改进了", "重构了", "升级了", "更新了"],
    }
    
    new_events = []
    
    for log in logs:
        user_msg = log.get('user_message', '') or log.get('content', '')
        assistant_msg = log.get('assistant_message', '') or ''
        timestamp = log.get('timestamp', '')
        
        combined = f"{user_msg} {assistant_msg}"
        
        for event_type, keywords in event_patterns.items():
            for keyword in keywords:
                if keyword in combined:
                    # 提取事件描述
                    if keyword in user_msg:
                        desc = extract_event_context(user_msg, keyword)
                        if desc:
                            new_events.append({
                                'timestamp': timestamp,
                                'event_type': event_type,
                                'description': desc,
                            })
                    break
    
    # 去重并添加到 Timeline
    existing = mp.recall_timeline()
    existing_descs = {e.get('content', '') for e in existing}
    
    added = 0
    for event in new_events:
        if event['description'] not in existing_descs:
            mp.remember_timeline(
                event_type=event['event_type'],
                content=event['description'],
                metadata={'source': 'auto_enhance', 'original_timestamp': event['timestamp']}
            )
            added += 1
    
    return added

def extract_event_context(text: str, keyword: str) -> str:
    """从文本中提取事件上下文"""
    sentences = re.split(r'[。！？\n]', text)
    for sentence in sentences:
        if keyword in sentence:
            cleaned = sentence.strip()
            if len(cleaned) > 10 and len(cleaned) < 200:
                return cleaned
    return ""

def enhance_habits(mp: MemoryPalace):
    """从对话模式中推断习惯"""
    logs = mp.recall_conversations(limit=1000)
    
    # 分析用户消息中的关键词频率
    user_messages = [log.get('user_message', '') or log.get('content', '') for log in logs]
    all_text = ' '.join(user_messages)
    
    # 工作习惯关键词
    habit_keywords = {
        '编程开发': ['代码', '函数', '调试', 'bug', '编程', '开发', '写代码', '运行', '测试'],
        '项目管理': ['项目', '任务', '计划', '进度', '需求', '功能'],
        '学习研究': ['学习', '研究', '文档', '教程', '探索', '尝试'],
        '运维部署': ['服务器', '部署', '配置', '监控', '日志', 'nginx', 'docker'],
        '内容创作': ['文章', '博客', '写作', '内容', '标题', '发布'],
    }
    
    detected_habits = []
    
    for habit_name, keywords in habit_keywords.items():
        count = sum(all_text.count(kw) for kw in keywords)
        if count >= 10:
            detected_habits.append((habit_name, count))
    
    # 检查是否已存在
    existing_habits = mp.recall_habits()
    existing_names = {h.get('pattern', '') for h in existing_habits}
    
    added = 0
    for habit_name, count in sorted(detected_habits, key=lambda x: -x[1]):
        if habit_name not in existing_names:
            mp.remember_habit(
                domain='工作习惯',
                pattern=habit_name,
                evidence=f'关键词出现 {count} 次',
                certainty=min(0.9, count / 100)
            )
            added += 1
    
    return added

def main():
    log("=== 开始记忆增强 ===")
    
    mp = MemoryPalace(db_path=str(MEMORY_PALACE_DB))
    
    # 1. 增强 Timeline
    log("📅 增强 Timeline...")
    timeline_added = enhance_timeline(mp)
    log(f"   新增 {timeline_added} 条时间线事件")
    
    # 2. 增强 Habits
    log("🔄 增强 Habits...")
    habits_added = enhance_habits(mp)
    log(f"   新增 {habits_added} 条习惯")
    
    # 统计
    facts = mp.recall_facts()
    habits = mp.recall_habits()
    timeline = mp.recall_timeline()
    logs = mp.recall_conversations()
    
    log("\n📊 增强后统计：")
    log(f"   Facts: {len(facts)}")
    log(f"   Habits: {len(habits)}")
    log(f"   Timeline: {len(timeline)}")
    log(f"   Conversation Logs: {len(logs)}")
    
    log("\n✅ 记忆增强完成！")

if __name__ == '__main__':
    main()
