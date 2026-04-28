#!/usr/bin/env python3
"""
DJI 无人机故障诊断工具 v2.0
集成智能诊断引擎、故障分析器和维修顾问
"""

import sys
import time
import json
import usb.core
import usb.util
from datetime import datetime
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from diagnostics import DiagnosticEngine, FaultAnalyzer, RepairAdvisor

# DJI USB参数
DJI_VENDOR_ID = 0x2ca3
DJI_PRODUCT_ID = 0x0020
WORKING_INTERFACE = 4


class DJIDiagnosticTool:
    """DJI故障诊断工具 v2.0"""
    
    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        self.device_info = {}
        
        # 初始化诊断引擎
        self.engine = DiagnosticEngine()
        self.analyzer = FaultAnalyzer()
        self.advisor = RepairAdvisor()
    
    def connect(self):
        """连接设备"""
        print("\n" + "=" * 70)
        print("  DJI 无人机故障诊断工具 v2.0")
        print("  集成智能诊断引擎 | 故障分析 | 维修建议")
        print("=" * 70)
        
        print("\n[1] 搜索DJI设备...")
        self.dev = usb.core.find(idVendor=DJI_VENDOR_ID, idProduct=DJI_PRODUCT_ID)
        
        if self.dev is None:
            print("❌ 未找到设备")
            print("\n请检查:")
            print("  • 设备是否已通过USB连接")
            print("  • 设备是否已开机")
            print("  • USB线缆是否正常")
            return False
        
        product = usb.util.get_string(self.dev, self.dev.iProduct)
        serial = usb.util.get_string(self.dev, self.dev.iSerialNumber)
        
        print(f"✅ 找到设备: {product}")
        print(f"   序列号: {serial}")
        
        self.device_info['product'] = product
        self.device_info['serial'] = serial
        
        # Detach内核驱动
        try:
            if self.dev.is_kernel_driver_active(WORKING_INTERFACE):
                self.dev.detach_kernel_driver(WORKING_INTERFACE)
                print(f"   Detach内核驱动: 接口 {WORKING_INTERFACE}")
        except Exception:
            pass
        
        # 获取端点
        cfg = self.dev.get_active_configuration()
        intf = cfg[(WORKING_INTERFACE, 0)]
        
        for ep in intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                self.ep_out = ep
            else:
                self.ep_in = ep
        
        if self.ep_out and self.ep_in:
            print(f"✅ 端点就绪: OUT=0x{self.ep_out.bEndpointAddress:02x}, IN=0x{self.ep_in.bEndpointAddress:02x}")
            return True
        
        return False
    
    def send_command(self, cmd_id, payload=b'', timeout=1000):
        """发送命令并接收响应"""
        # 构建数据包
        length = 10 + len(payload)
        packet = bytes([
            0x55, 0xAA,        # 起始标志
            0x01,              # 版本
            length,            # 长度
            0x00,              # 命令集
            0x0a,              # 设备类型 (飞控)
            cmd_id,            # 命令ID
            0x00, 0x00,        # 序列号
            0x00, 0x00         # CRC (简化)
        ]) + payload
        
        try:
            self.ep_out.write(packet)
            time.sleep(0.1)
            
            response = self.ep_in.read(512, timeout=timeout)
            return bytes(response)
        except Exception as e:
            return None
    
    def query_device_info(self):
        """查询设备信息"""
        print("\n[2] 查询设备信息...")
        
        # 发送查询命令
        response = self.send_command(0x88)
        
        if response and len(response) >= 10:
            print(f"✅ 收到响应: {len(response)} 字节")
            
            # 解析设备类型
            device_type = response[5] if len(response) > 5 else 0
            device_type_name = self.engine.get_device_type_name(device_type)
            
            self.device_info['device_type'] = device_type
            self.device_info['device_type_name'] = device_type_name
            
            print(f"✅ 设备类型: {device_type_name} (0x{device_type:02x})")
            
            if len(response) > 10:
                payload = response[10:]
                print(f"   负载数据: {payload.hex()[:40]}...")
            
            return True
        
        print("⚠️  未收到有效响应")
        return False
    
    def query_device_status(self):
        """查询设备状态"""
        print("\n[3] 查询设备状态...")
        
        # 发送状态查询命令
        response = self.send_command(0x0C)
        
        if response and len(response) >= 10:
            print(f"✅ 收到状态响应: {len(response)} 字节")
            
            # 保存状态数据用于诊断
            if len(response) > 10:
                self.device_info['status_data'] = response[10:]
            else:
                self.device_info['status_data'] = b'\x00'
            
            return True
        
        print("⚠️  未收到状态响应")
        self.device_info['status_data'] = None
        return False
    
    def diagnose(self):
        """智能诊断"""
        print("\n[4] 执行智能诊断...")
        print("-" * 70)
        
        # 使用诊断引擎
        diagnosis = self.engine.diagnose_device(
            device_info=self.device_info,
            status_data=self.device_info.get('status_data')
        )
        
        # 显示诊断结果
        print(f"\n📊 诊断结果:")
        print(f"   时间: {diagnosis['timestamp']}")
        print(f"   状态: {diagnosis['status'].upper()}")
        print(f"   严重程度: {diagnosis['severity'].upper()}")
        
        # 显示问题
        if diagnosis['issues']:
            print(f"\n⚠️  发现问题 ({len(diagnosis['issues'])}):")
            for i, issue in enumerate(diagnosis['issues'], 1):
                print(f"   {i}. {issue.get('description', issue.get('type', '未知问题'))}")
                if 'severity' in issue:
                    print(f"      严重程度: {issue['severity']}")
        else:
            print(f"\n✅ 未发现问题")
        
        # 显示故障
        if diagnosis['faults']:
            print(f"\n🔴 故障代码 ({len(diagnosis['faults'])}):")
            for fault in diagnosis['faults']:
                print(f"   • {fault['code']}: {fault['description']}")
                print(f"     类别: {fault['category']}")
                print(f"     可能原因: {', '.join(fault['causes'])}")
        
        # 显示建议
        if diagnosis['recommendations']:
            print(f"\n💡 建议:")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        return diagnosis
    
    def analyze_faults(self, diagnosis):
        """深度故障分析"""
        print("\n[5] 深度故障分析...")
        print("-" * 70)
        
        # 提取症状
        symptoms = []
        for issue in diagnosis.get('issues', []):
            if 'type' in issue:
                symptoms.append(issue['type'])
        
        for fault in diagnosis.get('faults', []):
            symptoms.append(fault['code'])
        
        if not symptoms:
            print("✅ 无需深度分析，设备状态正常")
            return None
        
        # 使用故障分析器
        analysis = self.analyzer.analyze(symptoms, self.device_info)
        
        print(f"\n🔍 分析结果:")
        print(f"   匹配模式: {len(analysis['matched_patterns'])}")
        
        for pattern in analysis['matched_patterns']:
            print(f"\n   📌 {pattern['pattern']}:")
            print(f"      匹配症状: {', '.join(pattern['matched_symptoms'])}")
            print(f"      严重程度: {pattern['severity']}")
            print(f"      可能原因:")
            for cause in pattern['root_causes'][:3]:
                print(f"        • {cause}")
        
        print(f"\n🎯 最可能原因:")
        for i, cause in enumerate(analysis['likely_causes'][:5], 1):
            print(f"   {i}. {cause}")
        
        print(f"\n📋 诊断步骤:")
        for step in analysis['diagnostic_plan'][:5]:
            print(f"   {step}")
        
        return analysis
    
    def get_repair_advice(self, diagnosis, analysis):
        """获取维修建议"""
        print("\n[6] 维修建议...")
        print("-" * 70)
        
        # 使用维修顾问
        advice = self.advisor.generate_advice(diagnosis, analysis)
        
        if not advice['repair_options']:
            print("✅ 无需维修，设备状态正常")
            print("\n💡 建议定期维护:")
            maintenance = self.advisor.get_maintenance_schedule(
                self.device_info.get('device_type_name', 'unknown')
            )
            for i, rec in enumerate(maintenance['recommendations'][:5], 1):
                print(f"   {i}. {rec}")
            return advice
        
        print(f"\n🔧 维修方案 ({len(advice['repair_options'])}):")
        
        for i, option in enumerate(advice['repair_options'], 1):
            print(f"\n   方案 {i}: {option['cause']}")
            print(f"   难度: {option['difficulty']['description']}")
            print(f"   预计时间: {option['difficulty']['time_estimate']}")
            print(f"   预计费用: {option['cost']}")
            print(f"   成功率: {option['success_rate']*100:.0f}%")
            
            if option.get('warning'):
                print(f"   ⚠️  {option['warning']}")
            
            print(f"   步骤:")
            for step in option['steps']:
                print(f"      {step}")
        
        # 推荐方案
        if advice['recommended_action']:
            print(f"\n⭐ 推荐方案:")
            rec = advice['recommended_action']
            print(f"   {rec['cause']}")
            print(f"   难度: {rec['difficulty']['description']}")
            print(f"   预计费用: {rec['cost']}")
            print(f"   成功率: {rec['success_rate']*100:.0f}%")
        
        return advice
    
    def save_report(self, diagnosis, analysis, advice):
        """保存诊断报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "device": self.device_info,
            "diagnosis": diagnosis,
            "analysis": analysis,
            "advice": advice
        }
        
        report_path = Path.home() / ".openclaw" / "workspace" / "omnia-os" / "logs" / f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 报告已保存: {report_path}")
    
    def run(self):
        """运行诊断工具"""
        if not self.connect():
            return 1
        
        self.query_device_info()
        self.query_device_status()
        
        diagnosis = self.diagnose()
        analysis = self.analyze_faults(diagnosis)
        advice = self.get_repair_advice(diagnosis, analysis)
        
        # 保存报告
        self.save_report(diagnosis, analysis, advice)
        
        print("\n" + "=" * 70)
        print("  诊断完成")
        print("=" * 70)
        
        return 0


def main():
    """主函数"""
    tool = DJIDiagnosticTool()
    sys.exit(tool.run())


if __name__ == "__main__":
    main()
