#!/usr/bin/env python3
"""
DJI 设备信息获取工具
通过USB连接获取设备详细信息
"""

import sys
import time
import usb.core
import usb.util

# DJI USB参数
DJI_VENDOR_ID = 0x2ca3
DJI_PRODUCT_ID = 0x0020

# 工作接口
WORKING_INTERFACE = 4

class DJIDeviceInfo:
    """DJI设备信息获取器"""
    
    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        
    def connect(self):
        """连接设备"""
        print("[1] 搜索DJI设备...")
        self.dev = usb.core.find(idVendor=DJI_VENDOR_ID, idProduct=DJI_PRODUCT_ID)
        
        if self.dev is None:
            print("❌ 未找到设备")
            return False
        
        print(f"✅ 找到设备: {usb.util.get_string(self.dev, self.dev.iProduct)}")
        
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
    
    def send_command(self, cmd_id, payload=b''):
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
            
            response = self.ep_in.read(512, timeout=1000)
            return bytes(response)
        except Exception as e:
            print(f"   通信错误: {e}")
            return None
    
    def get_device_info(self):
        """获取设备信息"""
        print("\n[2] 查询设备信息...")
        
        # 查询设备信息命令
        response = self.send_command(0x88)
        
        if response:
            print(f"   收到响应: {len(response)} 字节")
            return self.parse_device_info(response)
        
        return None
    
    def parse_device_info(self, data):
        """解析设备信息"""
        info = {}
        
        if len(data) >= 10:
            info['device_type'] = data[5]
            info['cmd_id'] = (data[7] << 8) | data[6]
            
            if len(data) > 10:
                payload = data[10:]
                info['payload'] = payload.hex()
                
                # 尝试提取字符串信息
                try:
                    # 查找可打印字符
                    printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in payload)
                    info['printable'] = printable
                except Exception:
                    pass
        
        return info
    
    def monitor(self, duration=10):
        """监控设备数据流"""
        print(f"\n[3] 监控设备数据流 ({duration}秒)...")
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration:
            try:
                data = self.ep_in.read(512, timeout=500)
                if data:
                    packet_count += 1
                    print(f"   [{packet_count}] {len(data)} 字节: {bytes(data[:20]).hex()}...")
            except Exception:
                pass
        
        print(f"   共收到 {packet_count} 个数据包")
    
    def run(self):
        """运行设备信息获取"""
        print("=" * 60)
        print("DJI 设备信息获取工具")
        print("=" * 60)
        
        if not self.connect():
            return 1
        
        # 获取设备信息
        info = self.get_device_info()
        
        if info:
            print("\n设备信息:")
            print(f"  设备类型: 0x{info.get('device_type', 0):02x}")
            if 'payload' in info:
                print(f"  负载数据: {info['payload']}")
            if 'printable' in info:
                print(f"  可打印: {info['printable']}")
        
        # 监控数据流
        self.monitor(5)
        
        print("\n" + "=" * 60)
        print("完成!")
        print("=" * 60)
        
        return 0

if __name__ == "__main__":
    tool = DJIDeviceInfo()
    sys.exit(tool.run())
