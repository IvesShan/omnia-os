#!/usr/bin/env python3
"""DJI 设备智能识别工具"""

import usb.core
import usb.util
import struct
import sys
import time

# 设备型号数据库
DEVICE_MODELS = {
    'A141': {'name': 'DJI Mini SE', 'code': 'WM160', 'type': 'drone'},
    'A142': {'name': 'DJI Mini 2', 'code': 'WM161', 'type': 'drone'},
    'A143': {'name': 'DJI Mini 2 SE', 'code': 'WM1615', 'type': 'drone'},
    'A144': {'name': 'DJI Mini 3', 'code': 'WM163', 'type': 'drone'},
    'A145': {'name': 'DJI Mini 3 Pro', 'code': 'WM1605', 'type': 'drone'},
    'A146': {'name': 'DJI Mini 4 Pro', 'code': 'WM170', 'type': 'drone'},
}

# 设备类型映射
DEVICE_TYPES = {
    0x01: '主控制器',
    0x03: '相机',
    0x07: '飞控',
    0x08: '云台',
    0x0A: '飞行控制器',
    0x10: 'PC',
    0x12: '感知模块',
    0x18: '遥控器',
    0x2A: '电池/电源管理',
    0x8A: '升级模块',
    0xFF: '广播'
}

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
    packet.extend([0x55, 0xAA])
    packet.extend(struct.pack('<H', 11 + len(data)))
    packet.append(0x00)
    packet.extend(struct.pack('<H', 0x0001))
    packet.extend([0x10, 0x00])
    packet.extend([0xFF, 0xFF])
    packet.append(cmd)
    packet.extend(data)
    crc = calc_crc16(packet[2:])
    packet.extend(struct.pack('<H', crc))
    return bytes(packet)

def send_receive(dev, cmd, data=b'', timeout=2000):
    """发送并接收数据"""
    packet = build_packet(cmd, data)
    try:
        dev.write(0x04, packet, timeout=timeout)
        response = dev.read(0x85, 512, timeout=timeout)
        return response
    except Exception as e:
        return None

def extract_model_code(data):
    """从数据中提取型号代码"""
    if len(data) < 4:
        return None
    
    # 查找 ASCII 字符串 (4字节)
    for i in range(len(data) - 3):
        chunk = data[i:i+4]
        # 检查是否为 ASCII 字母+数字组合
        if all(32 <= b <= 126 for b in chunk):
            text = bytes(chunk).decode('ascii', errors='ignore')
            if text in DEVICE_MODELS:
                return text
    
    return None

def parse_device_info(data):
    """解析设备信息"""
    info = {}
    
    if len(data) >= 1:
        info['device_type'] = data[0]
        info['device_type_name'] = DEVICE_TYPES.get(data[0], f'未知(0x{data[0]:02X})')
    
    if len(data) >= 2:
        info['device_subtype'] = data[1]
    
    if len(data) >= 3:
        info['hardware_version'] = data[2]
    
    if len(data) >= 4:
        info['software_version'] = data[3]
    
    # 提取型号代码
    model_code = extract_model_code(data)
    if model_code:
        info['model_code'] = model_code
        info['model_info'] = DEVICE_MODELS[model_code]
    
    return info

def main():
    print('=' * 70)
    print('🔍 DJI 设备智能识别工具')
    print('=' * 70)
    
    # 找到设备
    dev = usb.core.find(idVendor=0x2ca3, idProduct=0x0020)
    if not dev:
        print('❌ 设备未找到')
        return 1
    
    print('✅ 设备已找到')
    
    # 获取 USB 设备信息
    print('\n📋 USB 设备信息:')
    print(f'   制造商: {dev.manufacturer}')
    print(f'   产品: {dev.product}')
    print(f'   序列号: {dev.serial_number}')
    print(f'   VID:PID: 0x{dev.idVendor:04X}:0x{dev.idProduct:04X}')
    
    # 解除内核驱动
    for cfg in dev:
        for intf in cfg:
            try:
                if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                    dev.detach_kernel_driver(intf.bInterfaceNumber)
            except:
                pass
    
    dev.reset()
    time.sleep(1)
    
    # 配置接口
    try:
        usb.util.claim_interface(dev, 4)
    except Exception as e:
        print(f'❌ 无法配置接口: {e}')
        return 1
    
    print('✅ 接口已配置')
    
    # 查询设备信息
    print('\n' + '=' * 70)
    print('📊 设备详细信息')
    print('=' * 70)
    
    # 1. 查询设备信息
    print('\n【查询设备信息】')
    resp = send_receive(dev, 0x88)
    if resp and len(resp) > 14:
        data = resp[12:-2]
        info = parse_device_info(data)
        
        print(f'   设备类型: {info.get("device_type_name", "未知")}')
        print(f'   硬件版本: {info.get("hardware_version", "未知")}')
        print(f'   软件版本: {info.get("software_version", "未知")}')
        
        if 'model_code' in info:
            model_info = info['model_info']
            print(f'\n   🎯 设备型号识别成功!')
            print(f'   型号代码: {info["model_code"]}')
            print(f'   设备名称: {model_info["name"]}')
            print(f'   产品代码: {model_info["code"]}')
            print(f'   设备类型: {model_info["type"]}')
    
    # 2. 查询状态
    print('\n【查询设备状态】')
    resp = send_receive(dev, 0x0C)
    if resp and len(resp) > 14:
        data = resp[12:-2]
        
        # 提取型号代码
        model_code = extract_model_code(data)
        if model_code and model_code in DEVICE_MODELS:
            model_info = DEVICE_MODELS[model_code]
            print(f'   🎯 确认型号: {model_info["name"]} ({model_info["code"]})')
        
        # 解析状态数据
        if len(data) >= 1:
            status_code = data[0]
            print(f'   状态码: {status_code}')
        
        if len(data) >= 40:
            # 尝试解析电池信息
            battery1 = struct.unpack('<I', bytes(data[40:44]))[0]
            battery2 = struct.unpack('<I', bytes(data[48:52]))[0] if len(data) >= 52 else 0
            print(f'   电池状态1: {battery1}')
            if battery2:
                print(f'   电池状态2: {battery2}')
    
    # 3. 心跳
    print('\n【心跳检测】')
    resp = send_receive(dev, 0xEA)
    if resp:
        print(f'   ✅ 设备响应正常 ({len(resp)} 字节)')
    else:
        print(f'   ❌ 设备无响应')
    
    # 清理
    usb.util.dispose_resources(dev)
    
    print('\n' + '=' * 70)
    print('✅ 识别完成')
    print('=' * 70)
    return 0

if __name__ == '__main__':
    sys.exit(main())
