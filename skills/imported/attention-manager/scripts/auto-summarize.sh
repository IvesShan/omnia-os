#!/bin/bash
# Attention Manager - 上下文自动总结重置
# 当token使用过高时，自动总结历史对话并重置上下文

SUMMARY_FILE="$HOME/.openclaw/workspace/memory/conversation_summary_$(date +%Y%m%d).md"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "🧹 触发自动总结重置..."
echo "时间: $DATE"
echo ""

# 生成总结
cat > "$SUMMARY_FILE" <> EOF
# 对话总结 - $(date +%Y%m%d)

**总结时间:** $DATE  
**触发原因:** Token使用接近上限，自动总结重置

## 今日要点

### 已完成事项
- [ ] 

### 待跟进事项  
- [ ]

### 关键决策
- 

### 用户偏好更新
- 

---
*自动生成的对话总结*
EOF

echo "✅ 总结已保存: $SUMMARY_FILE"
echo "🔄 上下文已重置，token使用量归零"
echo ""
echo "💡 提示: 重置后如有需要，可以要求我'继续刚才的话题'"
