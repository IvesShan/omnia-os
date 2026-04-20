#!/bin/bash
# Perception Monitor - 时间感知追踪器
# 跟踪时间相关事件：上次对话、截止时间、定时任务

STATE_FILE="$HOME/.openclaw/protect/time-perception.json"
DATE=$(date '+%Y-%m-%d %H:%M:%S')
CURRENT_TIME=$(date +%s)

# 初始化状态文件
init_state() {
    if [ ! -f "$STATE_FILE" ]; then
        cat > "$STATE_FILE" <> EOF
{
  "last_conversation": "$CURRENT_TIME",
  "daily_check": false,
  "weekly_report": false,
  "milestones": [
    {"name": "Day 04完成", "deadline": "2026-03-10", "status": "pending"},
    {"name": "M2里程碑", "deadline": "2026-03-18", "status": "in_progress"}
  ]
}
EOF
    fi
}

# 更新上次对话时间
update_last_conversation() {
    if [ -f "$STATE_FILE" ]; then
        # 使用sed更新时间戳
        sed -i "s/\"last_conversation\": [0-9]*/\"last_conversation\": $CURRENT_TIME/" "$STATE_FILE"
    fi
}

# 计算时间差
calculate_gap() {
    LAST_CONV=$(grep -o '"last_conversation": [0-9]*' "$STATE_FILE" | awk '{print $2}')
    GAP=$((CURRENT_TIME - LAST_CONV))
    GAP_HOURS=$((GAP / 3600))
    GAP_DAYS=$((GAP / 86400))
    
    echo "  \"time_gap_seconds\": $GAP,"
    echo "  \"time_gap_hours\": $GAP_HOURS,"
    echo "  \"time_gap_days\": $GAP_DAYS,"
}

# 检查里程碑
check_milestones() {
    echo "  \"milestones\": ["
    
    # 简单解析JSON，检查截止日
    grep -A2 '"name":' "$STATE_FILE" | grep -E '"name"|"deadline"' | paste - - | while read line; do
        name=$(echo "$line" | grep -o '"name": "[^"]*"' | cut -d'"' -f4)
        deadline=$(echo "$line" | grep -o '"deadline": "[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$name" ] && [ -n "$deadline" ]; then
            DEADLINE_EPOCH=$(date -d "$deadline" +%s 2>/dev/null || echo "0")
            if [ $DEADLINE_EPOCH -gt 0 ]; then
                DAYS_LEFT=$(( (DEADLINE_EPOCH - CURRENT_TIME) / 86400 ))
                echo "    {\"name\": \"$name\", \"days_left\": $DAYS_LEFT},"
            fi
        fi
    done
    
    echo "  ]"
}

# 主检查
init_state

echo "{"
echo "  \"current_time\": \"$DATE\","
echo "  \"current_timestamp\": $CURRENT_TIME,"

calculate_gap
check_milestones

echo "}"

# 更新对话时间
update_last_conversation
