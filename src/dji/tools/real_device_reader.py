#!/usr/bin/env python3
"""真实设备读取器 - 直接读取连接的 DJI 设备"""

import usb.core
import usb.util
import sys

# DJI USB IDs
DJI_VID = 0x2ca3
DJI_PID = 0x0020

def bytes_to_hex(data):
    """将字节数据转换为十六进制字符串"""
    return ''.join(f'{b:02x}' for b in data)

def find_ascii_model_code(data):
    """在数据中查找 ASCII 型号代码 (如 A141)"""
    data_str = data.decode('latin-1')  # 使用 latin-1 保持所有字节
    
    # 常见型号代码
    model_codes = {
        'A141': 'DJI Mini SE (WM160)',
        'A143': 'DJI Mini 2 (WM161)',
        'A145': 'DJI Mini 3 (WM163)',
        'A147': 'DJI Mini 3 Pro (WM1605)',
        'A14B': 'DJI Mini 4 Pro (WM170)',
        'A130': 'DJI Mavic Air 2 (WM232)',
        'A132': 'DJI Air 2S (WM231)',
    }
    
    for code, name in model_codes.items():
        if code in data_str:
            return code, name
    
    return None, None

def read_real_device():
    """读取真实连接的 DJI 设备"""
    
    print("=" * 70)
    print("🔍 DJI 真实设备读取器")
    print("=" * 70)
    print()
    
    # 查找设备
    print("📡 正在查找 DJI 设备...")
    dev = usb.core.find(idVendor=DJI_VID, idProduct=DJI_PID)
    
    if dev is None:
        print("❌ 未找到 DJI 设备")
        print("   请确保设备已通过 USB 连接")
        return
    
    print("✅ 找到 DJI 设备！")
    print()
    
    # 基本信息
    print("📋 USB 基本信息:")
    print(f"   制造商: {usb.util.get_string(dev, dev.iManufacturer) or 'N/A'}")
    print(f"   产品: {usb.util.get_string(dev, dev.iProduct) or 'N/A'}")
    print(f"   序列号: {usb.util.get_string(dev, dev.iSerialNumber) or 'N/A'}")
    print(f"   VID:PID: 0x{DJI_VID:04X}:0x{DJI_PID:04X}")
    print(f"   USB 版本: {dev.bcdUSB / 256:.2f}")
    print(f"   设备版本: {dev.bcdDevice / 256:.2f}")
    print()
    
    # 配置信息
    print("🔌 接口配置:")
    cfg = dev.get_active_configuration()
    
    interface_list = []
    for intf in cfg:
        interface_list.append(intf)
        intf_str = f"   接口 {intf.bInterfaceNumber}: "
        try:
            intf_str += usb.util.get_string(dev, intf.iInterface) or "Unknown"
        except:
            intf_str += "Unknown"
        
        intf_str += f" (Class: {intf.bInterfaceClass}, SubClass: {intf.bInterfaceSubClass})"
        print(intf_str)
        
        for ep in intf:
            direction = "IN" if ep.bEndpointAddress & 0x80 else "OUT"
            print(f"      端点 0x{ep.bEndpointAddress:02X} ({direction}) - {ep.wMaxPacketSize} bytes")
    
    print()
    
    # 尝试通信
    print("📡 尝试与设备通信...")
    
    # 找到 BULK 接口 (接口 4)
    try:
        intf = cfg[(4, 0)]
    except:
        # 找第一个 Vendor Specific 接口
        for i in cfg:
            if i.bInterfaceClass == 0xFF:
                intf = i
                break
    
    # 分离内核驱动
    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
        try:
            dev.detach_kernel_driver(intf.bInterfaceNumber)
            print(f"✅ 已分离内核驱动 (接口 {intf.bInterfaceNumber})")
        except Exception as e:
            print(f"⚠️  无法分离内核驱动: {e}")
    
    # 获取端点
    ep_out = None
    ep_in = None
    
    for ep in intf:
        if ep.bEndpointAddress & 0x80:
            ep_in = ep
        else:
            ep_out = ep
    
    if not ep_out or not ep_in:
        print("❌ 未找到通信端点")
        return
    
    print(f"✅ 找到通信端点: OUT=0x{ep_out.bEndpointAddress:02X}, IN=0x{ep_in.bEndpointAddress:02X}")
    print()
    
    # 发送命令并读取响应
    print("📨 发送命令并读取响应:")
    print()
    
    commands = [
        (0x88, "查询设备信息"),
        (0x0C, "查询设备状态"),
        (0xEA, "心跳检测"),
    ]
    
    responses = {}
    
    for cmd_id, cmd_name in commands:
        try:
            # 构造命令包
            cmd = bytes([
                0x55,           # 起始标志
                0x04,           # 目标地址
                0x00,           # 源地址
                cmd_id,         # 命令 ID
                0x00, 0x00,     # 包序号
                0x00, 0x00,     # 数据长度
                0x00, 0x00,     # 保留
                0xAA, 0xAA,     # 校验码
                0x55,           # 结束标志
            ])
            
            # 发送
            ep_out.write(cmd)
            print(f"   📤 {cmd_name} (0x{cmd_id:02X}): 发送 {len(cmd)} 字节")
            
            # 接收
            try:
                data = ep_in.read(512, timeout=2000)
                data_bytes = bytes(data)
                print(f"   📥 响应: 接收 {len(data_bytes)} 字节")
                
                # 解析响应
                if len(data_bytes) >= 14:
                    resp_cmd = data_bytes[3]
                    resp_status = data_bytes[6]
                    
                    print(f"      命令 ID: 0x{resp_cmd:02X}")
                    print(f"      状态: {resp_status}")
                    
                    # 查找型号代码 (ASCII)
                    model_code, model_name = find_ascii_model_code(data_bytes)
                    if model_code:
                        print(f"      🎯 型号代码: {model_code} → {model_name}")
                    
                    responses[cmd_id] = data_bytes
                
            except usb.core.USBError as e:
                print(f"      ⚠️  无响应: {e}")
            
            print()
            
        except Exception as e:
            print(f"      ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # 分析所有响应数据
    print("=" * 70)
    print("📊 完整数据分析")
    print("=" * 70)
    
    # 查找型号代码
    print("\n🔍 型号识别:")
    all_data = b''
    for cmd_id, data in responses.items():
        all_data += data
    
    model_code, model_name = find_ascii_model_code(all_data)
    if model_code:
        print(f"   ✅ 设备型号: {model_name}")
        print(f"   ✅ 型号代码: {model_code}")
    else:
        print("   ⚠️  未找到已知型号代码")
    
    # 显示完整响应数据
    print("\n📦 原始响应数据:")
    for cmd_id, data in responses.items():
        print(f"\n   命令 0x{cmd_id:02X} 响应 ({len(data)} 字节):")
        # 分行显示，每行 16 字节
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"      {i:04x}: {hex_str:<48} {ascii_str}")
    
    # 恢复内核驱动
    try:
        usb.util.dispose_resources(dev)
        dev.attach_kernel_driver(intf.bInterfaceNumber)
        print(f"\n✅ 已恢复内核驱动")
    except:
        pass
    
    print()
    print("=" * 70)
    print("✅ 读取完成")
    print("=" * 70)

if __name__ == "__main__":
    try:
        read_real_device()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
