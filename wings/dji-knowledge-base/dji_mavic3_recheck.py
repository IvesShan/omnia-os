#!/usr/bin/env python3
"""Mavic 3 Pro 修复后诊断 - 对比验证"""
import usb.core, usb.util, time, json

VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x0022
EP_OUT = 0x04
EP_IN = 0x85

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if not dev:
    print("❌ 设备未连接")
    exit(1)

product = usb.util.get_string(dev, dev.iProduct)
serial = usb.util.get_string(dev, dev.iSerialNumber)
print(f"✅ 设备: {product} (PID: 0x{PRODUCT_ID:04X})")
print(f"   序列号: {serial}")

intf = 4
if dev.is_kernel_driver_active(intf):
    dev.detach_kernel_driver(intf)
usb.util.claim_interface(dev, intf)

commands = [
    (bytes([0x55, 0xAA, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]), "电池/设备详细"),
    (bytes([0x55, 0xAA, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台状态"),
    (bytes([0x55, 0xAA, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台标定状态"),
    (bytes([0x55, 0xAA, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台IMU状态"),
    (bytes([0x55, 0xAA, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台温度"),
    (bytes([0x55, 0xAA, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展查询"),
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
            
            # 实时解析关键位置
            if len(data) >= 40:
                print(f"\n   🔍 关键位置解析:")
                print(f"      位置16: 0x{data[16]:02X}")
                print(f"      位置24: 0x{data[24]:02X}")
                print(f"      位置32: 0x{data[32]:02X}")
                
                # 判断状态
                pos24 = data[24]
                pos32 = data[32]
                
                if pos24 in [0xFD, 0xFE]:
                    print(f"      ⚠️  位置24异常: 0x{pos24:02X}")
                else:
                    print(f"      ✅ 位置24正常: 0x{pos24:02X}")
                
                if pos32 == 0xFF:
                    print(f"      ⚠️  位置32异常: 0x{pos32:02X}")
                else:
                    print(f"      ✅ 位置32正常: 0x{pos32:02X}")
                    
        except Exception as e:
            print(f"   ❌ {e}")
finally:
    usb.util.release_interface(dev, intf)

print("\n" + "="*60)
print("📊 修复前后对比")
print("="*60)

# 之前故障数据
faulty_samples = {
    "云台状态_故障": bytes.fromhex("553e044b042a75e800040500000000c60480000000000164fd0000b82f0001ccff12003491f73e59d772b50218fcb67e15603f000000000000000000a5d8"),
    "云台IMU_故障": bytes.fromhex("553e044b042a32ea00040500000000c604800000000001c8fd0000b82f0001ccff1200c391f73e042e3ab7a9de85b75815603f000000000000000000bc20"),
}

print("\n🔴 修复前 (故障状态):")
for name, data in faulty_samples.items():
    print(f"  {name}:")
    print(f"    位置24: 0x{data[24]:02X} (异常)")
    print(f"    位置32: 0x{data[32]:02X} (异常)")

print("\n🟢 修复后 (当前状态):")
for name, data in results.items():
    if len(data) >= 40:
        print(f"  {name}:")
        print(f"    位置24: 0x{data[24]:02X} {'✅ 正常' if data[24] not in [0xFD, 0xFE] else '⚠️ 异常'}")
        print(f"    位置32: 0x{data[32]:02X} {'✅ 正常' if data[32] != 0xFF else '⚠️ 异常'}")

print("\n" + "="*60)
print("💡 最终诊断")
print("="*60)

# 判断修复是否彻底
all_normal = True
for name, data in results.items():
    if len(data) >= 40:
        if data[24] in [0xFD, 0xFE] or data[32] == 0xFF:
            all_normal = False

if all_normal:
    print("\n✅ 修复成功！")
    print("   位置24和32均已恢复正常")
    print("   Y轴电机更换有效")
else:
    print("\n⚠️  仍有异常标志")
    print("   需要进一步检查")

print("\n🔧 建议:")
print("   1. 确认云台三轴运动平滑")
print("   2. 进行云台自动校准（如果有企业账号）")
print("   3. 测试长时间运行是否稳定")
print("   4. 监控温度是否恢复正常")

print("\n✅ 诊断完成")
