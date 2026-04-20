#!/bin/bash
# DJI 诊断工具启动脚本

echo "🚀 启动 DJI 诊断工具..."
echo ""
echo "📍 访问地址: http://127.0.0.1:5001/dji/"
echo ""
echo "✅ 功能说明:"
echo "  - 自动扫描 DJI 设备"
echo "  - 显示设备详细信息"
echo "  - 运行设备诊断"
echo "  - 导出诊断报告"
echo ""
echo "💡 提示: 确保 DJI 设备已通过 USB 连接并开机"
echo ""

# 在浏览器中打开
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:5001/dji/
elif command -v open &> /dev/null; then
    open http://127.0.0.1:5001/dji/
fi

echo "✨ 浏览器已打开，如果没有自动打开，请手动访问上述地址"
