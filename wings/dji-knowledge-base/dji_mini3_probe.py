#!/usr/bin/env python3
"""
DJI Mini 3 全面协议探测
尝试多种接口、命令和通信方式
"""
import usb.core, usb.util, time

VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x001e

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if not dev:
    print("❌ 设备未连接")
    exit(1)

product = usb.util.get_string(dev, dev.iProduct)
serial = usb.util.get_string(dev, dev.iSerialNumber)
print(f"✅ 设备: {product} (PID: 0x{PRODUCT_ID:04X})")
print(f"   序列号: {serial}")

# 获取配置
cfg = dev.get_active_configuration()
print(f"\n📋 配置: {cfg.bConfigurationValue}")

# 扫描所有接口
for interface in cfg:
    intf_num = interface.bInterfaceNumber
    
    ep_in = None
    ep_out = None
    
    for ep in interface:
        addr = ep.bEndpointAddress
        if (addr & 0x80):
            ep_in = ep
        else:
            ep_out = ep
    
    if not ep_in and not ep_out:
        continue
    
    in_str = f"0x{ep_in.bEndpointAddress:02x}" if ep_in else "None"
    out_str = f"0x{ep_out.bEndpointAddress:02x}" if ep_out else "None"
    
    print(f"\n{'='*50}")
    print(f"接口 {intf_num} (Class={interface.bInterfaceClass})")
    print(f"  IN: {in_str}, OUT: {out_str}")
    
    # 尝试声明接口
    try:
        if dev.is_kernel_driver_active(intf_num):
            dev.detach_kernel_driver(intf_num)
        usb.util.claim_interface(dev, intf_num)
        print(f"  ✅ 已声明")
    except Exception as e:
        print(f"  ❌ 声明失败: {e}")
        continue
    
    # 尝试多种命令格式
    test_commands = [
        # 标准DJI命令
        bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        bytes([0x55, 0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]),
        # 可能的Mini系列命令
        bytes([0xAA, 0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        # 短命令
        bytes([0x55]),
        bytes([0xAA]),
    ]
    
    if ep_out:
        for cmd in test_commands:
            print(f"\n  📤 测试命令: {cmd.hex()}")
            try:
                dev.write(ep_out.bEndpointAddress, cmd)
                time.sleep(0.2)
                
                if ep_in:
                    try:
                        data = dev.read(ep_in.bEndpointAddress, 512, timeout=500)
                        print(f"    ✅ 响应: {bytes(data).hex()}")
                    except usb.core.USBError as e:
                        if e.errno == 110:
                            print(f"    ⏱️ 超时")
                        else:
                            print(f"    ⚠️  USB错误: {e}")
            except Exception as e:
                print(f"    ❌ 发送失败: {e}")
    
    # 尝试控制传输
    print(f"\n  🔌 控制传输测试:")
    try:
        result = dev.ctrl_transfer(0x80, 0x00, 0x0000, 0x0000, 64)
        print(f"    ✅ 成功: {result.hex()}")
    except Exception as e:
        print(f"    ⚠️ 失败: {e}")
    
    usb.util.release_interface(dev, intf_num)

print(f"\n{'='*50}")
print("✅ 扫描完成")
