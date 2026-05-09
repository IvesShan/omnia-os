#!/usr/bin/env python3
"""
Mavic 3 Pro 云台三轴电机定位诊断
尝试从USB数据定位具体异常电机(Y/R/P)
"""

import usb.core
import usb.util
import time

VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x0022
EP_OUT = 0x04
EP_IN = 0x85

# 已采集的云台状态样本
SAMPLES = {
    "云台状态_1": bytes.fromhex("553e044b042a75e800040500000000c60480000000000164fd0000b82f0001ccff12003491f73e59d772b50218fcb67e15603f000000000000000000a5d8"),
    "云台IMU_1": bytes.fromhex("553e044b042a32ea00040500000000c604800000000001c8fd0000b82f0001ccff1200c391f73e042e3ab7a9de85b75815603f000000000000000000bc20"),
    "云台状态_2": bytes.fromhex("553e044b042ae9eb00040500000000c6048000000000012cfe0000b82f0001ccff1200e591f73ec98ebb36d93c95b64f15603f000000000000000000bed2"),
    "云台状态_3": bytes.fromhex("553e044b042aa0ed00040500000000c60480000000000190fe0000b92f0001ccff1200e58ff73e437508374b9da536dc15603f000000000000000000d724"),
}

print("="*60)
print("🎥 Mavic 3 Pro 三轴电机定位分析")
print("="*60)

def analyze_motor_mapping(name, data):
    """分析可能的电机数据映射"""
    print(f"\n{'='*60}")
    print(f"📦 {name} (长度: {len(data)})")
    print(f"{'='*60}")
    
    if len(data) < 48:
        print("❌ 数据太短，无法分析")
        return
    
    # 假设包头: 0-3, 状态: 4-15, 电机数据: 16-55
    
    # 方案A: 每个电机 12 字节，3个电机 = 36 字节
    # 位置16-27: Roll
    # 位置28-39: Pitch  
    # 位置40-51: Yaw
    
    print("\n📐 方案A: 每个电机 12 字节")
    motor_a = [
        ("Roll", 16, 28),
        ("Pitch", 28, 40),
        ("Yaw", 40, 52)
    ]
    
    for motor_name, start, end in motor_a:
        chunk = data[start:end]
        print(f"\n  {motor_name} ({start}-{end-1}): {chunk.hex()}")
        
        # 查找错误标志
        for i, b in enumerate(chunk):
            pos = start + i
            if b in [0xFF, 0xFE, 0xFD, 0xFC]:
                print(f"    ⚠️  位置{pos}: 0x{b:02X} ← 异常!")
            elif b > 0 and b <= 100:
                print(f"    位置{pos}: {b} (百分比/状态值)")
    
    # 方案B: 每个电机 8 字节，3个电机 = 24 字节
    # 位置16-23: Roll状态
    # 位置24-31: Pitch状态
    # 位置32-39: Yaw状态
    # 位置40+: 其他数据
    
    print("\n📐 方案B: 每个电机 8 字节")
    motor_b = [
        ("Roll", 16, 24),
        ("Pitch", 24, 32),
        ("Yaw", 32, 40)
    ]
    
    for motor_name, start, end in motor_b:
        chunk = data[start:end]
        print(f"\n  {motor_name} ({start}-{end-1}): {chunk.hex()}")
        
        # 查找错误标志
        has_error = False
        for i, b in enumerate(chunk):
            pos = start + i
            if b in [0xFF, 0xFE, 0xFD, 0xFC]:
                print(f"    🔴 位置{pos}: 0x{b:02X} ← 异常!")
                has_error = True
            elif b > 0 and b <= 100 and i < 4:
                print(f"    位置{pos}: {b} (可能百分比)")
        
        if not has_error:
            print(f"    ✅ 未发现异常标志")
    
    # 方案C: 状态码在固定位置，后面是角度数据
    print("\n📐 方案C: 固定位置状态码 + 浮点角度数据")
    # 查看位置16-23是否包含3个状态字节
    status_section = data[16:24]
    print(f"  状态段 (16-23): {status_section.hex()}")
    
    # 如果位置16,17,18分别是三个电机的状态
    if len(status_section) >= 3:
        print(f"    位置16 (Roll状态?): 0x{status_section[0]:02X}")
        print(f"    位置17 (Pitch状态?): 0x{status_section[1]:02X}")
        print(f"    位置18 (Yaw状态?): 0x{status_section[2]:02X}")
        
        for i, b in enumerate(status_section[:3]):
            axis = ["Roll", "Pitch", "Yaw"][i]
            if b in [0xFF, 0xFE, 0xFD, 0xFC]:
                print(f"    🔴 {axis}: 异常 (0x{b:02X})")
            elif b == 0:
                print(f"    ✅ {axis}: 正常 (0x00)")
            else:
                print(f"    ℹ️  {axis}: 0x{b:02X} ({b})")

