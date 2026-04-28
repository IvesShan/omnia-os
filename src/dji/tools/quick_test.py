#!/usr/bin/env python3
"""
DJI 设备快速测试工具
最简单的使用方式
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import usb.core
import usb.util
import struct
import time


def calculate_crc(data):
    """计算 CRC16"""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def create_packet(cmd, seq=0):
    """创建数据包"""
    packet = bytearray()
    packet.extend([0x55, 0xAA])
    packet.extend(struct.pack('<H', 10))
    packet.append(0x00)
    packet.extend(struct.pack('<H', seq))
    packet.extend([0x10, 0x00, 0x0A, 0x00, cmd])
    
    crc = calculate_crc(packet[2:])
    packet.extend(struct.pack('<H', crc))
    
    return bytes(packet)


def main():
    print("\n" + "="*60)
    print("  🚁 DJI 设备快速测试")
    print("="*60 + "\n")
    
    # 查找设备
    print("1. 查找设备...")
    device = usb.core.find(idVendor=0x2ca3)
    if not device:
        print("   ❌ 未找到 DJI 设备\n")
        return
    
    serial = usb.util.get_string(device, device.iSerialNumber) if device.iSerialNumber else 'Unknown'
    print(f"   ✅ 找到设备: {serial}\n")
    
    # 初始化
    print("2. 初始化设备...")
    for cfg in device:
        for intf in cfg:
            try:
                if device.is_kernel_driver_active(intf.bInterfaceNumber):
                    device.detach_kernel_driver(intf.bInterfaceNumber)
            except Exception:
                pass
    
    device.reset()
    time.sleep(1)
    print("   ✅ 初始化完成\n")
    
    # 测试通信
    print("3. 测试通信...\n")
    
    commands = [
        ("心跳", 0xEA),
        ("查询设备信息", 0x88),
        ("查询状态", 0x0C),
    ]
    
    for i, (name, cmd) in enumerate(commands):
        print(f"   [{i+1}/{len(commands)}] {name}...")
        
        packet = create_packet(cmd, seq=i)
        
        try:
            # 发送
            sent = device.write(0x04, packet, timeout=1000)
            
            # 接收
            time.sleep(0.1)
            data = device.read(0x85, 512, timeout=2000)
            
            print(f"      ✅ 成功: 发送 {sent} 字节, 接收 {len(data)} 字节")
            print(f"      发送: {packet.hex()}")
            print(f"      接收: {bytes(data).hex()}\n")
            
        except Exception as e:
            print(f"      ❌ 失败: {e}\n")
        
        time.sleep(0.3)
    
    print("="*60)
    print("  测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  ❌ 错误: {e}\n")
