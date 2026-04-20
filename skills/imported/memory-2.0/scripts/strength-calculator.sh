#!/bin/bash
# Memory 2.0 - 记忆强度计算器
# 计算和更新所有记忆的强度权重

MEMORY_DIR="$HOME/.openclaw/workspace/memory"
STRENGTH_DB="$HOME/.openclaw/workspace/memory/meta/strength-db.json"
DATE=$(date '+%Y-%m-%d')

mkdir -p "$(dirname "$STRENGTH_DB")"

# 初始化强度数据库
init_db() {
    if [ ! -f "$STRENGTH_DB" ]; then
        echo '{"memories": {}}' > "$STRENGTH_DB"
    fi
}

# 计算文件强度
calculate_strength() {
    local file=$1
    local filename=$(basename "$file")
    
    # 基础强度
    local strength=50
    
    # 核心文件永不遗忘
    if echo "$filename" | grep -qiE "(IDENTITY|SOUL|MEMORY|USER|AGENTS)\.md"; then
        strength=100
    
    # 近期文件增强
    elif find "$file" -mtime -7 2>/dev/null | grep -q .; then
        strength=80
    elif find "$file" -mtime -30 2>/dev/null | grep -q .; then
        strength=70
    elif find "$file" -mtime -90 2>/dev/null | grep -q .; then
        strength=60
    else
        strength=40
    fi
    
    # 高频访问检测（通过文件访问时间）
    if [ -f "$file" ]; then
        # 如果7天内被访问过
        if find "$file" -atime -7 2>/dev/null | grep -q .; then
            strength=$((strength + 10))
        fi
    fi
    
    # 限制最大值
    [ $strength -gt 100 ] && strength=100
    
    echo $strength
}

# 更新强度数据库
update_strength_db() {
    init_db
    
    # 临时文件
    TEMP_DB="${STRENGTH_DB}.tmp"
    
    echo "{"
    echo '  "last_updated": "'$DATE'",'
    echo '  "memories": {'
    
    FIRST=true
    # 遍历所有记忆文件
    find "$MEMORY_DIR" -type f -name "*.md" 2>/dev/null | while read file; do
        filename=$(basename "$file")
        strength=$(calculate_strength "$file")
        
        if [ "$FIRST" = true ]; then
            FIRST=false
        else
            echo ","
        fi
        
        echo -n "    \"$filename\": {\"strength\": $strength, \"path\": \"$file\"}"
    done
    
    echo ""
    echo "  }"
    echo "}"
}

# 主执行
echo "🧠 Memory 2.0 - 强度计算"
echo "========================"

update_strength_db > "$STRENGTH_DB"

echo "✅ 强度数据库已更新: $STRENGTH_DB"
echo ""

# 显示统计
if [ -f "$STRENGTH_DB" ]; then
    CORE_COUNT=$(grep -c '"strength": 100' "$STRENGTH_DB" 2>/dev/null || echo 0)
    HIGH_COUNT=$(grep -E '"strength": (8|9)[0-9]' "$STRENGTH_DB" 2>/dev/null | wc -l)
    MID_COUNT=$(grep -E '"strength": [4567][0-9]' "$STRENGTH_DB" 2>/dev/null | wc -l)
    LOW_COUNT=$(grep -E '"strength": [123][0-9]' "$STRENGTH_DB" 2>/dev/null | wc -l)
    
    echo "强度分布:"
    echo "  🔴 核心 (100): $CORE_COUNT 个"
    echo "  🟠 高 (80-99): $HIGH_COUNT 个"
    echo "  🟡 中 (40-79): $MID_COUNT 个"
    echo "  🟢 低 (≤39):   $LOW_COUNT 个"
fi