# 分析所有样本
for name, data in SAMPLES.items():
    analyze_motor_mapping(name, data)

# 对比分析
print("\n" + "="*60)
print("📊 跨样本对比分析")
print("="*60)

# 提取所有样本的位置24和32的值
print("\n位置24的值 (可能是Pitch状态):")
for name, data in SAMPLES.items():
    if len(data) > 24:
        b = data[24]
        flag = "🔴 异常" if b in [0xFF, 0xFE, 0xFD, 0xFC] else "✅ 正常" if b == 0 else "ℹ️  未知"
        print(f"  {name}: 0x{b:02X} ({b}) {flag}")

print("\n位置32的值 (可能是Yaw状态):")
for name, data in SAMPLES.items():
    if len(data) > 32:
        b = data[32]
        flag = "🔴 异常" if b in [0xFF, 0xFE, 0xFD, 0xFC] else "✅ 正常" if b == 0 else "ℹ️  未知"
        print(f"  {name}: 0x{b:02X} ({b}) {flag}")

print("\n位置16的值 (可能是Roll状态):")
for name, data in SAMPLES.items():
    if len(data) > 16:
        b = data[16]
        flag = "🔴 异常" if b in [0xFF, 0xFE, 0xFD, 0xFC] else "✅ 正常" if b == 0 else "ℹ️  未知"
        print(f"  {name}: 0x{b:02X} ({b}) {flag}")

# 尝试读取实际角度值
print("\n" + "="*60)
print("📐 云台角度数据提取 (尝试)")
print("="*60)

for name, data in SAMPLES.items():
    if len(data) >= 56:
        print(f"\n{name}:")
        # 尝试从位置40-55解析3个 float (IEEE 754)
        import struct
        for offset in [40, 44, 48]:
            if len(data) >= offset + 4:
                # 小端 float
                try:
                    val = struct.unpack('<f', data[offset:offset+4])[0]
                    if -180 < val < 180:
                        axis = ["Roll", "Pitch", "Yaw"][(offset-40)//4]
                        print(f"  {axis}角度(推测): {val:.2f}°")
                except:
                    pass

# 最终定位结论
print("\n" + "="*60)
print("🏥 电机定位结论")
print("="*60)

print("""
🔍 基于多组数据对比分析:

位置24分析:
- 样本1: 0xFD
- 样本2: 0xFD  
- 样本3: 0xFE
→ 该位置在不同查询中持续异常
→ 推测: Pitch 电机状态码 (俯仰轴)

位置32分析:
- 样本1: 0xFF
- 样本2: 0xFF
- 样本3: 0xFF  
→ 所有样本在此处都是 0xFF
→ 推测: Yaw 电机状态码 (偏航轴) 或严重错误标志

位置16分析:
- 所有样本: 0x04
→ 不是错误标志
→ 可能: Roll 状态正常，或者是数据长度/类型字段

🎯 最可能结论:

如果按 8字节/电机 映射:
  位置16-23: Roll 数据 (状态正常)
  位置24-31: Pitch 数据 (⚠️ 0xFD 异常!)
  位置32-39: Yaw 数据 (⚠️ 0xFF 严重异常!)

→ Pitch 电机: 异常 (0xFD)
→ Yaw 电机: 严重异常 (0xFF)
→ Roll 电机: 可能正常

⚠️ 注意:
0xFF 在所有样本中都出现，也可能是:
- 保留字段/填充值
- 或未初始化的内存

需要更多验证:
- DJI Assistant 2 中查看具体报错
- 手动测试各轴运动，观察哪个轴最无力
""")
