#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 无人机维修诊断与二手检测工具包
基于 DJI Assistant 2 协议逆向分析

功能:
1. 通过USB连接读取飞机数据
2. 诊断故障并生成报告
3. 评估二手价值

作者: 无限 (Omnia)
日期: 2026-04-21
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# 导入子模块
from dji_communicator import DJICommunicator
from dji_fault_db import FaultDatabase
from dji_log_parser import LogParser
from dji_assessment import AssessmentEngine
from dji_report import ReportGenerator


@dataclass
class DeviceInfo:
    """设备信息"""
    model: str = "Unknown"
    serial_number: str = "Unknown"
    firmware_version: str = "Unknown"
    hardware_version: str = "Unknown"
    flight_time: int = 0  # 分钟
    battery_cycles: int = 0
    total_distance: float = 0.0  # km
    last_flight_date: str = "Unknown"
    activation_date: str = "Unknown"
    

@dataclass
class DiagnosisResult:
    """诊断结果"""
    device_info: DeviceInfo
    faults: List[Dict]
    warnings: List[Dict]
    health_score: int  # 0-100
    assessment: Dict
    recommendations: List[str]
    timestamp: str


class DJIDiagnosticTool:
    """DJI 诊断工具主类"""
    
    def __init__(self):
        self.communicator = DJICommunicator()
        self.fault_db = FaultDatabase()
        self.log_parser = LogParser()
        self.assessment = AssessmentEngine()
        self.report_gen = ReportGenerator()
        
    def connect_device(self) -> bool:
        """连接设备"""
        print("🔌 正在连接 DJI 设备...")
        if not self.communicator.connect_usb():
            print("❌ 连接失败，请检查:")
            print("   1. 设备是否通过 USB 连接")
            print("   2. 设备是否已开机")
            print("   3. 是否已安装 DJI 驱动")
            print("   4. Linux/Mac 用户可能需要 sudo 权限")
            return False
        return True
    
    def read_device_info(self) -> DeviceInfo:
        """读取设备信息"""
        print("📊 读取设备信息...")
        info = DeviceInfo()
        
        # 查询设备信息
        response = self.communicator.query_device_info()
        if response:
            # 解析设备信息（需要根据实际协议完善）
            info.model = self._parse_model(response)
            info.serial_number = self._parse_serial(response)
            info.firmware_version = self._parse_firmware(response)
        
        # 查询飞行数据
        flight_data = self.communicator.query_flight_data()
        if flight_data:
            info.flight_time = flight_data.get('flight_time', 0)
            info.battery_cycles = flight_data.get('battery_cycles', 0)
            info.total_distance = flight_data.get('total_distance', 0.0)
        
        return info
    
    def run_diagnosis(self) -> DiagnosisResult:
        """运行完整诊断"""
        print("\n" + "="*60)
        print("🔍 开始全面诊断...")
        print("="*60)
        
        # 1. 读取设备信息
        device_info = self.read_device_info()
        print(f"\n📱 设备型号: {device_info.model}")
        print(f"🔢 序列号: {device_info.serial_number}")
        print(f"🔋 电池循环: {device_info.battery_cycles}")
        print(f"⏱️  飞行时间: {device_info.flight_time} 分钟")
        
        # 2. 导出日志
        print("\n📥 导出飞行日志...")
        log_files = self._export_logs()
        
        # 3. 分析日志
        print("\n🔍 分析日志...")
        faults = []
        warnings = []
        
        for log_file in log_files:
            log_data = self.log_parser.parse(log_file)
            file_faults, file_warnings = self.fault_db.analyze(log_data)
            faults.extend(file_faults)
            warnings.extend(file_warnings)
        
        # 4. 健康评分
        print("\n💯 计算健康评分...")
        health_score = self._calculate_health_score(device_info, faults, warnings)
        
        # 5. 二手评估
        print("\n💰 评估二手价值...")
        assessment = self.assessment.evaluate(device_info, health_score)
        
        # 6. 生成建议
        recommendations = self._generate_recommendations(faults, warnings, device_info)
        
        # 7. 生成报告
        result = DiagnosisResult(
            device_info=device_info,
            faults=faults,
            warnings=warnings,
            health_score=health_score,
            assessment=assessment,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
        
        return result
    
    def generate_report(self, result: DiagnosisResult, output_dir: str = "./reports") -> str:
        """生成诊断报告"""
        print("\n📄 生成诊断报告...")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成JSON报告
        report_path = self.report_gen.generate_json(result, output_dir)
        
        # 生成HTML报告
        html_path = self.report_gen.generate_html(result, output_dir)
        
        # 生成文本报告
        text_path = self.report_gen.generate_text(result, output_dir)
        
        print(f"✅ 报告已生成:")
        print(f"   📊 JSON: {report_path}")
        print(f"   🌐 HTML: {html_path}")
        print(f"   📝 TEXT: {text_path}")
        
        return html_path
    
    def _export_logs(self) -> List[str]:
        """导出日志文件"""
        log_files = []
        log_types = ["state", "vision", "gimbal", "camera", "navigation"]
        
        for log_type in log_types:
            try:
                filepath = self.communicator.export_flight_log(log_type, "./dji_logs")
                if filepath:
                    log_files.append(filepath)
            except Exception as e:
                print(f"   ⚠️  导出 {log_type} 日志失败: {e}")
        
        return log_files
    
    def _calculate_health_score(self, info: DeviceInfo, faults: List, warnings: List) -> int:
        """计算健康评分"""
        score = 100
        
        # 根据故障扣分
        for fault in faults:
            severity = fault.get('severity', 'medium')
            if severity == 'critical':
                score -= 25
            elif severity == 'high':
                score -= 15
            elif severity == 'medium':
                score -= 10
            else:
                score -= 5
        
        # 根据警告扣分
        for warning in warnings:
            score -= 3
        
        # 根据飞行时间扣分（老化）
        if info.flight_time > 5000:  # 超过83小时
            score -= 10
        elif info.flight_time > 2000:  # 超过33小时
            score -= 5
        
        # 根据电池循环扣分
        if info.battery_cycles > 300:
            score -= 15
        elif info.battery_cycles > 200:
            score -= 10
        elif info.battery_cycles > 100:
            score -= 5
        
        return max(0, score)
    
    def _generate_recommendations(self, faults: List, warnings: List, info: DeviceInfo) -> List[str]:
        """生成维修建议"""
        recommendations = []
        
        # 根据故障生成建议
        for fault in faults:
            solutions = fault.get('solutions', [])
            if solutions:
                recommendations.append(f"【{fault['name']}】{solutions[0]}")
        
        # 根据设备状态生成建议
        if info.battery_cycles > 200:
            recommendations.append("【电池】建议更换电池，循环次数过高")
        
        if info.flight_time > 3000:
            recommendations.append("【保养】建议进行全面保养，飞行时间较长")
        
        # 通用建议
        if not recommendations:
            recommendations.append("设备状态良好，建议定期检查和保养")
        
        return recommendations
    
    def _parse_model(self, data: bytes) -> str:
        """解析设备型号"""
        # TODO: 根据实际协议解析
        model_map = {
            b'wm231': 'Mini 4 Pro',
            b'wm232': 'Mini 4 Pro',
            b'wm161': 'Mavic Mini',
            b'wm1615': 'Mini SE',
            b'wm163': 'Mini 2',
            b'wm1605': 'Mini 2 SE',
        }
        for key, value in model_map.items():
            if key in data:
                return value
        return "Unknown Model"
    
    def _parse_serial(self, data: bytes) -> str:
        """解析序列号"""
        # TODO: 根据实际协议解析
        return "SN" + data[:16].hex().upper() if len(data) >= 16 else "Unknown"
    
    def _parse_firmware(self, data: bytes) -> str:
        """解析固件版本"""
        # TODO: 根据实际协议解析
        return "Unknown"
    
    def disconnect(self):
        """断开连接"""
        self.communicator.disconnect()


def main():
    """主程序入口"""
    print("="*60)
    print("🚁 DJI 无人机维修诊断与二手检测工具")
    print("="*60)
    print()
    
    tool = DJIDiagnosticTool()
    
    # 连接设备
    if not tool.connect_device():
        print("\n❌ 无法连接设备，程序退出")
        sys.exit(1)
    
    try:
        # 运行诊断
        result = tool.run_diagnosis()
        
        # 生成报告
        report_path = tool.generate_report(result)
        
        # 显示摘要
        print("\n" + "="*60)
        print("📋 诊断摘要")
        print("="*60)
        print(f"设备型号: {result.device_info.model}")
        print(f"序列号: {result.device_info.serial_number}")
        print(f"健康评分: {result.health_score}/100")
        print(f"故障数量: {len(result.faults)}")
        print(f"警告数量: {len(result.warnings)}")
        print(f"二手估值: ¥{result.assessment.get('estimated_value', 0):,.0f}")
        print()
        print("💡 主要建议:")
        for i, rec in enumerate(result.recommendations[:3], 1):
            print(f"   {i}. {rec}")
        print()
        print(f"📄 完整报告: {report_path}")
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        tool.disconnect()
    
    print("\n✅ 诊断完成!")


if __name__ == "__main__":
    main()
