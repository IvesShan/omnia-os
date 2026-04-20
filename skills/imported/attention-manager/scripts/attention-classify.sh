#!/bin/bash
# Attention Manager - 消息优先级分类器
# 分析传入消息，返回优先级等级

MESSAGE="$1"
PRIORITY="normal"
REASON=""

# 检查CRITICAL级别
if echo "$MESSAGE" | grep -qiE "(无限|@无限|你.*吗|紧急|故障|出错|删除了|断联|坏了|救命)"; then
    PRIORITY="critical"
    REASON="直接提及或紧急关键词"
    
# 检查HIGH级别  
elif echo "$MESSAGE" | grep -qiE "(检查|查看|生成|创建|开发|进度|课程|协议|skill|配置|API|备份|优化|进化)"; then
    PRIORITY="high"
    REASON="包含动作指令或高优先级主题"
    
# 检查LOW级别
elif echo "$MESSAGE" | grep -qiE "^(HEARTBEAT|好的|收到|嗯|哦|谢谢|👍|ok|okk)$"; then
    PRIORITY="low"
    REASON="简短确认或无实质内容"
    
# 检查是否是群聊未提及我
elif echo "$MESSAGE" | grep -qvE "(无限|你|帮忙|请|帮我)"; then
    # 如果是群聊上下文但没有提及我
    if [ -n "$CHANNEL_TYPE" ] && [ "$CHANNEL_TYPE" = "group" ]; then
        PRIORITY="low"
        REASON="群聊中未提及我"
    fi
fi

# 输出结果
echo "{"
echo "  \"priority\": \"$PRIORITY\","
echo "  \"reason\": \"$REASON\","
echo "  \"message_preview\": \"$(echo "$MESSAGE" | cut -c1-50)...\""
echo "}"

# 记录分类日志
LOG_FILE="$HOME/.openclaw/logs/attention-classify.log"
echo "[$(date '+%H:%M:%S')] $PRIORITY | $REASON | ${MESSAGE:0:30}..." >> "$LOG_FILE"
