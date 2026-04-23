#!/bin/bash
# LLM 性能测试脚本

echo "========================================="
echo "  LLM 性能基准测试"
echo "========================================="

API_URL="http://localhost:8080/v1/chat/completions"
TEST_PROMPT="请用简洁的语言介绍一下人工智能的发展历史，不超过100字。"

echo ""
echo "📝 测试提示词：$TEST_PROMPT"
echo ""

# 预热请求
echo "🔥 预热中..."
curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"gemma\",
        \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}],
        \"max_tokens\": 10
    }" > /dev/null 2>&1

sleep 1

# 正式测试
echo "⚡ 开始测试..."
echo ""

START_TIME=$(date +%s.%N)

RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"gemma\",
        \"messages\": [{\"role\": \"user\", \"content\": \"$TEST_PROMPT\"}],
        \"max_tokens\": 200,
        \"stream\": false
    }")

END_TIME=$(date +%s.%N)

# 计算延迟
LATENCY=$(echo "$END_TIME - $START_TIME" | bc)
LATENCY_MS=$(echo "$LATENCY * 1000" | bc | cut -d. -f1)

# 提取响应内容
CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content' 2>/dev/null || echo "解析失败")

# 提取 token 统计
PROMPT_TOKENS=$(echo "$RESPONSE" | jq -r '.usage.prompt_tokens' 2>/dev/null || echo "N/A")
COMPLETION_TOKENS=$(echo "$RESPONSE" | jq -r '.usage.completion_tokens' 2>/dev/null || echo "N/A")
TOTAL_TOKENS=$(echo "$RESPONSE" | jq -r '.usage.total_tokens' 2>/dev/null || echo "N/A")

# 计算速度
if [ "$COMPLETION_TOKENS" != "N/A" ] && [ "$LATENCY" != "0" ]; then
    SPEED=$(echo "scale=1; $COMPLETION_TOKENS / $LATENCY" | bc)
else
    SPEED="N/A"
fi

# 输出结果
echo "========================================="
echo "  测试结果"
echo "========================================="
echo ""
echo "📊 性能指标："
echo "  • 总延迟：${LATENCY_MS} ms"
echo "  • 生成速度：${SPEED} tokens/s"
echo ""
echo "📈 Token 统计："
echo "  • 提示词：$PROMPT_TOKENS tokens"
echo "  • 生成：$COMPLETION_TOKENS tokens"
echo "  • 总计：$TOTAL_TOKENS tokens"
echo ""
echo "💬 模型响应："
echo "$CONTENT"
echo ""
echo "========================================="
