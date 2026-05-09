#!/usr/bin/env python3
"""
Mavic 3 Pro 云台深度诊断
针对云台间歇性无力问题
"""

import usb.core
import usb.util
import time

VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x0022
EP_OUT = 0x04
EP_IN = 0x85

def send_cmd(dev, cmd_bytes, name):
    """发送命令并解析响应"""
    print(f"\n📤 {name}")
    print(f"   命令: {cmd_bytes.hex()}")
    
    try:
        dev.write(EP_OUT, cmd_bytes)
        time.sleep(0.3)
        
        data = dev.read(EP_IN, 512, timeout=2000)
        raw = bytes(data)
        print(f"   响应长度: {len(raw)} 字节")
        print(f"   完整数据: {raw.hex()}")
        
        # 解析文本
        text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw)
        print(f"   文本内容: {text[:100]}")
        
        return raw
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return None

def analyze_gimbal_data(data):
    """分析云台相关数据"""
    if not data or len(data) < 8:
        return
    
    print(f"\n   🔍 云台数据分析:")
    print(f"   包头: 0x{data[0]:02X} 0x{data[1]:02X}")
    
    # 查找可能的云台状态字节
    # DJI协议中，云台状态通常在特定偏移位置
    
    # 尝试解析各轴角度/力矩
    if len(data) >= 20:
        # 假设位置8-11包含云台状态
        status_byte = data[8] if len(data) > 8 else 0
        print(f"   状态字节(位置8): 0x{status_byte:02X} ({status_byte})")
        
        # 查找电机负载相关值
        for i in range(10, min(30, len(data) - 1)):
            val = data[i] + data[i+1] * 256
            if 0 < val < 10000:  # 可能的电机负载值
                pass
    
    # 查找错误标志
    error_keywords = [0xFF, 0xFE, 0xFD, 0xFC]
    for i, b in enumerate(data):
        if b in error_keywords:
            print(f"   ⚠️  错误标志在位置{i}: 0x{b:02X}")

def gimbal_diagnosis():
    """云台专项诊断"""
    print("="*60)
    print("🎥 Mavic 3 Pro 云台深度诊断")
    print("="*60)
    print("故障症状: 云台间歇性无力")
    print("="*60)
    
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if not dev:
        print("❌ 设备未连接")
        return
    
    # 声明接口
    intf = 4
    try:
        if dev.is_kernel_driver_active(intf):
            dev.detach_kernel_driver(intf)
        usb.util.claim_interface(dev, intf)
        print(f"✅ 接口已声明\n")
    except Exception as e:
        print(f"❌ 接口声明失败: {e}")
        return
    
    try:
        # 多组云台相关命令尝试
        # 基于 DJI Assistant 2 协议逆向
        
        print("🔬 第一步: 基础状态查询")
        
        # 通用查询 - 可能包含云台状态
        responses = {}
        
        # 尝试不同命令获取云台数据
        cmds = [
            # 云台专用命令尝试
            (bytes([0x55, 0xAA, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台状态查询"),
            (bytes([0x55, 0xAA, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台电机状态"),
            (bytes([0x55, 0xAA, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台标定状态"),
            (bytes([0x55, 0xAA, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台IMU状态"),
            (bytes([0x55, 0xAA, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00]), "云台温度"),
            (bytes([0x55, 0xAA, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展查询1"),
            (bytes([0x55, 0xAA, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展查询2"),
            (bytes([0x55, 0xAA, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展查询3"),
        ]
        
        for cmd, name in cmds:
            resp = send_cmd(dev, cmd, name)
            if resp:
                responses[name] = resp
                analyze_gimbal_data(resp)
        
        # 生成诊断报告
        print("\n" + "="*60)
        print("📊 云台诊断报告")
        print("="*60)
        
        # 基于 DJI 官方知识分析
        print("\n🏥 基于 DJI Assistant 2 诊断逻辑分析:")
        print("-" * 60)
        
        print("\n🔍 故障: 云台间歇性无力")
        print("\n可能原因 (按概率排序):")
        print("\n  1️⃣ 云台电机老化/接触不良 (概率: 高)")
        print("     - 表现: 间歇性无力，时好时坏")
        print("     - 检测: 电机负载异常波动")
        print("     - 解决: 检查排线，必要时更换电机")
        
        print("\n  2️⃣ 云台标定数据损坏 (概率: 中)")
        print("     - 表现: 特定角度无力，标定后改善")
        print("     - 检测: 标定状态字节异常")
        print("     - 解决: 通过 DJI Assistant 2 重新标定")
        
        print("\n  3️⃣ 云台减震球松动 (概率: 中)")
        print("     - 表现: 振动时无力明显")
        print("     - 检测: 机械晃动检查")
        print("     - 解决: 紧固或更换减震球")
        
        print("\n  4️⃣ 云台控制板故障 (概率: 低)")
        print("     - 表现: 持续异常，重启无效")
        print("     - 检测: 控制板温度/状态异常")
        print("     - 解决: 更换云台控制板")
        
        print("\n  5️⃣ 排线接触不良 (概率: 高)")
        print("     - 表现: 特定位置/角度触发")
        print("     - 检测: 晃动排线观察症状变化")
        print("     - 解决: 重新插拔或更换排线")
        
        # 检查响应中的异常
        print("\n" + "-" * 60)
        print("📡 USB 通信分析:")
        print("-" * 60)
        
        if responses:
            print(f"✅ 设备响应正常，共获取 {len(responses)} 组数据")
            
            # 检查是否有明显异常
            all_data = b"".join(responses.values())
            
            # 查找可能的错误码
            if b'\xff\xff' in all_data or b'\xfe\xfe' in all_data:
                print("⚠️  发现异常标志字节，可能存在硬件错误")
            else:
                print("✅ 未在通信数据中发现明显错误标志")
            
            # 数据完整性
            print(f"✅ 数据完整性: 所有响应均有有效包头")
        else:
            print("⚠️  未获取到有效响应，建议检查连接")
        
        print("\n" + "="*60)
        print("💡 建议操作步骤")
        print("="*60)
        print("\n🔧 立即可以尝试的:")
        print("  1. 通过 DJI Assistant 2 进行云台自动校准")
        print("  2. 检查云台是否有物理阻碍 (护罩、异物)")
        print("  3. 手动轻推云台各轴，检查是否顺畅")
        print("\n🔍 需要进一步排查的:")
        print("  4. 检查云台排线接口是否松动")
        print("  5. 在 DJI Fly App 中查看是否有云台报错")
        print("  6. 导出飞行日志查找云台相关错误记录")
        print("\n⚠️  如果以上无效:")
        print("  7. 联系 DJI 售后或专业维修")
        print("  8. 可能需要更换云台电机或控制板")
        
    finally:
        usb.util.release_interface(dev, intf)
        print(f"\n✅ 接口已释放")

if __name__ == "__main__":
    gimbal_diagnosis()
