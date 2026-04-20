#!/usr/bin/env python3
"""
DJI 真实通信诊断工具
实现完整的 USB 通信流程
"""

import sys
import os
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dji.protocols.v1_protocol import (
    DJIPacket, DeviceType, CommandID, V1Protocol, get_device_name
)
from dji.transport.usb_transport import USBTransport, USBConfig, list_dji_devices
from dji.diagnostics.engine import DiagnosticEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealDJIDiagnosis:
    """真实 DJI 设备诊断"""
    
    def __init__(self):
        self.transport: Optional[USBTransport] = None
        self.protocol = V1Protocol()
        self.engine = DiagnosticEngine()
        self.seq_number = 0
        
    def connect(self) -> bool:
        """连接设备"""
        print("\n" + "="*60)
        print("  🔌 连接 DJI 设备...")
        print("="*60)
        
        # 先扫描设备
        devices = list_dji_devices()
        if not devices:
            print("  ❌ 未找到 DJI 设备")
            return False
        
        print(f"  ✅ 发现 {len(devices)} 个设备:")
        for i, dev in enumerate(devices, 1):
            print(f"     {i}. {dev}")
        
        # 创建传输层
        self.transport = USBTransport()
        
        # 尝试连接
        if not self.transport.connect():
            print("  ❌ 连接失败")
            return False
        
        print("  ✅ 连接成功！")
        return True
    
    def send_command(self, target_type: int, cmd_id: int, data: bytes = b'') -> Optional[DJIPacket]:
        """发送命令并接收响应"""
        if not self.transport or not self.transport.is_connected:
            return None
        
        # 创建数据包
        packet = DJIPacket(
            seq_number=self.seq_number,
            source_type=DeviceType.PC,
            source_num=0,
            target_type=target_type,
            target_num=0,
            cmd_id=cmd_id,
            data=data
        )
        
        self.seq_number += 1
        
        # 发送
        if not self.transport.send(packet):
            logger.error(f"发送命令失败: cmd=0x{cmd_id:02x}")
            return None
        
        # 接收响应
        response = self.transport.receive(timeout=2000)
        return response
    
    def query_device_info(self, device_type: int) -> Optional[Dict[str, Any]]:
        """查询设备信息"""
        print(f"\n  📋 查询设备信息: {get_device_name(device_type)}")
        
        response = self.send_command(device_type, CommandID.QUERY_DEVICE_INFO)
        
        if response and response.data:
            # 解析设备信息
            info = self._parse_device_info(response.data)
            return info
        
        return None
    
    def _parse_device_info(self, data: bytes) -> Dict[str, Any]:
        """解析设备信息数据"""
        # 这是基于逆向分析的解析逻辑
        # 实际格式可能需要调整
        
        try:
            if len(data) >= 20:
                # 尝试解析基本信息
                # 格式: [设备型号(2)] [固件版本(4)] [序列号(16)]
                model_code = data[0:2].hex().upper()
                firmware = f"{data[2]}.{data[3]}.{data[4]}.{data[5]}"
                serial_number = data[6:22].decode('ascii', errors='ignore').strip('\x00')
                
                return {
                    'model_code': f'WM-{model_code}',
                    'firmware_version': firmware,
                    'serial_number': serial_number,
                }
        except Exception as e:
            logger.error(f"解析设备信息失败: {e}")
        
        return {'raw_data': data.hex()}
    
    def query_device_status(self, device_type: int) -> Optional[Dict[str, Any]]:
        """查询设备状态"""
        print(f"\n  📊 查询设备状态: {get_device_name(device_type)}")
        
        response = self.send_command(device_type, CommandID.QUERY_DEVICE_STATUS)
        
        if response and response.data:
            status = self._parse_device_status(response.data)
            return status
        
        return None
    
    def _parse_device_status(self, data: bytes) -> Dict[str, Any]:
        """解析设备状态数据"""
        # 基于逆向分析的状态解析
        
        try:
            if len(data) >= 16:
                # 尝试解析状态数据
                # 格式可能包含: 温度、电压、电量、信号强度等
                
                status = {
                    'temperature': data[0] if len(data) > 0 else 0,
                    'voltage': int.from_bytes(data[1:3], 'little') / 100.0 if len(data) >= 3 else 0,
                    'battery_level': data[3] if len(data) > 3 else 0,
                    'signal_strength': data[4] if len(data) > 4 else 0,
                    'flight_time': int.from_bytes(data[5:7], 'little') if len(data) >= 7 else 0,
                    'error_code': int.from_bytes(data[8:10], 'little') if len(data) >= 10 else 0,
                }
                
                return status
        except Exception as e:
            logger.error(f"解析状态失败: {e}")
        
        return {'raw_data': data.hex()}
    
    def diagnose(self):
        """执行完整诊断"""
        print("\n" + "="*60)
        print("  🚁 DJI 设备真实诊断")
        print("="*60)
        
        # 连接设备
        if not self.connect():
            print("\n  ⚠️  无法连接真实设备，将使用模拟数据演示")
            self._demo_mode()
            return
        
        try:
            # 扫描所有设备类型
            device_types = [
                DeviceType.FLIGHT_CONTROLLER,
                DeviceType.CAMERA,
                DeviceType.GIMBAL,
                DeviceType.BATTERY,
                DeviceType.GPS,
                DeviceType.IMU,
            ]
            
            all_devices = []
            
            for device_type in device_types:
                # 查询设备信息
                info = self.query_device_info(device_type)
                
                if info and 'raw_data' not in info:
                    # 设备存在
                    print(f"  ✅ 发现设备: {get_device_name(device_type)}")
                    print(f"     型号: {info.get('model_code', 'Unknown')}")
                    print(f"     固件: {info.get('firmware_version', 'Unknown')}")
                    print(f"     序列号: {info.get('serial_number', 'Unknown')}")
                    
                    # 查询状态
                    status = self.query_device_status(device_type)
                    
                    if status and 'raw_data' not in status:
                        print(f"     温度: {status.get('temperature', 0)}°C")
                        print(f"     电量: {status.get('battery_level', 0)}%")
                        print(f"     电压: {status.get('voltage', 0):.2f}V")
                        print(f"     信号: {status.get('signal_strength', 0)}%")
                        
                        # 错误代码
                        error_code = status.get('error_code', 0)
                        if error_code:
                            print(f"     ⚠️  错误代码: 0x{error_code:04x}")
                    
                    all_devices.append({
                        'type': device_type,
                        'info': info,
                        'status': status
                    })
                else:
                    # 设备不存在或无响应
                    pass
            
            if not all_devices:
                print("\n  ⚠️  未发现任何设备")
            else:
                print(f"\n  ✅ 共发现 {len(all_devices)} 个设备")
                
                # 生成诊断报告
                self._generate_report(all_devices)
        
        finally:
            # 断开连接
            if self.transport:
                self.transport.disconnect()
    
    def _demo_mode(self):
        """模拟模式演示"""
        print("\n" + "="*60)
        print("  🎭 模拟模式 - 演示诊断流程")
        print("="*60)
        
        # 模拟设备数据
        demo_devices = [
            {
                'type': DeviceType.FLIGHT_CONTROLLER,
                'info': {
                    'model_code': 'WM170',
                    'model_name': 'Mini 4 Pro',
                    'firmware_version': '01.00.0500',
                    'serial_number': 'DJI-1581F7V2X24CJ0183JSR',
                },
                'status': {
                    'temperature': 52,
                    'voltage': 12.68,
                    'battery_level': 78,
                    'signal_strength': 95,
                    'flight_time': 1250,
                    'error_code': 0,
                }
            }
        ]
        
        for device in demo_devices:
            device_type = device['type']
            info = device['info']
            status = device['status']
            
            print(f"\n  📦 设备: {get_device_name(device_type)}")
            print(f"     型号: {info['model_name']} ({info['model_code']})")
            print(f"     固件: {info['firmware_version']}")
            print(f"     序列号: {info['serial_number']}")
            print(f"\n  📊 状态:")
            print(f"     温度: {status['temperature']}°C")
            print(f"     电量: {status['battery_level']}%")
            print(f"     电压: {status['voltage']:.2f}V")
            print(f"     信号: {status['signal_strength']}%")
            print(f"     飞行时间: {status['flight_time']} 分钟")
            
            # 执行诊断
            result = self.engine.diagnose_device(
                device_info=info,
                status_data=status,
                error_codes=[status['error_code']] if status['error_code'] else []
            )
            
            print(f"\n  🔧 诊断结果:")
            print(f"     状态: {result.get('status', 'Unknown')}")
            
            if result.get('issues'):
                print(f"     问题:")
                for issue in result['issues']:
                    print(f"       - {issue}")
            
            if result.get('recommendations'):
                print(f"     建议:")
                for rec in result['recommendations']:
                    print(f"       - {rec}")
        
        # 保存报告
        self._generate_report(demo_devices)
    
    def _generate_report(self, devices: list):
        """生成诊断报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'devices': devices,
            'summary': {
                'total_devices': len(devices),
                'healthy': sum(1 for d in devices if d.get('status', {}).get('error_code', 0) == 0),
                'warnings': sum(1 for d in devices if d.get('status', {}).get('error_code', 0) != 0),
            }
        }
        
        # 保存报告
        filename = f"/tmp/dji_real_diagnosis_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n  📄 报告已保存: {filename}")


def main():
    """主函数"""
    diagnosis = RealDJIDiagnosis()
    diagnosis.diagnose()


if __name__ == '__main__':
    main()
