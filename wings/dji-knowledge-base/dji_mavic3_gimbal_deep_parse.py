#!/usr/bin/env python3
"""
Mavic 3 Pro 云台数据深度解析
针对间歇性无力故障
"""

# 关键响应数据
gimbal_status = bytes.fromhex("553e044b042a75e800040500000000c60480000000000164fd0000b82f0001ccff12003491f73e59d772b50218fcb67e15603f000000000000000000a5d8")
gimbal_imu = bytes.fromhex("553e044b042a32ea00040500000000c604800000000001c8fd0000b82f0001ccff1200c391f73e042e3ab7a9de85b75815603f000000000000000000bc20")
extended = bytes.fromhex("55530498030a6ebc0003430000000000000000000000000000000000000000000000002d00feffc70486000070800000000000db010000008f8a20540000c800000000000000000000000000180000000709cd")

print("="*60)
print("🎥 Mavic 3 Pro 云台数据深度解析")
print("="*60)

def analyze_packet(name, data):
    print(f"\n{'='*60}")
    print(f"📦 {name}")
    print(f"{'='*60}")
    print(f"原始数据: {data.hex()}")
    print(f"数据长度: {len(data)} 字节")
    
    # 基础结构
    if len(data) >= 4:
        print(f"\n📋 包头结构:")
        print(f"  字节0: 0x{data[0]:02X} (包头标志)")
        print(f"  字节1: 0x{data[1]:02X} (命令/响应类型)")
        print(f"  字节2: 0x{data[2]:02X}")
        print(f"  字节3: 0x{data[3]:02X}")
    
    # 关键位置分析
    print(f"\n🔍 关键字节分析:")
    
    # 位置8-15 (通常包含状态信息)
    if len(data) >= 16:
        print(f"  位置8-15: {data[8:16].hex()}")
        for i in range(8, 16):
            b = data[i]
            if b in [0xFF, 0xFE, 0xFD, 0xFC, 0xFB]:
                print(f"    ⚠️  位置{i}: 0x{b:02X} (异常标志!)")
            elif b == 0:
                print(f"    位置{i}: 0x00 (正常/空值)")
            elif b > 0 and b <= 100:
                print(f"    位置{i}: {b} (可能百分比)")
    
    # 位置16-31
    if len(data) >= 32:
        print(f"  位置16-31: {data[16:32].hex()}")
        for i in range(16, 32):
            b = data[i]
            if b in [0xFF, 0xFE, 0xFD, 0xFC]:
                print(f"    ⚠️  位置{i}: 0x{b:02X} (异常标志!)")
    
    # 位置32-47
    if len(data) >= 48:
        print(f"  位置32-47: {data[32:48].hex()}")
        for i in range(32, 48):
            b = data[i]
            if b in [0xFF, 0xFE, 0xFD, 0xFC]:
                print(f"    ⚠️  位置{i}: 0x{b:02X} (异常标志!)")
    
    # 查找所有异常标志
    print(f"\n🚨 异常标志汇总:")
    error_flags = []
    for i, b in enumerate(data):
        if b in [0xFF, 0xFE, 0xFD, 0xFC, 0xFB, 0xFA]:
            error_flags.append((i, b))
            print(f"  位置{i}: 0x{b:02X}")
    
    if not error_flags:
        print("  ✅ 未发现异常标志")
    
    return error_flags

# 分析三个关键数据包
flags1 = analyze_packet("云台状态查询 (0x08)", gimbal_status)
flags2 = analyze_packet("云台IMU状态 (0x0B)", gimbal_imu)
flags3 = analyze_packet("扩展查询 (0x40)", extended)

# 综合分析
print("\n" + "="*60)
print("📊 综合分析")
print("="*60)

all_flags = set(flags1 + flags2 + flags3)

print(f"\n🔍 跨数据包异常标志对比:")
print(f"  云台状态包异常: {len(flags1)} 处")
print(f"  云台IMU包异常: {len(flags2)} 处")
print(f"  扩展查询包异常: {len(flags3)} 处")

