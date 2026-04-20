#!/usr/bin/env python3
"""
DJI 设备初始化 - 使用控制传输
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import usb.core
import usb.util
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "="*60)
    print("  🔧 DJI 设备初始化测试")
    print("="*60 + "\n")
    
    # 查找设备
    device = usb.core.find(idVendor=0x2ca3)
    if not device:
        print("  ❌ 未找到 DJI 设备\n")
        return
    
    serial = usb.util.get_string(device, device.iSerialNumber) if device.iSerialNumber else 'Unknown'
    print(f"设备: {serial}\n")
    
    # 解除所有接口的内核驱动
    print("解除内核驱动...")
    for cfg in device:
        for intf in cfg:
            interface_number = intf.bInterfaceNumber
            try:
                if device.is_kernel_driver_active(interface_number):
                    device.detach_kernel_driver(interface_number)
                    print(f"  ✅ 接口 {interface_number} 已解除")
            except Exception as e:
                print(f"  ⚠️  接口 {interface_number}: {e}")
    
    time.sleep(0.1)
    
    # 尝试控制传输
    print("\n尝试控制传输初始化...")
    
    # 标准USB控制请求
    control_requests = [
        # 获取设备描述符
        (0x80, 0x06, 0x0100, 0x0000, 18, "GET_DEVICE_DESCRIPTOR"),
        # 获取配置描述符
        (0x80, 0x06, 0x0200, 0x0000, 9, "GET_CONFIG_DESCRIPTOR"),
        # 获取字符串描述符
        (0x80, 0x06, 0x0300, 0x0000, 255, "GET_STRING_DESCRIPTOR"),
        # 设置配置
        (0x00, 0x09, 0x0001, 0x0000, 0, "SET_CONFIGURATION"),
        # 清除特性
        (0x00, 0x01, 0x0000, 0x0000, 0, "CLEAR_FEATURE"),
        # 设置接口
        (0x01, 0x0B, 0x0000, 0x0005, 0, "SET_INTERFACE_5"),
    ]
    
    for bmRequestType, bRequest, wValue, wIndex, wLength, name in control_requests:
        try:
            print(f"\n  {name}:")
            print(f"    bmRequestType: 0x{bmRequestType:02X}")
            print(f"    bRequest: 0x{bRequest:02X}")
            print(f"    wValue: 0x{wValue:04X}")
            print(f"    wIndex: 0x{wIndex:04X}")
            print(f"    wLength: {wLength}")
            
            if wLength > 0:
                result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength)
                print(f"    ✅ 成功: {len(result)} 字节")
                if len(result) <= 32:
                    print(f"    数据: {bytes(result).hex()}")
            else:
                result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength)
                print(f"    ✅ 成功")
            
            time.sleep(0.05)
            
        except Exception as e:
            print(f"    ❌ 失败: {e}")
    
    # 尝试厂商特定请求
    print("\n\n尝试厂商特定请求...")
    
    vendor_requests = [
        # DJI 可能使用的厂商请求
        (0x40, 0xFF, 0x0000, 0x0000, 0, "VENDOR_INIT_1"),
        (0x40, 0xFF, 0x0001, 0x0000, 0, "VENDOR_INIT_2"),
        (0xC0, 0xFF, 0x0000, 0x0000, 64, "VENDOR_QUERY_1"),
        (0xC0, 0xFF, 0x0001, 0x0000, 64, "VENDOR_QUERY_2"),
    ]
    
    for bmRequestType, bRequest, wValue, wIndex, wLength, name in vendor_requests:
        try:
            print(f"\n  {name}:")
            
            if wLength > 0:
                result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength)
                print(f"    ✅ 成功: {len(result)} 字节")
                print(f"    数据: {bytes(result).hex()}")
            else:
                result = device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength)
                print(f"    ✅ 成功")
            
            time.sleep(0.05)
            
        except Exception as e:
            print(f"    ❌ 失败: {e}")
    
    # 尝试批量传输
    print("\n\n尝试批量传输...")
    
    test_data = bytes([0x55, 0xAA, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x0A, 0x00, 0x88, 0x9F, 0x01])
    
    for ep in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]:
        try:
            print(f"\n  端点 0x{ep:02X}:")
            device.write(ep, test_data, timeout=1000)
            print(f"    ✅ 发送成功")
            
            # 尝试读取
            ep_in = ep | 0x80
            try:
                data = device.read(ep_in, 512, timeout=1000)
                print(f"    ✅ 接收成功: {len(data)} 字节")
                print(f"    数据: {data.hex()}")
            except:
                print(f"    ⚠️  无接收")
                
        except Exception as e:
            print(f"    ❌ 失败: {e}")
    
    print("\n" + "="*60)
    print("  测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  用户中断")
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
