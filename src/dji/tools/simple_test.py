#!/usr/bin/env python3
"""
DJI 真实通信测试工具（简化版）
直接测试 USB 通信
"""

import sys
import os

# 添加路径
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


def list_dji_devices():
    """列出所有 DJI 设备"""
    try:
        devices = usb.core.find(find_all=True, idVendor=0x2ca3)
        result = []
        for dev in devices:
            try:
                serial = dev.serial_number
                result.append({
                    'serial': serial,
                    'product_id': dev.idProduct,
                    'device': dev
                })
            except:
                result.append({
                    'serial': f'Device-{dev.idProduct:04x}',
                    'product_id': dev.idProduct,
                    'device': dev
                })
        return result
    except Exception as e:
        logger.error(f"查找设备失败: {e}")
        return []


def test_device_discovery():
    """测试设备发现"""
    print("\n" + "="*60)
    print("  🔍 测试设备发现")
    print("="*60)
    
    devices = list_dji_devices()
    
    if devices:
        print(f"\n  ✅ 发现 {len(devices)} 个 DJI 设备:")
        for i, dev in enumerate(devices, 1):
            print(f"     {i}. {dev['serial']} (PID: 0x{dev['product_id']:04x})")
        return devices
    else:
        print("\n  ❌ 未发现 DJI 设备")
        print("\n  💡 提示:")
        print("     1. 确保无人机已开机")
        print("     2. 确保 USB 已连接")
        print("     3. 确保 DJI Assistant 2 未运行")
        return None


def test_usb_connection(device_info):
    """测试 USB 连接"""
    print("\n" + "="*60)
    print("  🔌 测试 USB 连接")
    print("="*60)
    
    device = device_info['device']
    
    try:
        # 获取设备信息
        print(f"\n  设备信息:")
        try:
            print(f"     制造商: {device.manufacturer}")
            print(f"     产品: {device.product}")
            print(f"     序列号: {device.serial_number}")
        except:
            print("     (信息不可用)")
        
        # 获取配置
        cfg = device.get_active_configuration()
        print(f"\n  配置信息:")
        print(f"     配置值: {cfg.bConfigurationValue}")
        print(f"     接口数量: {cfg.bNumInterfaces}")
        
        # 列出所有接口
        print(f"\n  接口列表:")
        for interface in cfg:
            print(f"     接口 {interface.bInterfaceNumber}: "
                  f"类={interface.bInterfaceClass}, "
                  f"子类={interface.bInterfaceSubClass}, "
                  f"协议={interface.bInterfaceProtocol}")
            
            # 列出端点
            for endpoint in interface:
                addr = endpoint.bEndpointAddress
                direction = "IN" if addr & 0x80 else "OUT"
                print(f"        端点 0x{addr:02x} ({direction}): "
                      f"最大包大小={endpoint.wMaxPacketSize}")
        
        return True
        
    except usb.core.USBError as e:
        logger.error(f"USB 错误: {e}")
        return False


def test_interface_claim(device_info, interface_num=5):
    """测试接口占用"""
    print("\n" + "="*60)
    print(f"  🔐 测试接口占用 (接口 {interface_num})")
    print("="*60)
    
    device = device_info['device']
    
    try:
        # 检查内核驱动
        if device.is_kernel_driver_active(interface_num):
            print(f"\n  ⚠️  内核驱动已激活")
            
            try:
                device.detach_kernel_driver(interface_num)
                print(f"  ✅ 已解除内核驱动")
            except usb.core.USBError as e:
                print(f"  ❌ 无法解除内核驱动: {e}")
                print(f"\n  💡 需要 root 权限:")
                print(f"     sudo python3 simple_test.py")
                return False
        
        # 设置配置
        device.set_configuration()
        print(f"\n  ✅ 配置设置成功")
        
        # 占用接口
        usb.util.claim_interface(device, interface_num)
        print(f"  ✅ 接口占用成功")
        
        # 释放接口
        usb.util.release_interface(device, interface_num)
        print(f"  ✅ 接口释放成功")
        
        return True
        
    except usb.core.USBError as e:
        logger.error(f"USB 错误: {e}")
        return False


