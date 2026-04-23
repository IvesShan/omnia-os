#!/usr/bin/env python3
"""
真实电池查询工具
基于之前成功的通信协议，查询真实的电池状态
"""

import usb.core
import usb.util
import time

# Air 3S 设备信息
AIR3S_VID = 0x2ca3
AIR3S_PID = 0x0020

# 工作端点（之前测试成功的）
OUT_ENDPOINT = 0x04
IN_ENDPOINT = 0x85

def calculate_crc(data):
    """CRC16 校验算法"""
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

def build_packet(seq, cmd, data=b''):
    """
    构建 DJI 协议数据包
    
    格式:
    [0x55] [0xAA]  - 头部
    [长度 2字节]    - 数据长度
    [版本 1字节]    - 版本号
    [序列号 2字节]  - 包序号
    [源类型 1字节]  - 源设备类型 (0x10 = PC)
    [源编号 1字节]  - 源设备编号
    [目标类型 1字节] - 目标设备类型 (0x0A = 飞控)
    [目标编号 1字节] - 目标设备编号
    [命令ID 1字节]  - 命令标识
    [数据 N字节]    - 负载数据
    [CRC 2字节]     - 校验码
    """
    header = bytes([0x55, 0xAA])
    version = bytes([0x00])
    sequence = seq.to_bytes(2, 'little')
    src_type = bytes([0x10])  # PC
    src_id = bytes([0x00])
    dst_type = bytes([0x0A])  # 飞控
    dst_id = bytes([0x00])
    command = bytes([cmd])
    payload = data
    
    # 计算长度（从版本到命令+数据）
    length = len(version + sequence + src_type + src_id + dst_type + dst_id + command + payload)
    length_bytes = length.to_bytes(2, 'little')
    
    # 组合数据（不含头部和CRC）
    packet_data = length_bytes + version + sequence + src_type + src_id + dst_type + dst_id + command + payload
    
    # 计算CRC
    crc = calculate_crc(packet_data)
    crc_bytes = crc.to_bytes(2, 'little')
    
    # 完整数据包
    packet = header + packet_data + crc_bytes
    
    return packet

def init_device():
    """初始化设备"""
    print("🔍 查找设备...")
    dev = usb.core.find(idVendor=AIR3S_VID, idProduct=AIR3S_PID)
    
    if not dev:
        print("❌ 设备未找到")
        return None
    
    print(f"✅ 设备已找到: {dev}")
    
    # 解除所有内核驱动
    for cfg in dev:
        for intf in cfg:
            if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                try:
                    dev.detach_kernel_driver(intf.bInterfaceNumber)
                    print(f"✅ 已解除接口 {intf.bInterfaceNumber} 的内核驱动")
                except Exception as e:
                    print(f"⚠️ 解除接口 {intf.bInterfaceNumber} 失败: {e}")
    
    # 重置设备
    print("🔄 重置设备...")
    dev.reset()
    time.sleep(1)
    
    return dev

def query_battery_status(dev):
    """查询电池状态"""
    print("\n🔋 查询电池状态...")
    
    # 发送查询状态命令 (0x0C)
    packet = build_packet(seq=0, cmd=0x0C)
    print(f"📤 发送数据包: {packet.hex()}")
    
    # 发送
    dev.write(OUT_ENDPOINT, packet)
    print("✅ 数据包已发送")
    
    # 接收响应
    try:
        response = dev.read(IN_ENDPOINT, 512, timeout=2000)
        print(f"📥 接收响应: {response.hex()}")
        print(f"📏 响应长度: {len(response)} 字节")
        
        return response
    except Exception as e:
        print(f"❌ 接收失败: {e}")
        return None

def parse_battery_data(response):
    """
    解析电池数据
    
    根据之前的测试，查询状态命令返回 77 字节数据
    需要分析哪些字节对应电池信息
    """
    if not response or len(response) < 20:
        print("❌ 响应数据不足")
        return None
    
    print("\n📊 解析电池数据...")
    
    # 打印完整的响应数据
    print("\n原始数据（十六进制）:")
    for i in range(0, len(response), 16):
        hex_str = ' '.join(f'{b:02x}' for b in response[i:i+16])
        print(f"  {i:04d}: {hex_str}")
    
    # 尝试解析可能的电池字段
    # 根据常见的 DJI 协议，电池数据通常在响应的后半部分
    
    # 尝试不同的偏移量
    possible_offsets = [
        (12, "偏移12"),
        (16, "偏移16"),
        (20, "偏移20"),
        (24, "偏移24"),
        (28, "偏移28"),
        (32, "偏移32"),
        (36, "偏移36"),
        (40, "偏移40"),
    ]
    
    print("\n🔍 尝试解析可能的电池字段:")
    for offset, desc in possible_offsets:
        if offset + 4 <= len(response):
            # 尝试解析为百分比值
            value = response[offset]
            if 0 <= value <= 100:
                print(f"  {desc}: {value}% (可能是电量)")
    
    # 尝试解析电压（通常是 2 字节，单位 0.01V）
    print("\n⚡ 尝试解析电压:")
    for offset in range(20, min(len(response) - 2, 50)):
        voltage_raw = int.from_bytes(response[offset:offset+2], 'little')
        voltage = voltage_raw / 100.0
        if 10.0 <= voltage <= 20.0:  # 合理的电池电压范围
            print(f"  偏移{offset}: {voltage:.2f}V (可能是电压)")
    
    # 返回原始数据，让用户判断
    return {
        "raw_data": response.hex(),
        "length": len(response),
    }

def main():
    print("=" * 60)
    print("🔋 Air 3S 真实电池查询工具")
    print("=" * 60)
    
    # 初始化设备
    dev = init_device()
    if not dev:
        return
    
    try:
        # 查询电池状态
        response = query_battery_status(dev)
        
        if response:
            # 解析电池数据
            battery_info = parse_battery_data(response)
            
            print("\n" + "=" * 60)
            print("📋 总结")
            print("=" * 60)
            print("✅ 成功查询设备状态")
            print(f"📏 响应数据长度: {len(response)} 字节")
            print("\n⚠️ 注意: 电池数据字段需要进一步分析")
            print("   请查看上面的原始数据，判断哪些字节对应电池信息")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭设备
        usb.util.dispose_resources(dev)
        print("\n✅ 设备已关闭")

if __name__ == "__main__":
    main()
