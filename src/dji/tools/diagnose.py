#!/usr/bin/env python3
"""
DJI 设备诊断工具
检查设备状态和可用通信方式
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import usb.core
import usb.util

def check_dji_assistant():
    """检查 DJI Assistant 是否在运行"""
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    
    dji_processes = [line for line in lines if 'dji' in line.lower() and 'grep' not in line.lower()]
    
    if dji_processes:
        print("\n⚠️  检测到 DJI 相关进程:")
        for proc in dji_processes:
            print(f"  {proc}")
        return True
    else:
        print("\n✅ 未检测到 DJI Assistant 进程")
        return False

def check_usb_device():
    """检查 USB 设备状态"""
    print("\n" + "="*60)
    print("  USB 设备信息")
    print("="*60)
    
    device = usb.core.find(idVendor=0x2ca3)
    if not device:
        print("  ❌ 未找到 DJI 设备")
        return None
    
    serial = usb.util.get_string(device, device.iSerialNumber) if device.iSerialNumber else 'Unknown'
    manufacturer = usb.util.get_string(device, device.iManufacturer) if device.iManufacturer else 'Unknown'
    product = usb.util.get_string(device, device.iProduct) if device.iProduct else 'Unknown'
    
    print(f"\n  制造商: {manufacturer}")
    print(f"  产品: {product}")
    print(f"  序列号: {serial}")
    print(f"  VID:PID: 0x{device.idVendor:04X}:0x{device.idProduct:04X}")
    
    # 检查配置
    print(f"\n  配置数: {device.bNumConfigurations}")
    print(f"  当前配置: {device.get_active_configuration().bConfigurationValue}")
    
    # 检查接口
    cfg = device.get_active_configuration()
    print(f"\n  接口数: {cfg.bNumInterfaces}")
    
    for intf in cfg:
        print(f"\n    接口 {intf.bInterfaceNumber}:")
        print(f"      类别: 0x{intf.bInterfaceClass:02X}")
        print(f"      子类别: 0x{intf.bInterfaceSubClass:02X}")
        print(f"      协议: 0x{intf.bInterfaceProtocol:02X}")
        print(f"      端点数: {intf.bNumEndpoints}")
        
        # 检查驱动
        try:
            if device.is_kernel_driver_active(intf.bInterfaceNumber):
                print(f"      驱动: 已附加")
            else:
                print(f"      驱动: 未附加")
        except:
            print(f"      驱动: 检查失败")
    
    return device

def check_network_interfaces():
    """检查网络接口"""
    print("\n" + "="*60)
    print("  网络接口")
    print("="*60)
    
    result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
    print(result.stdout)
    
    # 检查是否有 RNDIS 接口
    if 'enx' in result.stdout or 'usb' in result.stdout:
        print("  ✅ 检测到 USB 网络接口")
    else:
        print("  ⚠️  未检测到 USB 网络接口")

def check_kernel_messages():
    """检查内核消息"""
    print("\n" + "="*60)
    print("  内核消息 (最近20条)")
    print("="*60 + "\n")
    
    result = subprocess.run(['dmesg'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    
    # 过滤 DJI 相关消息
    dji_messages = [line for line in lines if '2ca3' in line or 'DJI' in line or 'dji' in line.lower()]
    
    if dji_messages:
        for msg in dji_messages[-20:]:
            print(f"  {msg}")
    else:
        print("  无 DJI 相关消息")

def suggest_solution():
    """建议解决方案"""
    print("\n" + "="*60)
    print("  建议解决方案")
    print("="*60 + "\n")
    
    print("  1. 关闭 DJI Assistant 2 (如果正在运行)")
    print("     killall DJI\\ Assistant\\ 2")
    print()
    print("  2. 重新插拔设备")
    print()
    print("  3. 检查设备模式:")
    print("     - 某些 DJI 设备需要特定按键组合进入升级模式")
    print("     - Mini SE: 连接后自动识别")
    print("     - 其他型号: 可能需要开机状态下连接")
    print()
    print("  4. 尝试使用 USB 重置:")
    print("     sudo usbreset \"DJI\"")
    print()
    print("  5. 检查 udev 规则:")
    print("     ls -la /etc/udev/rules.d/ | grep dji")
    print()

def main():
    print("\n" + "="*60)
    print("  🔍 DJI 设备诊断工具")
    print("="*60)
    
    # 检查 DJI Assistant
    check_dji_assistant()
    
    # 检查 USB 设备
    device = check_usb_device()
    
    # 检查网络接口
    check_network_interfaces()
    
    # 检查内核消息
    check_kernel_messages()
    
    # 建议解决方案
    suggest_solution()
    
    print("="*60)
    print("  诊断完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
