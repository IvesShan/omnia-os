#!/usr/bin/env python3
"""
DJI 通信模块测试脚本
测试USB和串口连接功能
"""

import sys
import logging
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dji import (
    DJIDeviceManager,
    DeviceType,
    list_dji_devices,
    SerialTransport,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_list_devices():
    """测试设备列表"""
    print("\n" + "="*60)
    print("1. 扫描可用设备")
    print("="*60)
    
    # 列出USB设备
    print("\nUSB设备:")
    usb_devices = list_dji_devices()
    if usb_devices:
        for i, dev in enumerate(usb_devices, 1):
            print(f"  {i}. {dev.get('product', 'Unknown')}")
            print(f"     Vendor ID: {dev.get('vendor_id')}")
            print(f"     Product ID: {dev.get('product_id')}")
            print(f"     序列号: {dev.get('serial_number', 'N/A')}")
    else:
        print("  未找到DJI USB设备")
    
    # 列出串口
    print("\n串口设备:")
    serial_ports = SerialTransport.find_dji_ports()
    if serial_ports:
        for i, port in enumerate(serial_ports, 1):
            print(f"  {i}. {port}")
    else:
        print("  未找到DJI串口设备")
    
    # 列出所有串口
    print("\n所有串口:")
    all_ports = SerialTransport.list_ports()
    for i, port in enumerate(all_ports, 1):
        print(f"  {i}. {port['device']} - {port['description']}")


def test_usb_connection():
    """测试USB连接"""
    print("\n" + "="*60)
    print("2. 测试USB连接")
    print("="*60)
    
    manager = DJIDeviceManager()
    
    try:
        print("\n正在连接USB设备...")
        if manager.connect_usb():
            print("✓ USB连接成功")
            
            print("\n正在扫描设备...")
            devices = manager.scan_devices()
            
            if devices:
                print(f"\n发现 {len(devices)} 个设备:")
                print(manager.get_device_summary())
            else:
                print("未发现设备")
            
            # 启动心跳
            print("\n启动心跳...")
            manager.start_heartbeat()
            
            import time
            print("心跳运行中，5秒后停止...")
            time.sleep(5)
            
            manager.stop_heartbeat()
        else:
            print("✗ USB连接失败")
    
    except Exception as e:
        print(f"✗ 错误: {e}")
        logger.exception("USB连接测试失败")
    
    finally:
        manager.disconnect()


def test_serial_connection():
    """测试串口连接"""
    print("\n" + "="*60)
    print("3. 测试串口连接")
    print("="*60)
    
    manager = DJIDeviceManager()
    
    try:
        print("\n正在连接串口设备...")
        if manager.connect_serial():
            print("✓ 串口连接成功")
            
            print("\n正在扫描设备...")
            devices = manager.scan_devices()
            
            if devices:
                print(f"\n发现 {len(devices)} 个设备:")
                print(manager.get_device_summary())
            else:
                print("未发现设备")
        else:
            print("✗ 串口连接失败")
    
    except Exception as e:
        print(f"✗ 错误: {e}")
        logger.exception("串口连接测试失败")
    
    finally:
        manager.disconnect()


def test_protocol():
    """测试协议"""
    print("\n" + "="*60)
    print("4. 测试协议")
    print("="*60)
    
    from dji import V1Protocol, DJIPacket
    
    protocol = V1Protocol()
    
    # 测试构建查询设备信息命令
    print("\n构建查询设备信息命令:")
    packet = protocol.build_query_device_info(DeviceType.FLIGHT_CONTROLLER, 0)
    print(f"  目标: 飞控")
    print(f"  序列号: {packet.seq_number}")
    print(f"  数据: {packet.to_bytes().hex()}")
    
    # 测试构建心跳包
    print("\n构建心跳包:")
    heartbeat = protocol.build_heartbeat()
    print(f"  数据: {heartbeat.to_bytes().hex()}")
    
    # 测试设备名称映射
    print("\n设备型号映射:")
    from dji import get_device_name
    models = ['wm161', 'wm231', 'wm240', 'rc430', 'wa140']
    for model in models:
        print(f"  {model} -> {get_device_name(model)}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("DJI 通信模块测试")
    print("="*60)
    
    # 测试设备列表
    test_list_devices()
    
    # 测试协议
    test_protocol()
    
    # 测试USB连接
    try:
        test_usb_connection()
    except Exception as e:
        logger.error(f"USB测试失败: {e}")
    
    # 测试串口连接
    try:
        test_serial_connection()
    except Exception as e:
        logger.error(f"串口测试失败: {e}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == '__main__':
    main()
