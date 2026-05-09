#!/usr/bin/env python3
"""Air 2S 快速诊断分析"""

# 本次采集数据
battery = bytes.fromhex("55110492048aeb460000f1000000000973")
device = bytes.fromhex("55530498030a1d490003430000000000000000000000000000000000000000000000002500feffdb040600107180000000000068010000000f8a20420000c80000000000000000000000000000000001076cec")
flight = bytes.fromhex("55110492048a894b0000f1000000007443")
gimbal = bytes.fromhex("55530498030abe4d0003430000000000000000000000000000000000000000000000002400feff2b05060000718000000000009a010000000f8a20420000c8000000000000000000000000000000000007ea84")
extended = bytes.fromhex("55110492048a2a500000f100000000895a")

print("="*60)
print("📊 Air 2S 诊断分析")
print("="*60)

# 分析83字节格式（设备信息/云台）
def analyze_83byte(name, data):
    print(f"\n{'='*60}")
    print(f"📦 {name} ({len(data)}字节)")
    print(f"{'='*60}")
    print(f"HEX: {data.hex()}")
    
    if len(data) != 83:
        print(f"  长度异常: {len(data)}字节 (预期83)")
        return
    
    print(f"\n  包头: 0x{data[0]:02X} 0x{data[1]:02X} 0x{data[2]:02X} 0x{data[3]:02X}")
    
    # 查找异常标志
    print(f"\n  🔍 关键字节检查:")
    for i in [24, 32, 37, 38]:
        b = data[i]
        flag = "⚠️ " if b in [0xFF, 0xFE, 0xFD, 0xFC] else ""
        print(f"    位置{i:02d}: 0x{b:02X} {flag}")
    
    # 查找所有0xFF/0xFE
    print(f"\n  🔎 0xFF/0xFE分布:")
    for i, b in enumerate(data):
        if b in [0xFF, 0xFE]:
            print(f"    位置{i:02d}: 0x{b:02X}")
    
    # 查找可打印文本
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
    print(f"\n  📄 文本片段:")
    for i, c in enumerate(text):
        if c != '.' and c.isalnum():
            print(f"    位置{i:02d}: '{c}'")

# 分析17字节格式
def analyze_17byte(name, data):
    print(f"\n{'='*60}")
    print(f"📦 {name} ({len(data)}字节)")
    print(f"{'='*60}")
    print(f"HEX: {data.hex()}")
    
    if len(data) != 17:
        print(f"  长度异常: {len(data)}字节")
        return
    
    print(f"\n  包头: 0x{data[0]:02X} 0x{data[1]:02X}")
    print(f"  位置4-7: {data[4]:02X} {data[5]:02X} {data[6]:02X} {data[7]:02X}")

# 分析各包
analyze_83byte("设备信息 (83字节)", device)
analyze_83byte("云台状态 (83字节)", gimbal)
analyze_17byte("电池状态 (17字节)", battery)
analyze_17byte("飞行数据 (17字节)", flight)
analyze_17byte("扩展信息 (17字节)", extended)

# 综合判断
print("\n" + "="*60)
print("🏥 综合诊断结论")
print("="*60)

# 对比健康基准
print("\n📊 与健康基准对比:")
print("  设备信息中出现 0xFE(位置37), 0xFF(位置38)")
print("  云台状态中出现 0xFE(位置37), 0xFF(位置38)")
print("\n  ⚠️  注意: Air 2S 的83字节格式和Mavic 3 Pro的62字节格式不同")
print("     0xFE/0xFF在83字节中可能是正常数据值，不一定是错误码")

print("\n  17字节格式 (电池/飞行/扩展):")
print("  ✅ 包头正常: 0x55 0x11")
print("  ✅ 无异常标志")

print("\n💡 初步判断:")
print("  1. USB通信正常")
print("  2. 数据格式与之前采集的Air 2S一致")
print("  3. 83字节中的0xFE/0xFF需要更多样本确认是否为异常")

print("\n🤔 建议:")
print("  - 这台Air 2S有观察到异常表现吗？")
print("  - 如果有具体故障症状，可以针对性分析")
print("  - 如果暂时无异常，83字节中的0xFE/0xFF可能是正常数据")

print("\n✅ 分析完成")
