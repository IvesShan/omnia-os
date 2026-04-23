#!/bin/bash
# Omnia 模型模式管理工具
# 用法: bash scripts/model_mode.sh [local|cloud|auto|status]

set -e

OMNIA_ENV="$HOME//home/shan/omnia-os/omnia-os/.env"
MODE_FILE="/tmp/omnia_model_mode"

# 读取当前模式
get_current_mode() {
    if [ -f "$MODE_FILE" ]; then
        cat "$MODE_FILE"
    else
        echo "auto"
    fi
}

# 保存模式
save_mode() {
    echo "$1" > "$MODE_FILE"
}

# 检查本地服务状态
check_local_service() {
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ 运行中"
    else
        echo "❌ 未运行"
    fi
}

case "${1:-status}" in
    local|local_only)
        save_mode "local_only"
        echo "✅ 已切换到【本地模式】"
        echo "   - 所有请求使用本地 GPU 模型"
        echo "   - 零 Token 成本"
        echo "   - 隐私保护"
        echo ""
        echo "本地服务状态: $(check_local_service)"
        echo ""
        echo "如未启动，运行: bash scripts/local_llm.sh start"
        ;;
        
    cloud|cloud_only)
        save_mode "cloud_only"
        echo "✅ 已切换到【云端模式】"
        echo "   - 所有请求使用云端模型"
        echo "   - 更强大的模型能力"
        echo "   - 需要 Token 配额"
        ;;
        
    auto)
        save_mode "auto"
        echo "✅ 已切换到【自动模式】"
        echo "   - 简单任务用本地（免费）"
        echo "   - 复杂任务用云端（智能）"
        echo "   - 本地不可用自动降级"
        echo ""
        echo "本地服务状态: $(check_local_service)"
        ;;
        
    status)
        current=$(get_current_mode)
        echo "📊 当前模式: $current"
        echo ""
        
        case "$current" in
            local_only)
                echo "说明: 只用本地模型"
                ;;
            cloud_only)
                echo "说明: 只用云端模型"
                ;;
            auto)
                echo "说明: 智能选择模型"
                ;;
        esac
        
        echo ""
        echo "本地服务: $(check_local_service)"
        echo ""
        echo "切换命令:"
        echo "  bash scripts/model_mode.sh local  # 只用本地"
        echo "  bash scripts/model_mode.sh cloud  # 只用云端"
        echo "  bash scripts/model_mode.sh auto   # 智能选择"
        ;;
        
    *)
        echo "用法: bash scripts/model_mode.sh [local|cloud|auto|status]"
        echo ""
        echo "选项:"
        echo "  local  - 只用本地 GPU 模型（免费、隐私）"
        echo "  cloud  - 只用云端模型（强大、需 Token）"
        echo "  auto   - 智能选择（默认）"
        echo "  status - 查看当前状态"
        exit 1
        ;;
esac
