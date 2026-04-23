#!/bin/bash
# 测试 128K 上下文性能

echo "========================================="
echo "  128K 上下文性能测试"
echo "========================================="

# 测试不同长度的上下文
for ctx_tokens in 1000 5000 10000 20000 40000 64000; do
    echo ""
    echo "📊 测试上下文长度: $ctx_tokens tokens"
    
    # 生成填充文本（模拟长对话）
    padding=$(python3 -c "print('这是一个测试句子。' * ($ctx_tokens // 10))")
    
    # 发送请求并计时
    start_time=$(date +%s.%N)
    
    response=$(curl -s http://localhost:8080/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"gemma-4-e4b\",
        \"messages\": [
          {\"role\": \"user\", \"content\": \"$padding\"},
          {\"role\": \"user\", \"content\": \"请用一句话总结以上内容\"}
        ],
        \"max_tokens\": 100,
        \"stream\": false
      }")
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    
    # 提取生成速度
    completion_tokens=$(echo "$response" | jq -r '.usage.completion_tokens')
    speed=$(echo "scale=2; $completion_tokens / $duration" | bc)
    
    echo "  ⏱️  耗时: ${duration}s"
    echo "  🚀 速度: ${speed} tok/s"
    echo "  📝 生成: $completion_tokens tokens"
done

echo ""
echo "========================================="
echo "  测试完成"
echo "========================================="
