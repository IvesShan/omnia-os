#!/usr/bin/env python3
"""快速采集当前云台状态"""
import usb.core, usb.util, time
VENDOR_ID, PRODUCT_ID = 0x2ca3, 0x0022
EP_OUT, EP_IN = 0x04, 0x85

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if not dev:
    print("❌ 设备未连接")
    exit(1)

intf = 4
if dev.is_kernel_driver_active(intf):
    dev.detach_kernel_driver(intf)
usb.util.claim_interface(dev, intf)

try:
    # 发送云台状态查询
    dev.write(EP_OUT, bytes([0x55, 0xAA, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00]))
    time.sleep(0.3)
    data = bytes(dev.read(EP_IN, 512, timeout=2000))
    
    print(f"数据: {data.hex()}")
    print(f"位置16: 0x{data[16]:02X} (R轴?)")
    print(f"位置24: 0x{data[24]:02X} (P轴/系统?)")
    print(f"位置32: 0x{data[32]:02X} (Y轴?)")
    
finally:
    usb.util.release_interface(dev, intf)
