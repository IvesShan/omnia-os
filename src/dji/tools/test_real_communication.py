#!/usr/bin/env python3
"""
DJI 真实通信测试工具
测试 USB 通信和协议解析
"""

import sys
import os
import logging

# 添加父目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from protocols.v1_protocol import (
    DJIPacket, DeviceType, CommandID, V1Protocol, get_device_name
)
from transport.usb_transport_complete import USBTransport, USBConfig, list_dji_devices

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_device_discovery():
    """测试设备发现"""
    print("\n" + "="*60)
    print("  🔍 测试设备发现")
    print("="*60)
    
    devices = list_dji_devices()
    
    if devices:
        print(f"\n  ✅ 发现 {len(devices)} 个 DJI 设备:")
        for i, dev in enumerate(devices, 1):
            print(f"     {i}. {dev}")
        return True
    else:
        print("\n  ❌ 未发现 DJI 设备")
        print("\n  💡 提示:")
        print("     1. 确保无人机已开机")
        print("     2. 确保 USB 已连接")
        print("     3. 确保 DJI Assistant 2 未运行")
        return False


def test_usb_connection():
    """测试 USB 连接"""
    print("\n" + "="*60)
    print("  🔌 测试 USB 连接")
    print("="*60)
    
    transport = USBTransport()
    
    if transport.connect():
        print("\n  ✅ USB 连接成功！")
        transport.disconnect()
        return True
    else:
        print("\n  ❌ USB 连接失败")
        print("\n  💡 可能的原因:")
        print("     1. 需要 root 权限: sudo python3 test_real_communication.py")
        print("     2. 设备被其他程序占用（DJI Assistant 2）")
        print("     3. USB 驱动问题")
        return False


def test_protocol_parsing():
    """测试协议解析"""
    print("\n" + "="*60)
    print("  📦 测试协议解析")
    print("="*60)
    
    # 创建测试数据包
    packet = DJIPacket(
        seq_number=1,
        source_type=DeviceType.PC,
        source_num=0,
        target_type=DeviceType.FLIGHT_CONTROLLER,
        target_num=0,
        cmd_id=CommandID.QUERY_DEVICE_INFO,
        data=b'\x00\x01\x02\x03'
    )
    
    print(f"\n  📤 创建数据包:")
    print(f"     命令: 0x{packet.cmd_id:02x} (查询设备信息)")
    print(f"     目标: {get_device_name(packet.target_type)}")
    print(f"     序列号: {packet.seq_number}")
    
    # 转换为字节
    data = packet.to_bytes()
    print(f"\n  📊 数据包字节 ({len(data)} 字节):")
    print(f"     {' '.join(f'{b:02x}' for b in data[:20])} ...")
    
    # 解析回来
    parsed = DJIPacket.from_bytes(data)
    
    if parsed:
        print(f"\n  ✅ 解析成功:")
        print(f"     命令: 0x{parsed.cmd_id:02x}")
        print(f"     目标: {get_device_name(parsed.target_type)}")
        print(f"     CRC: 0x{parsed.crc:04x}")
        return True
    else:
        print("\n  ❌ 解析失败")
        return False


def test_real_communication():
    """测试真实通信"""
    print("\n" + "="*60)
    print("  🚁 测试真实通信")
    print("="*60)
    
    transport = USBTransport()
    
    if not transport.connect():
        print("\n  ❌ 无法连接设备")
        return False
    
    try:
        # 测试查询设备信息
        print("\n  📋 查询飞控信息...")
        
        packet = DJIPacket(
            seq_number=1,
            source_type=DeviceType.PC,
            source_num=0,
            target_type=DeviceType.FLIGHT_CONTROLLER,
            target_num=0,
            cmd_id=CommandID.QUERY_DEVICE_INFO,
            data=b''
        )
        
        response = transport.send_and_receive(packet, timeout=3000)
        
        if response:
            print(f"\n  ✅ 收到响应:")
            print(f"     命令: 0x{response.cmd_id:02x}")
            print(f"     源设备: {get_device_name(response.source_type)}")
            
            if response.data:
                print(f"     数据长度: {len(response.data)} 字节")
                print(f"     数据: {' '.join(f'{b:02x}' for b in response.data[:20])}")
            else:
                print(f"     无数据")
            
            return True
        else:
            print("\n  ❌ 未收到响应")
            print("\n  💡 可能的原因:")
            print("     1. 设备类型不正确")
            print("     2. 命令格式不正确")
            print("     3. 需要先发送握手/心跳包")
            return False
    
    finally:
        transport.disconnect()


def test_with_sudo():
    """测试 sudo 权限"""
    print("\n" + "="*60)
    print("  🔐 测试权限")
    print("="*60)
    
    if os.geteuid() == 0:
        print("\n  ✅ 已获得 root 权限")
        return True
    else:
        print("\n  ⚠️  未获得 root 权限")
        print("\n  💡 使用以下命令运行:")
        print("     sudo python3 test_real_communication.py")
        return False


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("  🚀 DJI 真实通信测试")
    print("="*60)
    
    results = {
        '设备发现': False,
        '协议解析': False,
        '权限检查': False,
        'USB连接': False,
        '真实通信': False,
    }
    
    # 1. 测试设备发现
    results['设备发现'] = test_device_discovery()
    
    # 2. 测试协议解析
    results['协议解析'] = test_protocol_parsing()
    
    # 3. 检查权限
    results['权限检查'] = test_with_sudo()
    
    # 4. 测试 USB 连接
    if results['设备发现']:
        results['USB连接'] = test_usb_connection()
    
    # 5. 测试真实通信
    if results['USB连接']:
        results['真实通信'] = test_real_communication()
    
    # 总结
    print("\n" + "="*60)
    print("  📊 测试总结")
    print("="*60)
    
    for test, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test}: {status}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n  总计: {passed_count}/{total_count} 通过")
    
    if passed_count == total_count:
        print("\n  🎉 所有测试通过！可以开始真实通信了！")
    elif results['设备发现'] and results['协议解析']:
        print("\n  💡 建议:")
        print("     1. 使用 sudo 运行以获得 USB 访问权限")
        print("     2. 关闭 DJI Assistant 2 避免设备冲突")
        print("     3. 检查 USB 线缆连接")


if __name__ == '__main__':
    main()
