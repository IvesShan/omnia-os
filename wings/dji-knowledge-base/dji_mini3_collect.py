#!/usr/bin/env python3
"""DJI Mini 3 数据采集 (接口3)"""
import usb.core, usb.util, time, json

VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x001e
EP_OUT = 0x02
EP_IN = 0x83

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if not dev:
    print("❌ 设备未连接")
    exit(1)

product = usb.util.get_string(dev, dev.iProduct)
serial = usb.util.get_string(dev, dev.iSerialNumber)
print(f"✅ 设备: {product} (PID: 0x{PRODUCT_ID:04X})")
print(f"   序列号: {serial}")

intf = 3
if dev.is_kernel_driver_active(intf):
    dev.detach_kernel_driver(intf)
usb.util.claim_interface(dev, intf)
print(f"✅ 接口3已声明 (OUT:0x{EP_OUT:02x}, IN:0x{EP_IN:02x})")

commands = [
    (bytes([0x55, 0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]), "电池状态"),
    (bytes([0x55, 0xAA, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]), "设备信息"),
    (bytes([0x55, 0xAA, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]), "飞行数据"),
    (bytes([0x55, 0xAA, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台状态"),
    (bytes([0x55, 0xAA, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展信息"),
]

results = {}
try:
    for cmd, name in commands:
        print(f"\n📤 {name}")
        try:
            dev.write(EP_OUT, cmd)
            time.sleep(0.3)
            data = bytes(dev.read(EP_IN, 512, timeout=2000))
            results[name] = data
            print(f"   响应: {len(data)} 字节")
            print(f"   HEX:  {data.hex()}")
        except Exception as e:
            print(f"   ❌ {e}")
finally:
    usb.util.release_interface(dev, intf)

# 输出JSON
print("\n" + "="*60)
print("📊 JSON格式数据")
print("="*60)
output = {
    "device_model": product,
    "serial": serial,
    "pid": f"0x{PRODUCT_ID:04X}",
    "interface": 3,
    "samples": {k: v.hex() for k, v in results.items()}
}
print(json.dumps(output, indent=2, ensure_ascii=False))
