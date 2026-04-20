#!/bin/bash
# Attention Manager - Token预算监控器
# 监控token使用情况，触发总结重置

SESSION_TOKENS=${1:-0}
THRESHOLD_ALERT=200000
THRESHOLD_CRITICAL=250000
MAX_TOKENS=262144

# 计算使用率
USAGE_PERCENT=$((SESSION_TOKENS * 100 / MAX_TOKENS))

# 判断状态
if [ $SESSION_TOKENS -gt $THRESHOLD_CRITICAL ]; then
    STATUS="CRITICAL"
    ACTION="立即强制总结，截断历史上下文"
    COLOR="🔴"
elif [ $SESSION_TOKENS -gt $THRESHOLD_ALERT ]; then
    STATUS="WARNING"
    ACTION="建议主动总结，重置上下文"
    COLOR="🟡"
elif [ $USAGE_PERCENT -gt 50 ]; then
    STATUS="ELEVATED"
    ACTION="监控中，准备总结"
    COLOR="🟠"
else
    STATUS="NORMAL"
    ACTION="正常运行"
    COLOR="🟢"
fi

# 输出状态
echo "{"
echo "  \"status\": \"$STATUS\","
echo "  \"tokens_used\": $SESSION_TOKENS,"
echo "  \"tokens_remaining\": $((MAX_TOKENS - SESSION_TOKENS)),"
echo "  \"usage_percent\": $USAGE_PERCENT,"
echo "  \"action\": \"$ACTION\","
echo "  \"should_summarize\": $([ "$STATUS" = "WARNING" ] || [ "$STATUS" = "CRITICAL" ] && echo "true" || echo "false")"
echo "}"

# 如果是警告或严重状态，输出到stderr以便捕获
if [ "$STATUS" = "WARNING" ] || [ "$STATUS" = "CRITICAL" ]; then
    echo "${COLOR} Attention: Token usage ${USAGE_PERCENT}% - $ACTION" >&2
fi

# 记录日志
LOG_FILE="$HOME/.openclaw/logs/token-budget.log"
echo "[$(date '+%H:%M:%S')] $STATUS | $SESSION_TOKENS/$MAX_TOKENS ($USAGE_PERCENT%)" >> "$LOG_FILE"
