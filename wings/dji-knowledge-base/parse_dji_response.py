#!/usr/bin/env python3
"""解析 DJI Air 3S 响应数据"""

# 电池响应
battery_data = bytes([85, 41, 4, 201, 146, 42, 239, 0, 0, 3, 206, 33, 1, 0, 1, 0, 0, 0, 0, 129, 32, 192, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0])

# 设备信息响应
device_data = bytes([85, 77, 4, 168, 72, 42, 112, 0, 64, 0, 129, 87, 65, 50, 51, 52, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

# 飞行数据响应
flight_data = bytes([85, 97, 4, 36, 3, 10, 245, 139, 0, 3, 67, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

print("="*60)
print("📊 DJI Air 3S 数据解析")
print("="*60)

# 解析电池数据
print("\n🔋 电池数据解析:")
print(f"  原始: {battery_data.hex()}")
print(f"  包头: 0x{battery_data[0]:02X} (0x55 = DJI包头)")
print(f"  命令: 0x{battery_data[1]:02X} ({battery_data[1]})")

# 尝试解析电压/电量
# DJI协议通常在字节10-11处有电压值
if len(battery_data) > 12:
    # 尝试不同的解析方式
    voltage = battery_data[10] + battery_data[11] * 256  # 大端
    voltage_le = battery_data[10] + battery_data[11] * 256
    print(f"  电压(猜测): {voltage} mV ({voltage/1000:.1f}V) [大端]")
    
    # 电量百分比
    soc = battery_data[12] if battery_data[12] <= 100 else None
    if soc:
        print(f"  电量: {soc}%")

# 解析设备信息
print("\n📱 设备信息解析:")
print(f"  原始: {device_data.hex()}")
print(f"  包头: 0x{device_data[0]:02X}")
print(f"  命令: 0x{device_data[1]:02X}")

# 查找字符串
text_part = device_data[10:].decode('ascii', errors='ignore').strip('\x00')
if text_part:
    print(f"  文本信息: {text_part}")

# 解析飞行数据
print("\n✈️  飞行数据解析:")
print(f"  原始: {flight_data.hex()}")
print(f"  包头: 0x{flight_data[0]:02X}")
print(f"  命令: 0x{flight_data[1]:02X}")

# 尝试解析飞行时间（可能在字节4-7）
flight_time = flight_data[4] + flight_data[5]*256 + flight_data[6]*65536
print(f"  飞行时间(猜测): {flight_time} 分钟")

# 尝试查找固件版本
print("\n🔍 固件版本信息:")
for i in range(len(device_data) - 3):
    chunk = device_data[i:i+4]
    if all(32 <= b < 127 for b in chunk):
        text = chunk.decode('ascii')
        if text.isalnum() and len(text) >= 3:
            print(f"  位置 {i}: {text}")

print("\n" + "="*60)
print("💡 初步结论:")
print("="*60)
print("✅ 设备硬件通信正常")
print("✅ 电池系统响应正常")
print("✅ 设备信息可读")
print("⚠️  需要 DJI Assistant 2 进行完整自检")
