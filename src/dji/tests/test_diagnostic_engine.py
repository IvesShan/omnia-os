#!/usr/bin/env python3
"""
测试诊断引擎
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from diagnostics import DiagnosticEngine, FaultAnalyzer, RepairAdvisor


def test_diagnostic_engine():
    """测试诊断引擎"""
    print("=" * 70)
    print("测试诊断引擎")
    print("=" * 70)
    
    engine = DiagnosticEngine()
    
    # 测试设备类型映射
    print("\n[1] 设备类型映射测试:")
    for device_type, name in list(engine.device_types.items())[:5]:
        print(f"   0x{device_type:02x} -> {name}")
    
    # 测试设备型号映射
    print("\n[2] 设备型号映射测试:")
    for model, name in list(engine.device_models.items())[:5]:
        print(f"   {model} -> {name}")
    
    # 测试诊断功能
    print("\n[3] 诊断功能测试:")
    device_info = {
        'device_type': 0x0a,
        'device_type_name': '飞控',
        'product': 'DJI Mini 3',
        'serial': 'TEST123456'
    }
    
    # 模拟正常状态
    status_data_normal = b'\x01'
    diagnosis_normal = engine.diagnose_device(device_info, status_data_normal)
    print(f"\n   正常状态诊断:")
    print(f"   状态: {diagnosis_normal['status']}")
    print(f"   严重程度: {diagnosis_normal['severity']}")
    
    # 模拟错误状态
    status_data_error = b'\x04'
    diagnosis_error = engine.diagnose_device(device_info, status_data_error)
    print(f"\n   错误状态诊断:")
    print(f"   状态: {diagnosis_error['status']}")
    print(f"   严重程度: {diagnosis_error['severity']}")
    print(f"   问题数量: {len(diagnosis_error['issues'])}")
    
    # 测试错误代码分析
    print("\n[4] 错误代码分析测试:")
    error_codes = ["sendTextMessage failed", "Time Out Error"]
    diagnosis_with_codes = engine.diagnose_device(
        device_info,
        status_data_normal,
        error_codes
    )
    print(f"   错误代码: {error_codes}")
    print(f"   故障数量: {len(diagnosis_with_codes['faults'])}")
    for fault in diagnosis_with_codes['faults']:
        print(f"   - {fault['code']}: {fault['description']}")
    
    print("\n✅ 诊断引擎测试完成")


def test_fault_analyzer():
    """测试故障分析器"""
    print("\n" + "=" * 70)
    print("测试故障分析器")
    print("=" * 70)
    
    analyzer = FaultAnalyzer()
    
    # 测试故障模式匹配
    print("\n[1] 故障模式匹配测试:")
    symptoms = ["sendTextMessage failed", "Time Out Error"]
    analysis = analyzer.analyze(symptoms)
    
    print(f"   症状: {symptoms}")
    print(f"   匹配模式数: {len(analysis['matched_patterns'])}")
    print(f"   严重程度: {analysis['severity']}")
    
    for pattern in analysis['matched_patterns']:
        print(f"\n   模式: {pattern['pattern']}")
        print(f"   匹配症状: {pattern['matched_symptoms']}")
        print(f"   可能原因: {pattern['root_causes'][:3]}")
    
    # 测试统计功能
    print("\n[2] 故障统计测试:")
    # 添加更多分析记录
    analyzer.analyze(["云台过载", "云台震动"])
    analyzer.analyze(["电池无法识别"])
    
    stats = analyzer.get_fault_statistics()
    print(f"   总分析次数: {stats['total']}")
    print(f"   按严重程度: {dict(stats['by_severity'])}")
    print(f"   按模式: {dict(stats['by_pattern'])}")
    
    # 测试预防建议
    print("\n[3] 预防建议测试:")
    suggestions = analyzer.suggest_preventive_actions()
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion}")
    
    print("\n✅ 故障分析器测试完成")


def test_repair_advisor():
    """测试维修顾问"""
    print("\n" + "=" * 70)
    print("测试维修顾问")
    print("=" * 70)
    
    advisor = RepairAdvisor()
    
    # 测试维修建议生成
    print("\n[1] 维修建议生成测试:")
    diagnosis = {
        'issues': [
            {'causes': ['USB线缆损坏', 'USB接口松动']}
        ],
        'faults': []
    }
    
    advice = advisor.generate_advice(diagnosis)
    
    print(f"   维修方案数: {len(advice['repair_options'])}")
    
    for i, option in enumerate(advice['repair_options'], 1):
        print(f"\n   方案 {i}: {option['cause']}")
        print(f"   难度: {option['difficulty']['description']}")
        print(f"   费用: {option['cost']}")
        print(f"   成功率: {option['success_rate']*100:.0f}%")
    
    if advice['recommended_action']:
        print(f"\n   ⭐ 推荐方案: {advice['recommended_action']['cause']}")
    
    # 测试维护计划
    print("\n[2] 维护计划测试:")
    maintenance = advisor.get_maintenance_schedule("DJI Mini 3", flight_hours=60)
    
    print(f"   设备类型: {maintenance['device_type']}")
    print(f"   飞行小时: {maintenance['flight_hours']}")
    print(f"   下次维护: {maintenance['next_maintenance']}")
    print(f"   维护建议数: {len(maintenance['recommendations'])}")
    
    print("\n   前5条建议:")
    for i, rec in enumerate(maintenance['recommendations'][:5], 1):
        print(f"   {i}. {rec}")
    
    print("\n✅ 维修顾问测试完成")


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("  DJI 诊断引擎测试套件")
    print("=" * 70)
    
    try:
        test_diagnostic_engine()
        test_fault_analyzer()
        test_repair_advisor()
        
        print("\n" + "=" * 70)
        print("  ✅ 所有测试通过")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
