#!/usr/bin/env python3
"""
记忆增强脚本

从现有对话中提取：
1. Habits - 从对话模式中推断习惯
2. Timeline - 从对话中提取重要事件
3. Relations - 从 Facts 中推断关系

运行方式：
    python3 scripts/enhance_memory.py
"""

import sys
from pathlib import Path
import sqlite3
import re
from collections import Counter
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 使用统一的数据库路径
DB_PATH = Path.home() / ".omnia" / "memory_palace.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def extract_habits_from_conversations():
    """从对话中推断习惯"""
    print("\n=== 提取习惯 ===")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取最近的对话
    cursor.execute("""
        SELECT content, content, created_at 
        FROM conversation_logs 
        ORDER BY created_at DESC 
        LIMIT 1000
    """)
    
    conversations = cursor.fetchall()
    conn.close()
    
    # 分析对话模式
    domain_keywords = {
        "coding": ["代码", "函数", "调试", "bug", "编程", "开发", "python", "javascript", "git"],
        "communication": ["消息", "回复", "发送", "通知", "飞书", "微信"],
        "workflow": ["任务", "计划", "安排", "会议", "日程"],
        "learning": ["学习", "教程", "文档", "研究", "探索"],
        "creativity": ["设计", "创意", "想法", "构思", "创作"],
    }
    
    domain_counts = Counter()
    
    for conv in conversations:
        text = f"{conv['content']} {conv['content']}"
        
        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    domain_counts[domain] += 1
    
    # 存储习惯
    conn = get_connection()
    cursor = conn.cursor()
    habits_added = 0
    
    for domain, count in domain_counts.most_common(5):
        if count > 10:  # 至少出现10次才算习惯
            pattern = f"频繁进行{domain}相关活动"
            evidence = f"在最近1000条对话中出现了{count}次{domain}相关关键词"
            certainty = min(0.9, count / 100)
            
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM habits WHERE domain = ? AND pattern = ?
            """, (domain, pattern))
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute("""
                    UPDATE habits 
                    SET certainty = ?, last_observed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (certainty, existing['id']))
            else:
                # 插入
                cursor.execute("""
                    INSERT INTO habits (domain, pattern, evidence, certainty)
                    VALUES (?, ?, ?, ?)
                """, (domain, pattern, evidence, certainty))
            
            print(f"  ✅ {domain}: {pattern} (出现{count}次)")
            habits_added += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n共提取 {habits_added} 个习惯")
    return habits_added


def extract_events_from_conversations():
    """从对话中提取重要事件"""
    print("\n=== 提取事件 ===")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取对话
    cursor.execute("""
        SELECT content, content, created_at 
        FROM conversation_logs 
        ORDER BY created_at DESC 
        LIMIT 500
    """)
    
    conversations = cursor.fetchall()
    
    # 事件类型关键词
    event_patterns = {
        "milestone": ["完成了", "实现了", "上线了", "发布了", "建成了", "做好了"],
        "decision": ["决定", "选择", "采用", "确定", "同意", "确认"],
        "error": ["错误", "失败", "bug", "崩溃", "异常", "问题"],
        "achievement": ["成功", "解决", "优化", "改进", "提升"],
        "project_start": ["开始做", "启动", "新建项目", "开始开发"],
    }
    
    events_added = 0
    
    for conv in conversations:
        text = f"{conv['content']} {conv['content']}"
        date = conv['created_at'][:10] if conv['created_at'] else datetime.now().strftime("%Y-%m-%d")
        
        for event_type, keywords in event_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    # 提取标题
                    title = text[:50].replace("\n", " ")
                    
                    try:
                        cursor.execute("""
                            INSERT INTO timeline (event_date, event_type, title, description)
                            VALUES (?, ?, ?, ?)
                        """, (date, event_type, f"{keyword}: {title}", text[:200]))
                        events_added += 1
                        break  # 一个对话只记录一个事件
                    except:
                        pass
    
    conn.commit()
    conn.close()
    
    print(f"共提取 {events_added} 个事件")
    return events_added


def extract_relations_from_facts():
    """从 Facts 中推断关系"""
    print("\n=== 推断关系 ===")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取所有 facts
    cursor.execute("SELECT * FROM facts")
    facts = cursor.fetchall()
    
    relations_added = 0
    
    for fact in facts:
        category = fact['category']
        key = fact['key']
        value = fact['value']
        
        # 从 user 类型的 fact 推断关系
        if category == "user":
            cursor.execute("""
                INSERT INTO relations (subject, predicate, object, context)
                VALUES (?, ?, ?, ?)
            """, ("用户", "是", value, key))
            relations_added += 1
        
        # 从 project 类型的 fact 推断关系
        elif category == "project":
            cursor.execute("""
                INSERT INTO relations (subject, predicate, object, context)
                VALUES (?, ?, ?, ?)
            """, ("用户", "正在进行", key, value))
            relations_added += 1
        
        # 从 preference 类型的 fact 推断关系
        elif category == "preference":
            cursor.execute("""
                INSERT INTO relations (subject, predicate, object, context)
                VALUES (?, ?, ?, ?)
            """, ("用户", "喜欢", value, key))
            relations_added += 1
    
    conn.commit()
    conn.close()
    
    print(f"共推断 {relations_added} 个关系")
    return relations_added


def get_stats():
    """获取统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    try:
        cursor.execute("SELECT COUNT(*) FROM facts")
        stats['facts'] = cursor.fetchone()[0]
    except:
        stats['facts'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM relations")
        stats['relations'] = cursor.fetchone()[0]
    except:
        stats['relations'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM habits")
        stats['habits'] = cursor.fetchone()[0]
    except:
        stats['habits'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM timeline")
        stats['timeline'] = cursor.fetchone()[0]
    except:
        stats['timeline'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM conversation_logs")
        stats['conversations'] = cursor.fetchone()[0]
    except:
        stats['conversations'] = 0
    
    conn.close()
    
    return stats


def main():
    print("=" * 60)
    print("Omnia 记忆增强器")
    print("从现有对话中推断更多 Habits、Timeline、Relations")
    print("=" * 60)
    
    # 统计初始状态
    print("\n=== 初始统计 ===")
    stats_before = get_stats()
    for key, value in stats_before.items():
        print(f"  {key}: {value}")
    
    # 执行增强
    habits_added = extract_habits_from_conversations()
    events_added = extract_events_from_conversations()
    relations_added = extract_relations_from_facts()
    
    # 统计最终状态
    print("\n=== 最终统计 ===")
    stats_after = get_stats()
    for key, value in stats_after.items():
        before = stats_before.get(key, 0)
        diff = value - before
        print(f"  {key}: {value} (+{diff})")
    
    print("\n" + "=" * 60)
    print("✅ 记忆增强完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
