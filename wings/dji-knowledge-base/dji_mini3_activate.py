#!/usr/bin/env python3
"""DJI Mini 3 深度探测 - 尝试激活完整通信"""
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

# 尝试多种命令格式
print("\n" + "="*60)
print("🔬 尝试激活序列")
print("="*60)

# 可能的DJI激活/握手命令
activation_commands = [
    # 标准查询
    (bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "标准心跳"),
    (bytes([0x55, 0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]), "版本查询"),
    (bytes([0x55, 0xAA, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]), "设备查询"),
    
    # 可能的激活命令
    (bytes([0x55, 0xAA, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00]), "激活1"),
    (bytes([0x55, 0xAA, 0x21, 0x00, 0x00, 0x00, 0x00, 0x00]), "激活2"),
    (bytes([0x55, 0xAA, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展1"),
    (bytes([0x55, 0xAA, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展2"),
    
    # 不同长度的命令
    (bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "10字节"),
    (bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "16字节"),
    
    # 不同的包头
    (bytes([0xAA, 0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "AA55包头"),
    (bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "全零"),
]

results = {}
try:
    for cmd, name in activation_commands:
        print(f"\n📤 {name} ({len(cmd)}字节)")
        try:
            dev.write(EP_OUT, cmd)
            time.sleep(0.3)
            data = bytes(dev.read(EP_IN, 512, timeout=2000))
            
            if len(data) > 17:
                print(f"   ✅ 长响应: {len(data)} 字节!")
                print(f"   HEX: {data.hex()}")
                results[name] = data
            elif len(data) == 17:
                print(f"   ℹ️  标准响应: 17字节")
                print(f"   HEX: {data.hex()}")
            else:
                print(f"   ⚠️  短响应: {len(data)} 字节")
                print(f"   HEX: {data.hex()}")
                
        except Exception as e:
            print(f"   ❌ {e}")
            
finally:
    usb.util.release_interface(dev, intf)

# 如果仍然没有长响应，说明Mini 3确实是简化协议
print("\n" + "="*60)
print("📊 结果汇总")
print("="*60)

if results:
    print(f"✅ 发现 {len(results)} 个长响应命令!")
    for name, data in results.items():
        print(f"  {name}: {len(data)} 字节")
else:
    print("❌ 所有命令都返回17字节标准响应")
    print("\n结论: DJI Mini 3 (WM160) 的USB协议是简化版")
    print("      不支持下位机直接获取详细诊断数据")
    print("      建议通过 DJI Assistant 2 或 DJI Fly App 进行诊断")

print("\n✅ 探测完成")
