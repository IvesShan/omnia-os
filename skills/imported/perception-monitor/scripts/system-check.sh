#!/bin/bash
# Perception Monitor - 系统状态检查器
# 检查API、磁盘、网络等系统状态

LOG_FILE="$HOME/.openclaw/logs/system-status.log"
ALERT_FILE="$HOME/.openclaw/protect/system-alerts.json"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 检查磁盘空间
check_disk() {
    DISK_USAGE=$(df -h "$HOME" | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -gt 95 ]; then
        STATUS="CRITICAL"
        MESSAGE="磁盘空间严重不足: ${DISK_USAGE}%"
    elif [ "$DISK_USAGE" -gt 85 ]; then
        STATUS="WARNING"
        MESSAGE="磁盘空间不足: ${DISK_USAGE}%"
    elif [ "$DISK_USAGE" -gt 70 ]; then
        STATUS="ELEVATED"
        MESSAGE="磁盘空间使用较高: ${DISK_USAGE}%"
    else
        STATUS="NORMAL"
        MESSAGE="磁盘空间正常: ${DISK_USAGE}%"
    fi
    
    echo "  \"disk\": {\"usage\": $DISK_USAGE, \"status\": \"$STATUS\", \"message\": \"$MESSAGE\"},"
    
    # 记录警报
    if [ "$STATUS" != "NORMAL" ]; then
        echo "{\"time\": \"$DATE\", \"type\": \"disk\", \"level\": \"$STATUS\", \"message\": \"$MESSAGE\"}" >> "$ALERT_FILE"
    fi
}

# 检查API配置
check_api() {
    CONFIG_FILE="$HOME/.openclaw/openclaw.json"
    
    if [ -f "$CONFIG_FILE" ]; then
        if grep -q "kimi\|openai" "$CONFIG_FILE" 2>/dev/null; then
            STATUS="NORMAL"
            MESSAGE="API配置正常"
        else
            STATUS="WARNING"
            MESSAGE="API配置可能不完整"
        fi
    else
        STATUS="CRITICAL"
        MESSAGE="配置文件不存在"
    fi
    
    echo "  \"api\": {\"status\": \"$STATUS\", \"message\": \"$MESSAGE\"},"
    
    if [ "$STATUS" != "NORMAL" ]; then
        echo "{\"time\": \"$DATE\", \"type\": \"api\", \"level\": \"$STATUS\", \"message\": \"$MESSAGE\"}" >> "$ALERT_FILE"
    fi
}

# 检查备份状态
check_backup() {
    BACKUP_COUNT=$(ls -1 "$HOME/.openclaw/backup/auto" 2>/dev/null | wc -l)
    LATEST_BACKUP=$(ls -1t "$HOME/.openclaw/backup/auto" 2>/dev/null | head -1)
    
    if [ $BACKUP_COUNT -eq 0 ]; then
        STATUS="WARNING"
        MESSAGE="无备份记录"
    elif [ -z "$LATEST_BACKUP" ]; then
        STATUS="WARNING"
        MESSAGE="无法获取最新备份"
    else
        STATUS="NORMAL"
        MESSAGE="备份正常: $BACKUP_COUNT份, 最新: $LATEST_BACKUP"
    fi
    
    echo "  \"backup\": {\"count\": $BACKUP_COUNT, \"latest\": \"$LATEST_BACKUP\", \"status\": \"$STATUS\", \"message\": \"$MESSAGE\"}"
}

# 主检查
echo "{"
echo "  \"timestamp\": \"$DATE\","
echo "  \"status\": {"

check_disk
check_api
check_backup

echo "  }"
echo "}"

# 记录状态
STATUS_SUMMARY=$(check_disk 2>/dev/null | grep -o '"status": "[^"]*"' | head -1 | cut -d'"' -f4)
echo "[$DATE] System check completed" >> "$LOG_FILE"
