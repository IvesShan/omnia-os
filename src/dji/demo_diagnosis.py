#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 诊断工具演示脚本
展示完整的诊断流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dji.diagnostics.engine import DiagnosticEngine
from dji.diagnostics.fault_analyzer import FaultAnalyzer
from dji.diagnostics.repair_advisor import RepairAdvisor


def demo_normal_device():
    """场景1: 正常设备诊断"""
    print("\n" + "="*70)
    print("  场景 1: 正常设备诊断")
    print("="*70)
    
    device_info = {
        'device_type': 0x0a,
        'model': 'wm163',
        'serial': '123ABC456',
        'firmware': 'v01.00.0500'
    }
    
    status_data = {
        'status': 0,
        'temperature': 35,
        'voltage': 12.6,
        'flight_time': 60
    }
    
    engine = DiagnosticEngine()
    result = engine.diagnose_device(device_info, status_data)
    
    print(f"\n📱 设备信息:")
    print(f"   型号: {result['device_info']['model_name']}")
    print(f"   类型: {result['device_info']['type_name']}")
    print(f"   序列号: {result['device_info']['serial']}")
    print(f"   固件: {result['device_info']['firmware']}")
    
    print(f"\n✅ 诊断结果: {result['status'].upper()}")
    print(f"   严重程度: {result['severity']}")
    
    if result['recommendations']:
        print(f"\n💡 建议:")
        for rec in result['recommendations']:
            print(f"   • {rec}")


def demo_communication_fault():
    """场景2: 通信故障诊断"""
    print("\n" + "="*70)
    print("  场景 2: 通信故障诊断")
    print("="*70)
    
    device_info = {
        'device_type': 0x0a,
        'model': 'wm231',
        'serial': '789DEF012',
        'firmware': 'v01.01.0600'
    }
    
    error_codes = [
        'sendTextMessage failed',
        'Time Out Error',
        'Do Ping V3 Test Failed!'
    ]
    
    engine = DiagnosticEngine()
    result = engine.diagnose_device(device_info, error_codes=error_codes)
    
    print(f"\n📱 设备: {result['device_info']['model_name']}")
    print(f"\n❌ 检测到 {len(error_codes)} 个错误:")
    for code in error_codes:
        print(f"   • {code}")
    
    if result['faults']:
        print(f"\n🔍 故障模式匹配:")
        for fault in result['faults']:
            print(f"   模式: {fault.get('pattern', 'unknown')}")
            print(f"   描述: {fault.get('description', 'N/A')}")
            if fault.get('possible_causes'):
                print(f"   可能原因:")
                for cause in fault['possible_causes']:
                    print(f"      - {cause}")


def demo_battery_health():
    """场景3: 电池健康诊断"""
    print("\n" + "="*70)
    print("  场景 3: 电池健康诊断")
    print("="*70)
    
    device_info = {
        'device_type': 0x05,
        'model': 'battery',
        'serial': 'BAT123456',
        'firmware': 'v02.00.01'
    }
    
    status_data = {
        'status': 0,
        'temperature': 58,
        'voltage': 10.5,
        'cycle_count': 150
    }
    
    engine = DiagnosticEngine()
    result = engine.diagnose_device(device_info, status_data)
    
    print(f"\n🔋 电池状态:")
    print(f"   温度: {status_data['temperature']}°C")
    print(f"   电压: {status_data['voltage']}V")
    print(f"   循环次数: {status_data['cycle_count']}")
    
    print(f"\n⚠️  诊断结果: {result['status'].upper()}")
    
    if result['issues']:
        print(f"\n🔴 检测到问题:")
        for issue in result['issues']:
            print(f"   • {issue['description']} (严重程度: {issue['severity']})")


def demo_fault_statistics():
    """场景4: 故障统计分析"""
    print("\n" + "="*70)
    print("  场景 4: 故障统计分析")
    print("="*70)
    
    analyzer = FaultAnalyzer()
    
    # 模拟历史诊断记录
    history = [
        {'fault_pattern': 'communication_failure', 'severity': 'high'},
        {'fault_pattern': 'battery_warning', 'severity': 'medium'},
        {'fault_pattern': 'communication_failure', 'severity': 'high'},
        {'fault_pattern': 'gimbal_error', 'severity': 'low'},
        {'fault_pattern': 'camera_error', 'severity': 'medium'},
    ]
    
    print(f"\n📊 历史诊断记录: {len(history)} 次")
    
    # 统计分析
    severity_stats = {}
    pattern_stats = {}
    
    for record in history:
        severity = record.get('severity', 'unknown')
        pattern = record.get('fault_pattern', 'unknown')
        
        severity_stats[severity] = severity_stats.get(severity, 0) + 1
        pattern_stats[pattern] = pattern_stats.get(pattern, 0) + 1
    
    print(f"\n📈 按严重程度分布:")
    for severity, count in sorted(severity_stats.items()):
        print(f"   {severity}: {count} 次")
    
    print(f"\n📈 按故障模式分布:")
    for pattern, count in sorted(pattern_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   {pattern}: {count} 次")


def demo_repair_recommendations():
    """场景5: 维修建议生成"""
    print("\n" + "="*70)
    print("  场景 5: 维修建议生成")
    print("="*70)
    
    advisor = RepairAdvisor()
    
    fault_info = {
        'pattern': 'communication_failure',
        'description': 'USB通信失败',
        'severity': 'high',
        'device_type': 'flight_controller'
    }
    
    print(f"\n🔧 故障信息:")
    print(f"   模式: {fault_info['pattern']}")
    print(f"   描述: {fault_info['description']}")
    print(f"   严重程度: {fault_info['severity']}")
    
    print(f"\n💡 维修建议:")
    print(f"   1. 检查USB线缆连接")
    print(f"   2. 更换USB数据线")
    print(f"   3. 检查USB接口")
    print(f"   4. 重新安装DJI Assistant")
    print(f"   5. 检查驱动程序")


def main():
    """主演示流程"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + " "*15 + "DJI 智能诊断工具 v2.0 - 功能演示" + " "*18 + "█")
    print("█" + " "*68 + "█")
    print("█"*70 + "\n")
    
    try:
        demo_normal_device()
        demo_communication_fault()
        demo_battery_health()
        demo_fault_statistics()
        demo_repair_recommendations()
        
        print("\n" + "="*70)
        print("  ✅ 所有演示场景完成！")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
