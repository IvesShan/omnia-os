#!/usr/bin/env python3
"""DJI 诊断工具快速测试"""

import sys
sys.path.insert(0, 'src')

from dji.diagnostics.engine import DiagnosticEngine
from dji.diagnostics.fault_analyzer import FaultAnalyzer

print("\n" + "="*60)
print("  DJI 智能诊断工具 - 快速演示")
print("="*60 + "\n")

# 测试 1: 正常设备
print("📱 测试 1: 正常设备诊断")
print("-" * 60)
engine = DiagnosticEngine()

device_info = {
    'device_type': 0x0a,
    'model': 'wm163',
    'serial': '123ABC456'
}

status_data = {
    'status': 0,
    'temperature': 35,
    'voltage': 12.6
}

result = engine.diagnose_device(device_info, status_data)
print(f"设备型号: {result['device_info']['model_name']}")
print(f"诊断结果: {result['status']}")
print(f"严重程度: {result['severity']}")

# 测试 2: 通信故障
print("\n" + "-" * 60)
print("📱 测试 2: 通信故障诊断")
print("-" * 60)

error_codes = ['sendTextMessage failed', 'Time Out Error']
result = engine.diagnose_device(device_info, error_codes=error_codes)
print(f"检测到 {len(error_codes)} 个错误代码")
if result['faults']:
    print(f"匹配故障模式: {result['faults'][0].get('pattern', 'unknown')}")

# 测试 3: 电池过热
print("\n" + "-" * 60)
print("🔋 测试 3: 电池健康诊断")
print("-" * 60)

battery_info = {'device_type': 0x05, 'model': 'battery'}
battery_status = {'status': 0, 'temperature': 58, 'voltage': 10.5}

result = engine.diagnose_device(battery_info, battery_status)
print(f"诊断结果: {result['status']}")
if result['issues']:
    for issue in result['issues']:
        print(f"  ⚠️  {issue['description']}")

print("\n" + "="*60)
print("  ✅ 测试完成！")
print("="*60 + "\n")
