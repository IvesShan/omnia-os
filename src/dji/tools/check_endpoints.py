#!/usr/bin/env python3
"""
检查 DJI 设备的所有端点
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import usb.core
import usb.util

def main():
    print("\n" + "="*60)
    print("  🔍 DJI 设备端点检查")
    print("="*60 + "\n")
    
    # 查找设备
    device = usb.core.find(idVendor=0x2ca3)
    if not device:
        print("  ❌ 未找到 DJI 设备")
        return
    
    # 获取设备信息
    serial = usb.util.get_string(device, device.iSerialNumber) if device.iSerialNumber else 'Unknown'
    manufacturer = usb.util.get_string(device, device.iManufacturer) if device.iManufacturer else 'Unknown'
    product = usb.util.get_string(device, device.iProduct) if device.iProduct else 'Unknown'
    
    print(f"设备信息:")
    print(f"  制造商: {manufacturer}")
    print(f"  产品: {product}")
    print(f"  序列号: {serial}")
    print(f"  VID: 0x{device.idVendor:04X}")
    print(f"  PID: 0x{device.idProduct:04X}")
    print()
    
    # 遍历所有配置
    for cfg_idx, cfg in enumerate(device):
        print(f"配置 {cfg_idx}:")
        print(f"  配置值: {cfg.bConfigurationValue}")
        print(f"  接口数: {cfg.bNumInterfaces}")
        print()
        
        # 遍历所有接口
        for intf_idx, intf in enumerate(cfg):
            print(f"  接口 {intf_idx}:")
            print(f"    接口号: {intf.bInterfaceNumber}")
            print(f"    类别: 0x{intf.bInterfaceClass:02X}")
            print(f"    子类别: 0x{intf.bInterfaceSubClass:02X}")
            print(f"    协议: 0x{intf.bInterfaceProtocol:02X}")
            print(f"    端点数: {intf.bNumEndpoints}")
            print()
            
            # 遍历所有端点
            for ep_idx, ep in enumerate(intf):
                print(f"    端点 {ep_idx}:")
                print(f"      地址: 0x{ep.bEndpointAddress:02X}")
                print(f"      方向: {'IN' if ep.bEndpointAddress & 0x80 else 'OUT'}")
                print(f"      类型: {['控制', '等时', '批量', '中断'][ep.bmAttributes & 0x03]}")
                print(f"      最大包大小: {ep.wMaxPacketSize}")
                print(f"      轮询间隔: {ep.bInterval}")
                print()
    
    print("="*60)
    print("  检查完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
