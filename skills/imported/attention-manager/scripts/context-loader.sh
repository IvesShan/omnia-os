#!/bin/bash
# Attention Manager - 动态上下文加载器
# 根据消息主题，智能加载相关记忆和skills

TOPIC="$1"
MEMORY_DIR="$HOME//home/shan/omnia-os/memory_topics"
SKILLS_DIR="$HOME//home/shan/omnia-os/skills"

# 初始化加载列表
MEMORY_TO_LOAD=""
SKILLS_TO_LOAD=""
ESTIMATED_TOKENS=0

case "$TOPIC" in
    "课程开发"|"课程"|"讲义"|"课件"|"day"|"无人机")
        MEMORY_TO_LOAD="课程开发,项目进度"
        SKILLS_TO_LOAD="course-dev-tracker,auto-skill-creator,user-behavior-analyzer"
        ESTIMATED_TOKENS=4000
        ;;
        
    "系统配置"|"配置"|"API"|"备份"|"cron"|"skill")
        MEMORY_TO_LOAD="系统配置,工具技能"
        SKILLS_TO_LOAD="topic-memory-system,file-delivery,self-inspector"
        ESTIMATED_TOKENS=3000
        ;;
        
    "进化"|"优化"|"变强"|"升级"|"自动"|"无限.0")
        MEMORY_TO_LOAD="进化优化,用户偏好"
        SKILLS_TO_LOAD="self-improving,auto-skill-creator,active-evolution-proposer"
        ESTIMATED_TOKENS=3000
        ;;
        
    "股东"|"协议"|"合同"|"法律"|"债务")
        MEMORY_TO_LOAD="未分类"
        SKILLS_TO_LOAD="file-delivery"
        ESTIMATED_TOKENS=2000
        ;;
        
    "心跳"|"HEARTBEAT"|"定时")
        MEMORY_TO_LOAD=""
        SKILLS_TO_LOAD=""
        ESTIMATED_TOKENS=500
        ;;
        
    *)
        # 默认加载最近记忆
        MEMORY_TO_LOAD="最近2天"
        SKILLS_TO_LOAD="infinite-butler"
        ESTIMATED_TOKENS=6000
        ;;
esac

# 输出加载计划
echo "{"
echo "  \"topic\": \"$TOPIC\","
echo "  \"memory_topics\": \"$MEMORY_TO_LOAD\","
echo "  \"skills\": \"$SKILLS_TO_LOAD\","
echo "  \"estimated_tokens\": $ESTIMATED_TOKENS,"
echo "  \"savings_vs_full_load\": $((16000 - ESTIMATED_TOKENS))"
echo "}"

# 记录日志
LOG_FILE="$HOME/.openclaw/logs/context-loader.log"
echo "[$(date '+%H:%M:%S')] $TOPIC | $ESTIMATED_TOKENS tokens | 节省$((16000 - ESTIMATED_TOKENS)) tokens" >> "$LOG_FILE"
