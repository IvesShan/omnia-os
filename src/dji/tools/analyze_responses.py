#!/usr/bin/env python3
"""分析 DJI 设备响应数据"""

import usb.core
import usb.util
import struct
import sys

def calc_crc16(data):
    """计算 CRC16"""
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

def build_packet(cmd, data=b''):
    """构建数据包"""
    packet = bytearray()
    packet.extend([0x55, 0xAA])  # 头
    packet.extend(struct.pack('<H', 11 + len(data)))  # 长度
    packet.append(0x00)  # 版本
    packet.extend(struct.pack('<H', 0x0001))  # 序列号
    packet.extend([0x10, 0x00])  # 源: PC
    packet.extend([0xFF, 0xFF])  # 目标: 广播
    packet.append(cmd)  # 命令ID
    packet.extend(data)  # 数据
    crc = calc_crc16(packet[2:])
    packet.extend(struct.pack('<H', crc))
    return bytes(packet)

def parse_packet(data):
    """解析数据包"""
    if len(data) < 14:
        return None
    
    result = {
        'header': f'0x{data[0]:02X} 0x{data[1]:02X}',
        'length': struct.unpack('<H', bytes(data[2:4]))[0],
        'version': data[4],
        'seq': struct.unpack('<H', bytes(data[5:7]))[0],
        'src_type': data[7],
        'src_id': data[8],
        'dst_type': data[9],
        'dst_id': data[10],
        'cmd': data[11],
        'data': data[12:-2],
        'crc': f'0x{data[-2]:02X}{data[-1]:02X}'
    }
    return result

def main():
    print('=' * 70)
    print('DJI 设备响应数据分析')
    print('=' * 70)
    
    # 找到设备
    dev = usb.core.find(idVendor=0x2ca3, idProduct=0x0020)
    if not dev:
        print('❌ 设备未找到')
        return 1
    
    print('✅ 设备已找到')
    
    # 解除内核驱动
    for cfg in dev:
        for intf in cfg:
            try:
                if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                    dev.detach_kernel_driver(intf.bInterfaceNumber)
            except:
                pass
    
    dev.reset()
    
    import time
    time.sleep(1)
    
    # 配置接口
    try:
        usb.util.claim_interface(dev, 4)
    except Exception as e:
        print(f'❌ 无法配置接口: {e}')
        return 1
    
    print('✅ 接口已配置')
    
    def send_receive(cmd, data=b'', timeout=2000):
        packet = build_packet(cmd, data)
        try:
            dev.write(0x04, packet, timeout=timeout)
            response = dev.read(0x85, 512, timeout=timeout)
            return response
        except Exception as e:
            print(f'  ❌ 通信失败: {e}')
            return None
    
    # 设备类型映射
    device_types = {
        0x03: '相机',
        0x08: '云台',
        0x0a: '飞控',
        0x10: 'PC',
        0x12: '感知模块',
        0xFF: '广播'
    }
    
    # 测试命令
    commands = [
        (0xEA, '心跳'),
        (0x88, '查询设备信息'),
        (0x0C, '查询状态'),
        (0x07, '进入升级模式')
    ]
    
    for cmd_id, cmd_name in commands:
        print(f'\n{"=" * 70}')
        print(f'【{cmd_name} - 0x{cmd_id:02X}】')
        print('=' * 70)
        
        resp = send_receive(cmd_id)
        if not resp:
            continue
        
        print(f'\n📦 原始数据 ({len(resp)} 字节):')
        print('   ' + ' '.join(f'{b:02X}' for b in resp[:32]))
        if len(resp) > 32:
            print('   ' + ' '.join(f'{b:02X}' for b in resp[32:64]))
        if len(resp) > 64:
            print('   ' + ' '.join(f'{b:02X}' for b in resp[64:]))
        
        # 解析数据包
        parsed = parse_packet(resp)
        if not parsed:
            print('❌ 数据包格式错误')
            continue
        
        print(f'\n📋 数据包解析:')
        print(f'   头部: {parsed["header"]}')
        print(f'   长度: {parsed["length"]}')
        print(f'   版本: {parsed["version"]}')
        print(f'   序列号: {parsed["seq"]}')
        print(f'   源: 类型=0x{parsed["src_type"]:02X} ({device_types.get(parsed["src_type"], "未知")}) 编号={parsed["src_id"]}')
        print(f'   目标: 类型=0x{parsed["dst_type"]:02X} ({device_types.get(parsed["dst_type"], "未知")}) 编号={parsed["dst_id"]}')
        print(f'   命令: 0x{parsed["cmd"]:02X}')
        print(f'   CRC: {parsed["crc"]}')
        
        # 解析数据字段
        data = parsed['data']
        print(f'\n📊 数据字段 ({len(data)} 字节):')
        
        if cmd_id == 0xEA:  # 心跳
            print('   心跳响应通常包含:')
            if len(data) >= 1:
                print(f'   - 状态: {data[0]}')
            if len(data) >= 4:
                timestamp = struct.unpack('<I', bytes(data[0:4]))[0]
                print(f'   - 时间戳: {timestamp}')
        
        elif cmd_id == 0x88:  # 查询设备信息
            print('   设备信息:')
            if len(data) >= 1:
                dev_type = data[0]
                print(f'   - 设备类型: 0x{dev_type:02X} ({device_types.get(dev_type, "未知")})')
            if len(data) >= 2:
                print(f'   - 设备子类型: 0x{data[1]:02X}')
            if len(data) >= 3:
                print(f'   - 硬件版本: {data[2]}')
            if len(data) >= 4:
                print(f'   - 软件版本: {data[3]}')
        
        elif cmd_id == 0x0C:  # 查询状态
            print('   状态信息:')
            if len(data) >= 1:
                print(f'   - 状态码: {data[0]}')
            if len(data) >= 2:
                print(f'   - 错误码: {data[1]}')
            if len(data) >= 4:
                status = struct.unpack('<I', bytes(data[0:4]))[0]
                print(f'   - 状态值: {status} (0x{status:08X})')
            
            # 尝试解析更多字段
            print(f'   - 原始数据: {" ".join(f"{b:02X}" for b in data[:min(16, len(data))])}')
        
        elif cmd_id == 0x07:  # 进入升级模式
            print('   升级模式响应:')
            if len(data) >= 1:
                result = data[0]
                print(f'   - 结果: {result} ({"成功" if result == 0 else "失败"})')
            if len(data) >= 2:
                print(f'   - 模式: {data[1]}')
    
    # 清理
    usb.util.dispose_resources(dev)
    print('\n' + '=' * 70)
    print('✅ 分析完成')
    print('=' * 70)
    return 0

if __name__ == '__main__':
    sys.exit(main())
