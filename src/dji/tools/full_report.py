#!/usr/bin/env python3
"""DJI 设备完整报告生成器"""

import usb.core
import usb.util
from datetime import datetime

DJI_VID = 0x2ca3
DJI_PID = 0x0020

MODEL_CODES = {
    'A141': {'name': 'DJI Mini SE', 'code': 'WM160', 'release': '2021', 'weight': '249g', 'camera': '2.7K'},
    'A143': {'name': 'DJI Mini 2', 'code': 'WM161', 'release': '2020', 'weight': '249g', 'camera': '4K'},
    'A145': {'name': 'DJI Mini 3', 'code': 'WM163', 'release': '2022', 'weight': '249g', 'camera': '4K'},
    'A147': {'name': 'DJI Mini 3 Pro', 'code': 'WM1605', 'release': '2022', 'weight': '249g', 'camera': '4K'},
    'A14B': {'name': 'DJI Mini 4 Pro', 'code': 'WM170', 'release': '2023', 'weight': '249g', 'camera': '4K'},
}

def find_model_code(data):
    try:
        data_str = data.decode('latin-1')
        for code, info in MODEL_CODES.items():
            if code in data_str:
                return code, info
    except:
        pass
    return None, None

def main():
    print("=" * 70)
    print("📋 DJI 设备完整报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 查找设备
    dev = usb.core.find(idVendor=DJI_VID, idProduct=DJI_PID)
    if dev is None:
        print("\n❌ 未找到 DJI 设备")
        print("   请确保设备已通过 USB 连接并开机")
        return
    
    # USB 基本信息
    print("\n🔌 USB 设备信息")
    print("-" * 70)
    manufacturer = usb.util.get_string(dev, dev.iManufacturer) or 'N/A'
    product = usb.util.get_string(dev, dev.iProduct) or 'N/A'
    serial = usb.util.get_string(dev, dev.iSerialNumber) or 'N/A'
    
    print(f"   制造商:      {manufacturer}")
    print(f"   产品名称:    {product}")
    print(f"   序列号:      {serial}")
    print(f"   VID:PID:     0x{DJI_VID:04X}:0x{DJI_PID:04X}")
    print(f"   USB 版本:    {dev.bcdUSB / 256:.2f}")
    print(f"   设备版本:    {dev.bcdDevice / 256:.2f}")
    
    # 接口配置
    print("\n📡 接口配置")
    print("-" * 70)
    cfg = dev.get_active_configuration()
    
    interface_names = []
    for intf in cfg:
        name = usb.util.get_string(dev, intf.iInterface) or "Unknown"
        interface_names.append(name)
        print(f"   接口 {intf.bInterfaceNumber}: {name}")
    
    # 通信测试
    print("\n📊 设备通信")
    print("-" * 70)
    
    intf = cfg[(4, 0)]
    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
        dev.detach_kernel_driver(intf.bInterfaceNumber)
    
    ep_out = None
    ep_in = None
    for ep in intf:
        if ep.bEndpointAddress & 0x80:
            ep_in = ep
        else:
            ep_out = ep
    
    print(f"   通信端点:    OUT=0x{ep_out.bEndpointAddress:02X}, IN=0x{ep_in.bEndpointAddress:02X}")
    
    # 发送命令
    model_found = None
    commands = [
        (0x88, "查询设备信息"),
        (0x0C, "查询设备状态"),
        (0xEA, "心跳检测"),
    ]
    
    for cmd_id, cmd_name in commands:
        try:
            cmd = bytes([0x55, 0x04, 0x00, cmd_id, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0x55])
            ep_out.write(cmd)
            data = ep_in.read(512, timeout=2000)
            data_bytes = bytes(data)
            
            print(f"   {cmd_name}: ✅ 接收 {len(data_bytes)} 字节")
            
            code, info = find_model_code(data_bytes)
            if code and not model_found:
                model_found = (code, info)
                
        except Exception as e:
            print(f"   {cmd_name}: ⚠️  {e}")
    
    # 设备识别
    print("\n🎯 设备识别")
    print("-" * 70)
    
    if model_found:
        code, info = model_found
        print(f"   设备型号:    {info['name']}")
        print(f"   型号代码:    {code}")
        print(f"   产品代码:    {info['code']}")
        print(f"   发布年份:    {info['release']}")
        print(f"   起飞重量:    {info['weight']}")
        print(f"   相机规格:    {info['camera']}")
    else:
        print("   ⚠️  未识别型号")
    
    # 恢复驱动
    try:
        usb.util.dispose_resources(dev)
        dev.attach_kernel_driver(intf.bInterfaceNumber)
    except:
        pass
    
    print("\n" + "=" * 70)
    print("✅ 报告生成完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
