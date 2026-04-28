#!/usr/bin/env python3
"""
DJI 实际设备测试脚本
测试连接到真实的DJI设备
"""

import sys
import usb.core
import usb.util

# DJI USB参数
DJI_VENDOR_ID = 0x2ca3
DJI_PRODUCT_ID = 0x0020

def test_device_connection():
    """测试设备连接"""
    print("=" * 60)
    print("DJI 设备连接测试")
    print("=" * 60)
    
    # 查找设备
    print("\n[1] 搜索DJI设备...")
    dev = usb.core.find(idVendor=DJI_VENDOR_ID, idProduct=DJI_PRODUCT_ID)
    
    if dev is None:
        print("❌ 未找到DJI设备")
        return False
    
    print(f"✅ 找到设备: {dev}")
    print(f"   制造商: {usb.util.get_string(dev, dev.iManufacturer)}")
    print(f"   产品: {usb.util.get_string(dev, dev.iProduct)}")
    print(f"   序列号: {usb.util.get_string(dev, dev.iSerialNumber)}")
    
    # 显示配置
    print("\n[2] 设备配置信息:")
    for cfg in dev:
        print(f"   配置 {cfg.bConfigurationValue}: {usb.util.get_string(dev, cfg.iConfiguration)}")
        for intf in cfg:
            print(f"     接口 {intf.bInterfaceNumber}: {usb.util.get_string(dev, intf.iInterface)}")
            for ep in intf:
                print(f"       端点 {hex(ep.bEndpointAddress)}: {ep.bmAttributes}")
    
    return True

def test_interface_access(dev, interface_num):
    """测试接口访问"""
    print(f"\n[3] 测试接口 {interface_num} 访问...")
    
    try:
        # 获取活动配置
        cfg = dev.get_active_configuration()
        intf = cfg[(interface_num, 0)]
        
        # 查找端点
        ep_out = None
        ep_in = None
        
        for ep in intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                ep_out = ep
            else:
                ep_in = ep
        
        if ep_out and ep_in:
            print(f"   ✅ 找到端点:")
            print(f"      OUT: {hex(ep_out.bEndpointAddress)}")
            print(f"      IN: {hex(ep_in.bEndpointAddress)}")
            return ep_out, ep_in
        else:
            print(f"   ❌ 未找到端点对")
            return None, None
            
    except Exception as e:
        print(f"   ❌ 访问失败: {e}")
        return None, None

def test_communication(ep_out, ep_in):
    """测试基本通信"""
    print("\n[4] 测试基本通信...")
    
    # DJI心跳包
    heartbeat = bytes([
        0x55, 0xAA,  # 起始标志
        0x00,        # 版本
        0x00,        # 长度低字节
        0x00,        # 长度高字节
        0x00,        # 命令集
        0xEA,        # 命令ID (心跳)
        0x00, 0x00,  # 序列号
        0x00, 0x00   # CRC (简化)
    ])
    
    try:
        print(f"   发送心跳包: {heartbeat.hex()}")
        ep_out.write(heartbeat)
        print("   ✅ 发送成功")
        
        # 尝试读取响应
        print("   等待响应...")
        try:
            response = ep_in.read(64, timeout=1000)
            print(f"   ✅ 收到响应: {bytes(response).hex()}")
            return True
        except usb.core.USBError as e:
            print(f"   ⚠️  无响应 (超时): {e}")
            return False
            
    except Exception as e:
        print(f"   ❌ 通信失败: {e}")
        return False

def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("DJI 设备通信测试")
    print("=" * 60)
    
    # 1. 查找设备
    dev = usb.core.find(idVendor=DJI_VENDOR_ID, idProduct=DJI_PRODUCT_ID)
    if dev is None:
        print("\n❌ 未找到DJI设备!")
        print("\n请检查:")
        print("  1. 设备是否已连接")
        print("  2. lsusb 是否能看到设备")
        print("  3. 是否有权限访问")
        return 1
    
    print(f"\n✅ 找到设备: {usb.util.get_string(dev, dev.iProduct)}")
    
    # 2. 尝试detach内核驱动
    print("\n[2] 配置设备...")
    for cfg in dev:
        for intf in cfg:
            if intf.bInterfaceClass == 0xFF:  # Vendor Specific
                try:
                    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                        print(f"   Detach内核驱动: 接口 {intf.bInterfaceNumber}")
                        dev.detach_kernel_driver(intf.bInterfaceNumber)
                except Exception as e:
                    print(f"   ⚠️  接口 {intf.bInterfaceNumber}: {e}")
    
    # 3. 设置配置
    try:
        dev.set_configuration()
        print("   ✅ 配置设置成功")
    except Exception as e:
        print(f"   ⚠️  配置设置失败: {e}")
    
    # 4. 测试各个BULK接口
    print("\n[3] 测试BULK接口...")
    cfg = dev.get_active_configuration()
    
    for intf in cfg:
        if intf.bInterfaceClass == 0xFF:  # Vendor Specific
            print(f"\n   测试接口 {intf.bInterfaceNumber}:")
            
            # 查找端点
            ep_out = None
            ep_in = None
            for ep in intf:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    ep_out = ep
                    print(f"     OUT端点: {hex(ep.bEndpointAddress)}")
                else:
                    ep_in = ep
                    print(f"     IN端点: {hex(ep.bEndpointAddress)}")
            
            if ep_out and ep_in:
                # 尝试通信
                try:
                    # 发送简单的查询
                    test_data = bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x88, 0x00, 0x00, 0x00, 0x00])
                    ep_out.write(test_data)
                    print(f"     ✅ 发送成功")
                    
                    # 读取响应
                    try:
                        response = ep_in.read(512, timeout=500)
                        print(f"     ✅ 收到响应: {len(response)} 字节")
                        print(f"        数据: {bytes(response[:32]).hex()}...")
                    except Exception:
                        print(f"     ⚠️  无响应")
                        
                except Exception as e:
                    print(f"     ❌ 通信失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
