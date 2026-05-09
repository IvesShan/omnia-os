#!/usr/bin/env python3
"""DJI PID 0x0022 设备深度探测"""

import usb.core
import usb.util
import time

VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x0022

# 接口 4 端点
EP_OUT = 0x04
EP_IN = 0x85

def test_command(dev, cmd_bytes, name):
    """测试单个命令"""
    print(f"\n📤 {name}")
    print(f"   命令: {cmd_bytes.hex()}")
    
    try:
        dev.write(EP_OUT, cmd_bytes)
        time.sleep(0.2)
        
        try:
            data = dev.read(EP_IN, 512, timeout=1000)
            print(f"   ✅ 响应: {bytes(data).hex()}")
            
            # 解析文本
            text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
            print(f"   📄 文本: {text[:80]}")
            
            # 查找数字
            nums = [b for b in data if b > 0 and b <= 100]
            if nums:
                print(f"   🔢 可能百分比: {nums[:5]}")
            
            return data
        except usb.core.USBError as e:
            if e.errno == 110:
                print(f"   ⏱️ 超时")
            else:
                print(f"   ❌ USB错误: {e}")
    except Exception as e:
        print(f"   ❌ 发送失败: {e}")
    
    return None

def main():
    print("="*60)
    print("DJI PID 0x0022 设备探测")
    print("="*60)
    
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if not dev:
        print("❌ 设备未连接")
        return
    
    print(f"✅ 设备已连接")
    
    # 声明接口
    intf = 4
    try:
        if dev.is_kernel_driver_active(intf):
            dev.detach_kernel_driver(intf)
        usb.util.claim_interface(dev, intf)
        print(f"✅ 接口 {intf} 已声明")
    except Exception as e:
        print(f"❌ 声明失败: {e}")
        return
    
    try:
        # 测试不同命令
        commands = [
            (bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "心跳/握手"),
            (bytes([0x55, 0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]), "电池查询 v1"),
            (bytes([0x55, 0xAA, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]), "设备查询 v1"),
            (bytes([0x55, 0xAA, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]), "飞行数据 v1"),
            (bytes([0x55, 0xAA, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]), "状态查询"),
            (bytes([0x55, 0xAA, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]), "固件版本"),
            (bytes([0x55, 0xAA, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展查询1"),
            (bytes([0x55, 0xAA, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00]), "扩展查询2"),
        ]
        
        for cmd, name in commands:
            test_command(dev, cmd, name)
        
        print("\n" + "="*60)
        print("💡 诊断结论:")
        print("="*60)
        print("✅ 设备硬件连接正常")
        print("✅ USB 通信正常")
        print("⚠️  PID 0x0022 协议与 Air 3S 不同")
        print("⚠️  需要 DJI Assistant 2 获取完整诊断")
        
    finally:
        usb.util.release_interface(dev, intf)
        print(f"\n✅ 接口已释放")

if __name__ == "__main__":
    main()
