#!/usr/bin/env python3
"""DJI 设备通用诊断采集 (支持多PID)"""
import usb.core, usb.util, time, json

# 扫描所有已知的DJI PID
DJI_PIDS = [0x0020, 0x0022, 0x001e]

def find_dji_device():
    """查找DJI设备"""
    for pid in DJI_PIDS:
        dev = usb.core.find(idVendor=0x2ca3, idProduct=pid)
        if dev:
            return dev, pid
    return None, None

dev, found_pid = find_dji_device()
if not dev:
    print("❌ 未找到DJI设备")
    exit(1)

try:
    product = usb.util.get_string(dev, dev.iProduct)
    serial = usb.util.get_string(dev, dev.iSerialNumber)
except:
    product = f"Unknown(PID:0x{found_pid:04X})"
    serial = "Unknown"

print(f"✅ 设备: {product}")
print(f"   PID: 0x{found_pid:04X}")
print(f"   序列号: {serial}")

# 查找接口
EP_OUT = None
EP_IN = None
cfg = dev.get_active_configuration()
for interface in cfg:
    intf_num = interface.bInterfaceNumber
    for ep in interface:
        addr = ep.bEndpointAddress
        if (addr & 0x80) == 0:
            EP_OUT = addr
        else:
            EP_IN = addr
    if EP_OUT and EP_IN:
        print(f"   接口: {intf_num}, OUT:0x{EP_OUT:02x}, IN:0x{EP_IN:02x}")
        break

if not EP_OUT or not EP_IN:
    print("❌ 未找到通信端点")
    exit(1)

intf = 4  # 尝试接口4
if dev.is_kernel_driver_active(intf):
    dev.detach_kernel_driver(intf)
try:
    usb.util.claim_interface(dev, intf)
    print(f"✅ 接口已声明")
except:
    print(f"⚠️  接口4声明失败，尝试接口0")
    intf = 0
    if dev.is_kernel_driver_active(intf):
        dev.detach_kernel_driver(intf)
    usb.util.claim_interface(dev, intf)
    print(f"✅ 接口0已声明")

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

# 输出JSON格式
print("\n" + "="*60)
print("📊 JSON格式数据")
print("="*60)
output = {
    "device_model": product,
    "serial": serial,
    "pid": f"0x{found_pid:04X}",
    "samples": {k: v.hex() for k, v in results.items()}
}
print(json.dumps(output, indent=2, ensure_ascii=False))