def test_bulk_transfer(device_info, interface_num=5):
    """测试 Bulk 传输"""
    print("\n" + "="*60)
    print(f"  📦 测试 Bulk 传输")
    print("="*60)
    
    device = device_info['device']
    
    try:
        # 解除内核驱动
        if device.is_kernel_driver_active(interface_num):
            device.detach_kernel_driver(interface_num)
        
        # 设置配置
        device.set_configuration()
        
        # 占用接口
        usb.util.claim_interface(device, interface_num)
        
        # 获取端点
        cfg = device.get_active_configuration()
        interface = cfg[(interface_num, 0)]
        
        endpoint_in = None
        endpoint_out = None
        
        for endpoint in interface:
            addr = endpoint.bEndpointAddress
            if addr & 0x80:
                endpoint_in = addr
            else:
                endpoint_out = addr
        
        print(f"\n  端点:")
        print(f"     输入: 0x{endpoint_in:02x}" if endpoint_in else "     输入: 未找到")
        print(f"     输出: 0x{endpoint_out:02x}" if endpoint_out else "     输出: 未找到")
        
        if endpoint_out:
            # 发送测试数据包
            # DJI 数据包格式: 55 AA [长度2字节] [版本1字节] [序列号2字节] ...
            test_packet = bytes([
                0x55, 0xAA,  # 头部
                0x0A, 0x00,  # 长度 (10 字节)
                0x00,        # 版本
                0x01, 0x00,  # 序列号
                0x10,        # 源设备类型 (PC)
                0x00,        # 源设备编号
                0x0A,        # 目标设备类型 (飞控)
                0x00,        # 目标设备编号
                0x88,        # 命令ID (查询设备信息)
                0x00, 0x00   # CRC (占位)
            ])
            
            print(f"\n  📤 发送测试数据包:")
            print(f"     {' '.join(f'{b:02x}' for b in test_packet)}")
            
            try:
                bytes_written = device.write(endpoint_out, test_packet, timeout=2000)
                print(f"\n  ✅ 发送成功: {bytes_written} 字节")
                
                # 尝试接收响应
                if endpoint_in:
                    print(f"\n  📥 等待响应...")
                    try:
                        data = device.read(endpoint_in, 4096, timeout=3000)
                        print(f"  ✅ 接收到 {len(data)} 字节:")
                        print(f"     {' '.join(f'{b:02x}' for b in data[:20])}")
                    except usb.core.USBError as e:
                        if e.errno == 110:
                            print(f"  ⚠️  接收超时（设备可能需要特定的握手协议）")
                        else:
                            print(f"  ❌ 接收失败: {e}")
                
            except usb.core.USBError as e:
                print(f"  ❌ 发送失败: {e}")
        
        # 释放接口
        usb.util.release_interface(device, interface_num)
        
        return True
        
    except usb.core.USBError as e:
        logger.error(f"USB 错误: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("  🚀 DJI 真实通信测试（简化版）")
    print("="*60)
    
    # 检查权限
    if os.geteuid() != 0:
        print("\n  ⚠️  警告: 未获得 root 权限")
        print("  某些操作可能需要 sudo 权限")
    
    # 1. 测试设备发现
    devices = test_device_discovery()
    
    if not devices:
        print("\n  ❌ 未找到设备，测试结束")
        return
    
    # 使用第一个设备
    device_info = devices[0]
    
    # 2. 测试 USB 连接
    if not test_usb_connection(device_info):
        print("\n  ❌ USB 连接失败")
        return
    
    # 3. 测试接口占用
    if not test_interface_claim(device_info):
        print("\n  ❌ 接口占用失败")
        return
    
    # 4. 测试 Bulk 传输
    test_bulk_transfer(device_info)
    
    print("\n" + "="*60)
    print("  ✅ 测试完成")
    print("="*60)


if __name__ == '__main__':
    main()
