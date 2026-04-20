#!/bin/bash
# Perception Monitor - 文件变化监控
# 监控重要目录的文件变化

WATCH_DIR="$HOME/.openclaw/workspace"
SNAPSHOT_FILE="$HOME/.openclaw/protect/file-snapshot.txt"
LOG_FILE="$HOME/.openclaw/logs/file-changes.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 生成当前快照
generate_snapshot() {
    find "$WATCH_DIR" -type f \( -name "*.md" -o -name "*.html" -o -name "*.docx" -o -name "*.pptx" \) -printf "%T@ %p\n" 2>/dev/null | sort > "$SNAPSHOT_FILE.new"
}

# 对比快照，找出变化
detect_changes() {
    if [ ! -f "$SNAPSHOT_FILE" ]; then
        # 首次运行，创建初始快照
        generate_snapshot
        mv "$SNAPSHOT_FILE.new" "$SNAPSHOT_FILE"
        echo "首次运行，已创建文件快照"
        return
    fi
    
    # 对比
    NEW_FILES=$(comm -23 <(sort "$SNAPSHOT_FILE.new") <(sort "$SNAPSHOT_FILE") | wc -l)
    MODIFIED_FILES=$(comm -12 <(sort "$SNAPSHOT_FILE.new") <(sort "$SNAPSHOT_FILE") | wc -l)
    
    if [ $NEW_FILES -gt 0 ]; then
        echo "[$DATE] 检测到 $NEW_FILES 个新文件" >> "$LOG_FILE"
        comm -23 <(sort "$SNAPSHOT_FILE.new") <(sort "$SNAPSHOT_FILE") | while read line; do
            file=$(echo "$line" | cut -d' ' -f2-)
            echo "  NEW: $file" >> "$LOG_FILE"
        done
    fi
    
    # 更新快照
    mv "$SNAPSHOT_FILE.new" "$SNAPSHOT_FILE"
    
    echo "{"
    echo "  \"timestamp\": \"$DATE\","
    echo "  \"new_files\": $NEW_FILES,"
    echo "  \"watched_directory\": \"$WATCH_DIR\""
    echo "}"
}

# 命令处理
case "$1" in
    check)
        generate_snapshot
        detect_changes
        ;;
    snapshot)
        generate_snapshot
        mv "$SNAPSHOT_FILE.new" "$SNAPSHOT_FILE"
        echo "✅ 文件快照已更新"
        ;;
    *)
        echo "文件变化监控器"
        echo "用法: $0 {check|snapshot}"
        echo ""
        echo "  check    - 检查文件变化"
        echo "  snapshot - 更新文件快照"
        ;;
esac
