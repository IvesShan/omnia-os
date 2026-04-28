#!/usr/bin/env python3
"""DJI 设备读取器 - 多次读取以捕获型号代码"""

import usb.core
import usb.util
import time

DJI_VID = 0x2ca3
DJI_PID = 0x0020

MODEL_CODES = {
    'A141': {'name': 'DJI Mini SE', 'code': 'WM160'},
    'A143': {'name': 'DJI Mini 2', 'code': 'WM161'},
    'A145': {'name': 'DJI Mini 3', 'code': 'WM163'},
    'A147': {'name': 'DJI Mini 3 Pro', 'code': 'WM1605'},
    'A14B': {'name': 'DJI Mini 4 Pro', 'code': 'WM170'},
}

def find_model_code(data):
    """在数据中查找型号代码"""
    try:
        data_str = data.decode('latin-1')
        for code, info in MODEL_CODES.items():
            if code in data_str:
                return code, info
    except Exception:
        pass
    return None, None

def main():
    print("=" * 70)
    print("🔍 DJI 设备完整读取")
    print("=" * 70)
    
    # 查找设备
    dev = usb.core.find(idVendor=DJI_VID, idProduct=DJI_PID)
    if dev is None:
        print("❌ 未找到 DJI 设备")
        return
    
    print("\n📋 USB 信息:")
    print(f"   产品: {usb.util.get_string(dev, dev.iProduct)}")
    print(f"   序列号: {usb.util.get_string(dev, dev.iSerialNumber)}")
    
    # 获取接口
    cfg = dev.get_active_configuration()
    intf = cfg[(4, 0)]
    
    # 分离驱动
    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
        dev.detach_kernel_driver(intf.bInterfaceNumber)
    
    # 获取端点
    ep_out = None
    ep_in = None
    for ep in intf:
        if ep.bEndpointAddress & 0x80:
            ep_in = ep
        else:
            ep_out = ep
    
    print("\n📡 开始通信测试...")
    print(f"   端点: OUT=0x{ep_out.bEndpointAddress:02X}, IN=0x{ep_in.bEndpointAddress:02X}")
    
    # 发送多次心跳
    print("\n📨 发送心跳命令 (多次尝试)...")
    
    model_found = None
    all_responses = []
    
    for i in range(5):
        try:
            # 心跳命令
            cmd = bytes([0x55, 0x04, 0x00, 0xEA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0x55])
            ep_out.write(cmd)
            
            data = ep_in.read(512, timeout=2000)
            data_bytes = bytes(data)
            all_responses.append(data_bytes)
            
            # 查找型号代码
            code, info = find_model_code(data_bytes)
            if code and not model_found:
                model_found = (code, info)
                print(f"   ✅ 第 {i+1} 次: 找到型号代码 {code}!")
            else:
                print(f"   📥 第 {i+1} 次: 接收 {len(data_bytes)} 字节")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ⚠️  第 {i+1} 次: {e}")
    
    # 显示找到的型号
    print("\n" + "=" * 70)
    print("🎯 设备识别结果")
    print("=" * 70)
    
    if model_found:
        code, info = model_found
        print(f"\n   ✅ 设备型号: {info['name']}")
        print(f"   ✅ 型号代码: {code}")
        print(f"   ✅ 产品代码: {info['code']}")
    else:
        print("\n   ⚠️  未找到型号代码，显示所有响应数据:")
        for i, data in enumerate(all_responses):
            print(f"\n   响应 {i+1} ({len(data)} 字节):")
            for j in range(0, min(len(data), 64), 16):
                chunk = data[j:j+16]
                hex_str = ' '.join(f'{b:02x}' for b in chunk)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print(f"      {j:04x}: {hex_str:<48} {ascii_str}")
    
    # 恢复驱动
    try:
        usb.util.dispose_resources(dev)
        dev.attach_kernel_driver(intf.bInterfaceNumber)
    except Exception:
        pass
    
    print("\n" + "=" * 70)
    print("✅ 读取完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
