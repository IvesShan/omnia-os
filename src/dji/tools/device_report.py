#!/usr/bin/env python3
"""DJI 设备完整报告生成器"""

import usb.core
import usb.util
from datetime import datetime

# DJI USB IDs
DJI_VID = 0x2ca3
DJI_PID = 0x0020

# 型号代码映射
MODEL_CODES = {
    'A141': {'name': 'DJI Mini SE', 'code': 'WM160', 'release': '2021'},
    'A143': {'name': 'DJI Mini 2', 'code': 'WM161', 'release': '2020'},
    'A145': {'name': 'DJI Mini 3', 'code': 'WM163', 'release': '2022'},
    'A147': {'name': 'DJI Mini 3 Pro', 'code': 'WM1605', 'release': '2022'},
    'A14B': {'name': 'DJI Mini 4 Pro', 'code': 'WM170', 'release': '2023'},
    'A130': {'name': 'DJI Mavic Air 2', 'code': 'WM232', 'release': '2020'},
    'A132': {'name': 'DJI Air 2S', 'code': 'WM231', 'release': '2021'},
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

def generate_report():
    """生成完整设备报告"""
    
    report = []
    report.append("=" * 70)
    report.append("📋 DJI 设备完整报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")
    
    # 查找设备
    dev = usb.core.find(idVendor=DJI_VID, idProduct=DJI_PID)
    
    if dev is None:
        report.append("❌ 未找到 DJI 设备")
        return "\n".join(report)
    
    # USB 基本信息
    report.append("🔌 USB 设备信息")
    report.append("-" * 70)
    manufacturer = usb.util.get_string(dev, dev.iManufacturer) or 'N/A'
    product = usb.util.get_string(dev, dev.iProduct) or 'N/A'
    serial = usb.util.get_string(dev, dev.iSerialNumber) or 'N/A'
    
    report.append(f"   制造商:    {manufacturer}")
    report.append(f"   产品名称:  {product}")
    report.append(f"   序列号:    {serial}")
    report.append(f"   VID:PID:   0x{DJI_VID:04X}:0x{DJI_PID:04X}")
    report.append(f"   USB 版本:  {dev.bcdUSB / 256:.2f}")
    report.append(f"   设备版本:  {dev.bcdDevice / 256:.2f}")
    report.append("")
    
    # 接口配置
    report.append("📡 接口配置")
    report.append("-" * 70)
    cfg = dev.get_active_configuration()
    
    interface_info = []
    for intf in cfg:
        intf_name = usb.util.get_string(dev, intf.iInterface) or "Unknown"
        interface_info.append({
            'number': intf.bInterfaceNumber,
            'name': intf_name,
            'class': intf.bInterfaceClass,
            'subclass': intf.bInterfaceSubClass,
        })
        report.append(f"   接口 {intf.bInterfaceNumber}: {intf_name}")
        report.append(f"      类型: Class {intf.bInterfaceClass}, SubClass {intf.bInterfaceSubClass}")
    
    report.append("")
    
    # 通信测试
    report.append("📊 设备通信测试")
    report.append("-" * 70)
    
    # 找到通信接口
    try:
        intf = cfg[(4, 0)]
    except Exception:
        for i in cfg:
            if i.bInterfaceClass == 0xFF:
                intf = i
                break
    
    # 分离内核驱动
    driver_detached = False
    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
        try:
            dev.detach_kernel_driver(intf.bInterfaceNumber)
            driver_detached = True
            report.append("   ✅ 已分离内核驱动")
        except Exception as e:
            report.append(f"   ⚠️  无法分离内核驱动: {e}")
    
    # 获取端点
    ep_out = None
    ep_in = None
    for ep in intf:
        if ep.bEndpointAddress & 0x80:
            ep_in = ep
        else:
            ep_out = ep
    
    if ep_out and ep_in:
        report.append(f"   ✅ 通信端点: OUT=0x{ep_out.bEndpointAddress:02X}, IN=0x{ep_in.bEndpointAddress:02X}")
        report.append("")
        
        # 发送命令
        commands = [
            (0x88, "查询设备信息"),
            (0x0C, "查询设备状态"),
            (0xEA, "心跳检测"),
        ]
        
        all_data = b''
        model_found = None
        
        for cmd_id, cmd_name in commands:
            try:
                cmd = bytes([0x55, 0x04, 0x00, cmd_id, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0x55])
                ep_out.write(cmd)
                
                try:
                    data = ep_in.read(512, timeout=2000)
                    data_bytes = bytes(data)
                    all_data += data_bytes
                    
                    report.append(f"   ✅ {cmd_name} (0x{cmd_id:02X}): 接收 {len(data_bytes)} 字节")
                    
                    # 查找型号代码
                    code, info = find_model_code(data_bytes)
                    if code and not model_found:
                        model_found = (code, info)
                        
                except usb.core.USBError:
                    report.append(f"   ⚠️  {cmd_name} (0x{cmd_id:02X}): 无响应")
                    
            except Exception as e:
                report.append(f"   ❌ {cmd_name} (0x{cmd_id:02X}): 错误 - {e}")
        
        report.append("")
        
        # 设备识别
        report.append("🎯 设备识别")
        report.append("-" * 70)
        
        if model_found:
            code, info = model_found
            report.append(f"   ✅ 设备型号: {info['name']}")
            report.append(f"   ✅ 型号代码: {code}")
            report.append(f"   ✅ 产品代码: {info['code']}")
            report.append(f"   ✅ 发布年份: {info['release']}")
        else:
            report.append("   ⚠️  未识别型号代码")
            report.append(f"   数据片段: {all_data[:50].hex()}")
        
        report.append("")
        
        # 显示心跳响应（包含型号信息）
        report.append("📦 心跳响应数据 (包含型号代码)")
        report.append("-" * 70)
        if 0xEA in commands:
            # 重新发送心跳获取数据
            cmd = bytes([0x55, 0x04, 0x00, 0xEA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAA, 0xAA, 0x55])
            ep_out.write(cmd)
            try:
                data = ep_in.read(512, timeout=2000)
                data_bytes = bytes(data)
                
                # 分行显示
                for i in range(0, len(data_bytes), 16):
                    chunk = data_bytes[i:i+16]
                    hex_str = ' '.join(f'{b:02x}' for b in chunk)
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                    report.append(f"   {i:04x}: {hex_str:<48} {ascii_str}")
            except Exception:
                pass
        
        # 恢复内核驱动
        if driver_detached:
            try:
                usb.util.dispose_resources(dev)
                dev.attach_kernel_driver(intf.bInterfaceNumber)
                report.append("")
                report.append("   ✅ 已恢复内核驱动")
            except Exception:
                pass
    
    report.append("")
    report.append("=" * 70)
    report.append("✅ 报告生成完成")
    report.append("=" * 70)
    
    return "\n".join(report)

if __name__ == "__main__":
    print(generate_report())
