#!/usr/bin/env python3
"""
DJI 诊断工具命令行界面
用于连接和诊断DJI无人机
"""

import sys
import argparse
import logging
from pathlib import Path
import time

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dji import (
    DJIDeviceManager,
    DeviceType,
    list_dji_devices,
    SerialTransport,
    get_device_name,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_scan(args):
    """扫描设备"""
    print("\n📡 扫描DJI设备...\n")
    
    # USB设备
    print("USB设备:")
    usb_devices = list_dji_devices()
    if usb_devices:
        for i, dev in enumerate(usb_devices, 1):
            print(f"  [{i}] {dev.get('product', 'Unknown')}")
            print(f"      Vendor ID: {dev.get('vendor_id')}")
            print(f"      Product ID: {dev.get('product_id')}")
            print(f"      序列号: {dev.get('serial_number', 'N/A')}")
    else:
        print("  未找到设备")
    
    # 串口设备
    print("\n串口设备:")
    serial_ports = SerialTransport.find_dji_ports()
    if serial_ports:
        for i, port in enumerate(serial_ports, 1):
            print(f"  [{i}] {port}")
    else:
        print("  未找到DJI串口")
    
    # 所有串口
    print("\n所有串口:")
    all_ports = SerialTransport.list_ports()
    for i, port in enumerate(all_ports, 1):
        print(f"  [{i}] {port['device']} - {port['description']}")


def cmd_connect(args):
    """连接设备"""
    manager = DJIDeviceManager()
    
    try:
        # 选择连接方式
        if args.serial:
            print(f"\n🔌 通过串口连接: {args.serial}")
            if not manager.connect_serial(args.serial, args.baudrate):
                print("❌ 串口连接失败")
                return
        else:
            print("\n🔌 通过USB连接...")
            if not manager.connect_usb():
                print("❌ USB连接失败")
                return
        
        print("✅ 连接成功")
        
        # 扫描设备
        print("\n🔍 扫描设备...")
        devices = manager.scan_devices()
        
        if devices:
            print(f"\n发现 {len(devices)} 个设备:\n")
            print(manager.get_device_summary())
        else:
            print("⚠️  未发现设备")
        
        # 如果指定了监控模式
        if args.monitor:
            print("\n📊 监控模式 (Ctrl+C 退出)...\n")
            manager.start_heartbeat(interval=1.0)
            
            try:
                while True:
                    # 更新状态
                    statuses = manager.update_all_status()
                    
                    # 显示状态
                    print("\033[H\033[J", end="")  # 清屏
                    print("📊 设备状态监控\n")
                    print("="*60)
                    
                    for device in manager.connected_devices:
                        print(f"\n【{device.model_name}】")
                        if device.status:
                            if 'temperature' in device.status:
                                print(f"  温度: {device.status['temperature']:.1f}°C")
                            if 'battery_percent' in device.status:
                                print(f"  电量: {device.status['battery_percent']}%")
                            if 'voltage' in device.status:
                                print(f"  电压: {device.status['voltage']:.2f}V")
                            if 'error_code' in device.status:
                                error = device.status['error_code']
                                if error:
                                    print(f"  ⚠️  错误: 0x{error:04x}")
                                else:
                                    print(f"  ✅ 状态正常")
                    
                    time.sleep(1)
            
            except KeyboardInterrupt:
                print("\n\n⏹️  停止监控")
                manager.stop_heartbeat()
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        logger.exception("连接失败")
    
    finally:
        manager.disconnect()
        print("\n👋 已断开连接")


def cmd_info(args):
    """查询设备信息"""
    manager = DJIDeviceManager()
    
    try:
        # 连接
        if args.serial:
            if not manager.connect_serial(args.serial):
                print("❌ 串口连接失败")
                return
        else:
            if not manager.connect_usb():
                print("❌ USB连接失败")
                return
        
        print("✅ 连接成功\n")
        
        # 扫描设备
        devices = manager.scan_devices()
        
        if not devices:
            print("⚠️  未发现设备")
            return
        
        # 显示详细信息
        print("="*60)
        print("📋 设备详细信息")
        print("="*60)
        
        for device in devices:
            print(f"\n【{device.device_type_name}】")
            print(f"  型号代码: {device.model_code}")
            print(f"  产品名称: {device.model_name}")
            print(f"  固件版本: {device.firmware_version}")
            print(f"  序列号: {device.serial_number}")
            
            if device.status:
                print(f"\n  状态信息:")
                for key, value in device.status.items():
                    if key not in ['raw_packet', 'data']:
                        print(f"    {key}: {value}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        logger.exception("查询失败")
    
    finally:
        manager.disconnect()


def cmd_test(args):
    """测试协议"""
    from dji import V1Protocol, DJIPacket, DeviceType
    
    print("\n🧪 协议测试\n")
    
    protocol = V1Protocol()
    
    # 测试各种命令
    print("构建命令:")
    
    commands = [
        ("查询设备信息", protocol.build_query_device_info(DeviceType.FLIGHT_CONTROLLER)),
        ("查询设备状态", protocol.build_query_device_status(DeviceType.FLIGHT_CONTROLLER)),
        ("心跳包", protocol.build_heartbeat()),
        ("进入升级模式", protocol.build_enter_upgrade(DeviceType.FLIGHT_CONTROLLER)),
        ("重启设备", protocol.build_reboot(DeviceType.FLIGHT_CONTROLLER)),
    ]
    
    for name, packet in commands:
        print(f"\n  {name}:")
        print(f"    序列号: {packet.seq_number}")
        print(f"    目标: 0x{packet.target_type:02x}")
        print(f"    命令: 0x{packet.cmd_id:02x}")
        print(f"    数据: {packet.to_bytes().hex()}")
    
    # 设备型号映射
    print("\n\n设备型号映射:")
    from dji import DEVICE_MODEL_MAP
    for code, name in sorted(DEVICE_MODEL_MAP.items())[:10]:
        print(f"  {code}: {name}")
    print("  ...")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='DJI 无人机诊断工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描设备
  python dji_tool.py scan
  
  # USB连接
  python dji_tool.py connect
  
  # 串口连接
  python dji_tool.py connect --serial /dev/ttyUSB0
  
  # 监控模式
  python dji_tool.py connect --monitor
  
  # 查询设备信息
  python dji_tool.py info
  
  # 测试协议
  python dji_tool.py test
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # scan 命令
    parser_scan = subparsers.add_parser('scan', help='扫描设备')
    
    # connect 命令
    parser_connect = subparsers.add_parser('connect', help='连接设备')
    parser_connect.add_argument('--serial', '-s', help='串口设备路径')
    parser_connect.add_argument('--baudrate', '-b', type=int, default=115200, help='波特率')
    parser_connect.add_argument('--monitor', '-m', action='store_true', help='监控模式')
    
    # info 命令
    parser_info = subparsers.add_parser('info', help='查询设备信息')
    parser_info.add_argument('--serial', '-s', help='串口设备路径')
    
    # test 命令
    parser_test = subparsers.add_parser('test', help='测试协议')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'connect':
        cmd_connect(args)
    elif args.command == 'info':
        cmd_info(args)
    elif args.command == 'test':
        cmd_test(args)


if __name__ == '__main__':
    main()
