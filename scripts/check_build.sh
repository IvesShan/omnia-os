#!/bin/bash
# 检查 Tauri 构建进度

echo "=== Tauri 构建状态检查 ==="
echo ""

# 检查是否有构建进程
if pgrep -f "cargo build" > /dev/null; then
    echo "✓ 构建进程正在运行"
    echo ""
    
    # 显示当前正在编译的 crate
    echo "当前编译任务："
    ps aux | grep rustc | grep -v grep | awk '{print $NF}' | grep -o '\-\-crate-name [^ ]*' | sed 's/--crate-name /  - /' | head -5
    echo ""
    
    # 显示 CPU 使用率
    echo "CPU 使用率："
    ps aux | grep rustc | grep -v grep | awk '{sum+=$3} END {printf "  %.1f%%\n", sum}'
    echo ""
    
    # 检查已编译的文件
    if [ -d "src-tauri/target/release/deps" ]; then
        count=$(ls src-tauri/target/release/deps/*.rlib 2>/dev/null | wc -l)
        echo "已编译依赖库：$count 个"
    fi
else
    echo "✗ 没有正在运行的构建进程"
    echo ""
    
    # 检查是否构建成功
    if [ -f "src-tauri/target/release/omnia" ]; then
        echo "✓ 构建已完成！"
        echo "  可执行文件：src-tauri/target/release/omnia"
        ls -lh src-tauri/target/release/omnia
    else
        echo "构建尚未开始或已失败"
    fi
fi
