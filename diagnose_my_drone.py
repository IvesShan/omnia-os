#!/usr/bin/env python3
"""
DJI 无人机诊断工具 - 交互式诊断
使用方法: python3 diagnose_my_drone.py
"""

import sys
import json
from datetime import datetime

sys.path.insert(0, '/home/shan//home/shan/omnia-os/omnia-os/src')

from dji.diagnostics.engine import DiagnosticEngine
from dji.diagnostics.fault_analyzer import FaultAnalyzer
from dji.diagnostics.repair_advisor import RepairAdvisor


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    print("\n" + "-" * 60)
    print(f"  {title}")
    print("-" * 60)


def get_user_input():
    """交互式获取无人机信息"""
    print_header("DJI 无人机智能诊断系统")
    print("\n请输入您的无人机信息：\n")
    
    # 设备信息
    print("【设备信息】")
    device_id = input("  设备ID (如: WM163, 留空自动生成): ").strip()
    if not device_id:
        device_id = f"DRONE_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    device_type = input("  设备类型 (1=无人机, 2=云台, 3=相机, 默认=1): ").strip()
    device_type = "drone" if device_type != "2" and device_type != "3" else ("gimbal" if device_type == "2" else "camera")
    
    model = input("  型号 (如: Mini 3, Mavic 3, Air 2S): ").strip()
    if not model:
        model = "Unknown"
    
    # 状态数据
    print("\n【状态数据】")
    print("  请输入当前状态（可选）：")
    
    battery_level = input("  电池电量 % (0-100, 留空跳过): ").strip()
    temperature = input("  温度 °C (留空跳过): ").strip()
    voltage = input("  电压 V (留空跳过): ").strip()
    signal_strength = input("  信号强度 % (0-100, 留空跳过): ").strip()
    
    # 构建状态数据
    status_data = {}
    if battery_level:
        status_data['battery_level'] = int(battery_level)
    if temperature:
        status_data['temperature'] = float(temperature)
    if voltage:
        status_data['voltage'] = float(voltage)
    if signal_strength:
        status_data['signal_strength'] = int(signal_strength)
    
    # 错误代码
    print("\n【错误信息】")
    has_errors = input("  是否有错误代码? (y/n): ").strip().lower()
    
    error_codes = []
    if has_errors == 'y':
        print("  请输入错误代码（每行一个，输入 'done' 结束）：")
        while True:
            code = input("  错误代码: ").strip()
            if code.lower() == 'done' or not code:
                break
            error_codes.append(code)
    
    # 症状描述
    print("\n【症状描述】")
    symptoms = input("  请描述遇到的问题（如: 无法连接、飞行不稳定）: ").strip()
    
    return {
        'device_id': device_id,
        'device_type': device_type,
        'model': model,
        'status_data': status_data,
        'error_codes': error_codes,
        'symptoms': symptoms
    }


def run_diagnosis(device_info):
    """执行诊断"""
    print_header("开始诊断...")
    
    # 创建诊断引擎
    engine = DiagnosticEngine()
    analyzer = FaultAnalyzer()
    advisor = RepairAdvisor()
    
    # 设备信息
    device_id = device_info['device_id']
    device_type = device_info['device_type']
    model = device_info['model']
    status_data = device_info['status_data']
    error_codes = device_info['error_codes']
    symptoms = device_info['symptoms']
    
    # 步骤 1: 基础诊断
    print_section("步骤 1: 设备状态分析")
    
    if status_data:
        result = engine.diagnose_device(
            device_id=device_id,
            status_data=status_data
        )
        
        print(f"\n  设备ID: {device_id}")
        print(f"  设备型号: {result.get('device_model', model)}")
        print(f"  诊断结果: {result.get('result', 'unknown')}")
        print(f"  严重程度: {result.get('severity', 'unknown')}")
        
        # 显示警告
        if 'warnings' in result and result['warnings']:
            print("\n  ⚠️  警告信息：")
            for warning in result['warnings']:
                print(f"    - {warning}")
    else:
        print("  ⚠️  未提供状态数据，跳过状态分析")
    
    # 步骤 2: 故障分析
    print_section("步骤 2: 故障模式匹配")
    
    if error_codes:
        print(f"\n  检测到 {len(error_codes)} 个错误代码:")
        for code in error_codes:
            print(f"    - {code}")
        
        # 分析错误
        fault_result = analyzer.analyze(error_codes, symptoms)
        
        print(f"\n  匹配故障模式: {fault_result.get('pattern', 'unknown')}")
        print(f"  置信度: {fault_result.get('confidence', 0):.0%}")
        
        if 'possible_causes' in fault_result:
            print("\n  可能原因：")
            for cause in fault_result['possible_causes']:
                print(f"    • {cause}")
        
        if 'recommendations' in fault_result:
            print("\n  建议：")
            for rec in fault_result['recommendations']:
                print(f"    ✓ {rec}")
    else:
        print("  ✓ 未检测到错误代码")
    
    # 步骤 3: 维修建议
    print_section("步骤 3: 维修建议")
    
    if error_codes or symptoms:
        # 生成维修建议
        repair_plan = advisor.generate_repair_plan(
            device_id=device_id,
            fault_pattern=fault_result.get('pattern', 'unknown') if error_codes else 'unknown',
            severity=result.get('severity', 'medium') if status_data else 'medium'
        )
        
        print(f"\n  维修方案: {repair_plan.get('plan_name', '标准维修流程')}")
        print(f"  预计时间: {repair_plan.get('estimated_time', '未知')}")
        print(f"  难度等级: {repair_plan.get('difficulty', '未知')}")
        
        if 'steps' in repair_plan:
            print("\n  维修步骤：")
            for i, step in enumerate(repair_plan['steps'], 1):
                print(f"    {i}. {step}")
        
        if 'maintenance_schedule' in repair_plan:
            print("\n  维护计划：")
            for task in repair_plan['maintenance_schedule']:
                print(f"    • {task}")
    else:
        print("  ✓ 设备状态良好，无需维修")
    
    # 总结
    print_header("诊断完成")
    
    print("\n  📋 诊断摘要：")
    print(f"    设备ID: {device_id}")
    print(f"    型号: {model}")
    print(f"    状态: {'需要关注' if (error_codes or symptoms) else '正常'}")
    
    if error_codes:
        print(f"    错误代码: {', '.join(error_codes)}")
    if symptoms:
        print(f"    症状: {symptoms}")
    
    print("\n" + "=" * 60)
    print("  感谢使用 DJI 智能诊断系统！")
    print("=" * 60 + "\n")


def main():
    try:
        # 获取用户输入
        device_info = get_user_input()
        
        # 执行诊断
        run_diagnosis(device_info)
        
    except KeyboardInterrupt:
        print("\n\n  已取消诊断。")
    except Exception as e:
        print(f"\n  ❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