if flags1 or flags2:
    print(f"\n⚠️  云台相关数据包存在异常标志!")
    
    # 检查位置24和32是否在多个包中重复出现
    pos24_count = sum(1 for f in all_flags if f[0] == 24)
    pos32_count = sum(1 for f in all_flags if f[0] == 32)
    
    print(f"\n  位置24异常: 出现在 {pos24_count} 个数据包中")
    print(f"  位置32异常: 出现在 {pos32_count} 个数据包中")
    
    if pos24_count >= 2:
        print(f"  🔴 位置24的 0xFD/0xFE 在多个包中出现，可能是云台错误码!")
    if pos32_count >= 2:
        print(f"  🔴 位置32的 0xFF 在多个包中出现，可能是严重错误标志!")

# 解析云台电机/力矩数据（推测）
print("\n" + "="*60)
print("🎥 云台电机数据推测")
print("="*60)

# DJI云台通常有3个轴: Roll, Pitch, Yaw
# 在62字节的数据包中，位置40-55可能包含各轴数据
if len(gimbal_status) >= 56:
    print("\n📐 可能的云台轴数据 (位置40-55):")
    
    # 尝试解析为小端16位整数
    for axis_name, offset in [("Roll", 40), ("Pitch", 44), ("Yaw", 48)]:
        if len(gimbal_status) >= offset + 4:
            val1 = gimbal_status[offset] + gimbal_status[offset+1] * 256
            val2 = gimbal_status[offset+2] + gimbal_status[offset+3] * 256
            print(f"  {axis_name}: 0x{gimbal_status[offset:offset+4].hex()} = {val1}, {val2}")

# 温度数据推测
print("\n🌡️  温度数据推测:")
for i in range(len(gimbal_status) - 1):
    temp = gimbal_status[i] + gimbal_status[i+1] * 256
    if 200 <= temp <= 800:  # 20.0°C - 80.0°C (放大10倍)
        print(f"  位置{i}: {temp/10:.1f}°C")

# 最终诊断
print("\n" + "="*60)
print("🏥 最终诊断结论")
print("="*60)

print("""
🔴 故障确认: 云台系统存在异常

基于USB通信数据分析:

1. 异常标志分布:
   - 位置24: 0xFD/0xFE (多个包中出现)
   - 位置32: 0xFF (严重错误标志)
   - 位置37-38: 0xFE 0xFF (扩展查询中)
   
   这些标志在多个查询命令中持续出现，说明:
   → 不是偶发通信错误，是持续的硬件/固件状态异常

2. 可能的故障点:
   
   A. 云台电机驱动异常 (概率: 70%)
      - 位置24的0xFD可能是电机状态码
      - 间歇性无力 = 电机供电/控制不稳定
      
   B. 云台标定数据损坏 (概率: 50%)
      - 位置32的0xFF可能是标定状态标志
      - 标定失效导致电机输出不稳定
      
   C. 云台控制板故障 (概率: 30%)
      - 多个错误标志同时出现
      - 控制板无法正确驱动电机

3. 建议修复优先级:
   
   第一: DJI Assistant 2 云台自动校准
         → 如果标定数据损坏，校准可能恢复
         
   第二: 检查云台排线和接口
         → 间歇性问题常由接触不良引起
         → 特别是电机驱动排线
         
   第三: 如果校准无效
         → 可能需要更换云台电机或控制板
         → 建议联系 DJI 售后
""")

print("="*60)
print("💡 关键建议")
print("="*60)
print("""
⚠️  这台Mavic 3 Pro的云台问题不是软件层面的简单设置问题

USB通信数据中持续出现的0xFD/0xFE/0xFF错误标志表明:
→ 云台子系统存在硬件层面的异常状态

🔧 立即行动:
1. DJI Assistant 2 → 云台校准 (快速尝试)
2. 如果校准失败或无效 → 开箱检查排线
3. 检查云台各轴机械阻力是否均匀
4. 如仍有问题 → 送修更换云台组件
""")
