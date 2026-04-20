#!/usr/bin/env python3
"""
DJI 设备信息解析器
解析从设备收到的响应数据
"""

import struct

def parse_dji_response(data):
    """解析DJI响应数据包"""
    if len(data) < 10:
        return None
    
    result = {}
    
    # 起始标志
    result['start_flag'] = data[0:2]
    
    # 版本
    result['version'] = data[2]
    
    # 长度
    result['length'] = data[3]
    
    # 命令集
    result['cmd_set'] = data[4]
    
    # 设备类型
    result['device_type'] = data[5]
    
    # 命令ID
    result['cmd_id'] = (data[7] << 8) | data[6]
    
    # 序列号
    result['seq'] = (data[9] << 8) | data[8]
    
    # 数据部分
    data_len = result['length'] - 10
    if data_len > 0 and len(data) >= 10 + data_len:
        result['payload'] = data[10:10+data_len]
    else:
        result['payload'] = data[10:]
    
    return result

def get_device_type_name(device_type):
    """获取设备类型名称"""
    device_types = {
        0x00: "未知设备",
        0x03: "相机",
        0x04: "遥控器",
        0x05: "电池",
        0x06: "GPS",
        0x07: "IMU",
        0x08: "云台",
        0x09: "遥控器",
        0x0a: "飞控",
        0x0b: "电调",
        0x0c: "图传",
        0x0d: "视觉模块",
        0x0e: "避障模块",
        0x0f: "指南针",
        0x10: "电脑端",
        0x11: "移动设备",
        0x12: "感知模块",
        0x13: "RTK模块",
        0x14: "雷达模块",
    }
    return device_types.get(device_type, f"未知类型(0x{device_type:02x})")

def analyze_response(hex_data):
    """分析响应数据"""
    data = bytes.fromhex(hex_data)
    
    print("=" * 60)
    print("DJI 响应数据分析")
    print("=" * 60)
    
    print(f"\n原始数据 ({len(data)} 字节):")
    print(f"  {hex_data}")
    
    # 解析数据包
    parsed = parse_dji_response(data)
    
    print(f"\n解析结果:")
    print(f"  起始标志: {parsed['start_flag'].hex()} ({'有效' if parsed['start_flag'][0] == 0x55 else '无效'})")
    print(f"  版本: {parsed['version']}")
    print(f"  长度: {parsed['length']} 字节")
    print(f"  命令集: 0x{parsed['cmd_set']:02x}")
    print(f"  设备类型: 0x{parsed['device_type']:02x} ({get_device_type_name(parsed['device_type'])})")
    print(f"  命令ID: 0x{parsed['cmd_id']:04x}")
    print(f"  序列号: {parsed['seq']}")
    
    if parsed['payload']:
        print(f"\n负载数据 ({len(parsed['payload'])} 字节):")
        print(f"  {parsed['payload'].hex()}")
        
        # 尝试解析字符串
        try:
            # 查找可打印字符
            printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in parsed['payload'])
            print(f"  可打印: {printable}")
        except:
            pass
    
    return parsed

# 分析实际收到的响应
if __name__ == "__main__":
    # 从测试中收到的数据
    response_hex = "55610424030aa678000343000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    
    analyze_response(response_hex)
    
    print("\n" + "=" * 60)
    print("设备识别结果")
    print("=" * 60)
    print("\n✅ 设备类型: 飞控 (Flight Controller)")
    print("✅ 通信接口: Interface 4")
    print("✅ 端点: OUT=0x04, IN=0x85")
    print("\n下一步: 发送查询命令获取详细设备信息")
