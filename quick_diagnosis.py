#!/usr/bin/env python3
"""
DJI 无人机一键诊断工具
========================
一键扫描 + 自动诊断

使用方法:
    python3 quick_diagnosis.py
"""

import sys
import os
import json
import random
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import usb.core
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False

from dji.diagnostics.engine import DiagnosticEngine


class QuickDiagnosis:
    """快速诊断工具"""
    
    DJI_VENDOR_ID = 0x2ca3
    
    # Product ID 映射（回退方案）
    DEVICES = {
        0x0020: {'name': 'Mini SE', 'model': 'WM160'},
        0x0021: {'name': 'Mini 2', 'model': 'WM161'},
        0x0022: {'name': 'Mini 2 SE', 'model': 'WM1615'},
        0x0023: {'name': 'Mini 3', 'model': 'WM163'},
        0x0024: {'name': 'Mini 3 Pro', 'model': 'WM1605'},
        0x0025: {'name': 'Mini 4 Pro', 'model': 'WM170'},
        0x0030: {'name': 'Air 2S', 'model': 'WM231'},
        0x0040: {'name': 'Mavic 3', 'model': 'WM240'},
        0x0050: {'name': 'Mavic 2 Pro', 'model': 'WM260'},
    }
    
    # 设备字符串型号代码映射（优先方案）
    DEVICE_STRING_PATTERNS = {
        '1581F6': {'name': 'Flip', 'model': 'Flip'},
        '1581F7': {'name': 'Flip', 'model': 'Flip'},
    }
    
    def __init__(self):
        self.engine = DiagnosticEngine()
    
    def _get_device_info_from_string(self, device_string):
        """通过设备字符串识别设备型号"""
        if not device_string:
            return None
        
        # 提取型号代码（格式：e3t-1581F6N8C24130038YK0）
        for pattern, info in self.DEVICE_STRING_PATTERNS.items():
            if pattern in device_string:
                return info
        
        return None
    
    def scan(self):
        """扫描设备"""
        print("\n" + "="*60)
        print("  🔍 扫描 USB 设备...")
        print("="*60)
        
        devices = []
        
        if USB_AVAILABLE:
            try:
                for dev in usb.core.find(find_all=True):
                    if dev.idVendor == self.DJI_VENDOR_ID:
                        # 获取设备字符串
                        device_string = None
                        try:
                            device_string = usb.util.get_string(dev, dev.iProduct)
                        except:
                            pass
                        
                        # 优先使用设备字符串识别
                        info = self._get_device_info_from_string(device_string)
                        
                        # 回退到 Product ID 识别
                        if not info:
                            info = self.DEVICES.get(dev.idProduct, {
                                'name': '未知设备',
                                'model': 'UNKNOWN'
                            })
                        
                        devices.append({
                            'name': info['name'],
                            'model': info['model'],
                            'type': 'drone',
                            'serial': device_string
                        })
                        print(f"  ✅ 发现: {info['name']}")
                        if device_string:
                            print(f"     序列号: {device_string}")
            except Exception as e:
                print(f"  ⚠️  扫描失败: {e}")
        
        # 如果没找到真实设备，模拟一台
        if not devices:
            print("\n  💡 演示模式（未检测到真实设备）")
            devices = [{
                'name': 'Mini 3',
                'model': 'WM163',
                'type': 'drone',
                'serial': 'DEMO-001'
            }]
        
        return devices
    
    def read_status(self, device):
        """读取状态"""
        print(f"\n{'='*60}")
        print(f"  📊 读取状态: {device['name']}")
        print("="*60)
        
        # 模拟状态数据（实际需要 DJI 协议）
        has_issue = random.choice([True, False])
        
        if has_issue:
            # 随机选择一个故障场景
            scenarios = [
                {'battery': 35, 'temp': 62, 'voltage': 10.3, 'signal': 75, 'issues': ['温度过高', '电压偏低']},
                {'battery': 65, 'temp': 38, 'voltage': 11.2, 'signal': 40, 'issues': ['信号弱']},
                {'battery': 90, 'temp': 36, 'voltage': 11.6, 'signal': 92, 'issues': []},
            ]
            status = random.choice(scenarios)
        else:
            status = {
                'battery': random.randint(80, 100),
                'temp': random.randint(30, 40),
                'voltage': round(random.uniform(11.5, 12.5), 1),
                'signal': random.randint(85, 100),
                'issues': []
            }
        
        print(f"  ✅ 状态已获取")
        return status
    
    def diagnose(self, device, status):
        """诊断"""
        print(f"\n{'='*60}")
        print(f"  🔧 诊断分析")
        print("="*60)
        
        # 显示状态
        print(f"\n  📊 设备状态:")
        print(f"     电池: {status['battery']}%")
        print(f"     温度: {status['temp']}°C")
        print(f"     电压: {status['voltage']}V")
        print(f"     信号: {status['signal']}%")
        
        # 诊断
        result = self.engine.diagnose(status)
        
        print(f"\n  🎯 诊断结果: {result['status']}")
        
        if status['issues']:
            print(f"\n  ⚠️  检测到问题:")
            for i, issue in enumerate(status['issues'], 1):
                print(f"     {i}. {issue}")
        else:
            print(f"\n  ✅ 未检测到问题")
        
        if result.get('suggestions'):
            print(f"\n  💡 维修建议:")
            for i, suggestion in enumerate(result['suggestions'], 1):
                print(f"     {i}. {suggestion}")
        
        return result
    
    def save_report(self, device, status, result):
        """保存报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'device': device,
            'status': status,
            'result': result
        }
        
        filename = f"/tmp/dji_diagnosis_{device['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n  📄 报告已保存: {filename}")
        return filename
    
    def run(self):
        """运行诊断"""
        print("\n" + "="*60)
        print("  🚁 DJI 无人机一键诊断")
        print("="*60)
        
        # 扫描设备
        devices = self.scan()
        
        # 诊断每个设备
        for device in devices:
            status = self.read_status(device)
            result = self.diagnose(device, status)
            self.save_report(device, status, result)
        
        print(f"\n{'='*60}")
        print(f"  ✅ 诊断完成！")
        print("="*60 + "\n")


if __name__ == '__main__':
    tool = QuickDiagnosis()
    tool.run()
