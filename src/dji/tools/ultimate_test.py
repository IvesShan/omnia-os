#!/usr/bin/env python3
"""
DJI 设备完整测试工具
尝试所有可能的通信方式
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import usb.core
import usb.util
import logging
import struct
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DJIUltimateTest:
    """DJI 设备完整测试"""
    
    def __init__(self):
        self.device = None
        self.seq = 0
        
    def find_device(self):
        """查找设备"""
        device = usb.core.find(idVendor=0x2ca3)
        if device:
            self.device = device
            return True
        return False
    
    def reset_device(self):
        """重置设备"""
        logger.info("重置设备...")
        try:
            self.device.reset()
            logger.info("✅ 设备已重置")
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"❌ 重置失败: {e}")
            return False
    
    def detach_all_drivers(self):
        """解除所有驱动"""
        logger.info("解除所有内核驱动...")
        
        for cfg in self.device:
            for intf in cfg:
                try:
                    if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                        self.device.detach_kernel_driver(intf.bInterfaceNumber)
                        logger.info(f"  ✅ 接口 {intf.bInterfaceNumber}")
                except:
                    pass
    
    def test_control_endpoint(self):
        """测试控制端点"""
        logger.info("\n" + "="*60)
        logger.info("  测试控制端点")
        logger.info("="*60)
        
        # 尝试读取设备状态
        tests = [
            ("获取设备描述符", 0x80, 0x06, 0x0100, 0x0000, 18),
            ("获取配置描述符", 0x80, 0x06, 0x0200, 0x0000, 9),
            ("获取状态", 0x80, 0x00, 0x0000, 0x0000, 2),
        ]
        
        for name, req_type, req, value, index, length in tests:
            try:
                result = self.device.ctrl_transfer(req_type, req, value, index, length, timeout=1000)
                logger.info(f"  ✅ {name}: {bytes(result).hex()}")
            except Exception as e:
                logger.error(f"  ❌ {name}: {e}")
    
    def test_bulk_transfer(self, ep_out, ep_in, name):
        """测试批量传输"""
        logger.info(f"\n测试 {name}:")
        logger.info(f"  OUT: 0x{ep_out:02X}, IN: 0x{ep_in:02X}")
        
        # 创建测试数据包
        packet = self.create_test_packet()
        
        try:
            # 发送
            sent = self.device.write(ep_out, packet, timeout=1000)
            logger.info(f"  ✅ 发送: {sent} 字节")
            logger.info(f"     数据: {packet.hex()}")
            
            # 接收
            time.sleep(0.1)
            try:
                data = self.device.read(ep_in, 512, timeout=2000)
                logger.info(f"  ✅ 接收: {len(data)} 字节")
                logger.info(f"     数据: {data.hex()}")
                
                # 解析
                if len(data) >= 14 and data[0] == 0x55 and data[1] == 0xAA:
                    self.parse_response(data)
                
                return True
            except usb.core.USBError as e:
                if e.errno == 110:
                    logger.warning(f"  ⚠️  接收超时")
                else:
                    logger.error(f"  ❌ 接收失败: {e}")
                
        except Exception as e:
            logger.error(f"  ❌ 发送失败: {e}")
        
        return False
    
    def create_test_packet(self):
        """创建测试数据包"""
        packet = bytearray()
        packet.extend([0x55, 0xAA])  # 头部
        packet.extend(struct.pack('<H', 10))  # 长度
        packet.append(0x00)  # 版本
        packet.extend(struct.pack('<H', self.seq))  # 序列号
        self.seq = (self.seq + 1) & 0xFFFF
        packet.append(0x10)  # PC
        packet.append(0x00)
        packet.append(0x0A)  # 飞控
        packet.append(0x00)
        packet.append(0x88)  # 查询命令
        
        # CRC
        crc = self.calculate_crc(packet[2:])
        packet.extend(struct.pack('<H', crc))
        
        return bytes(packet)
    
    def calculate_crc(self, data):
        """计算 CRC16"""
        crc = 0
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc
    
    def parse_response(self, data):
        """解析响应"""
        logger.info("  📦 解析响应:")
        
        length = struct.unpack('<H', data[2:4])[0]
        version = data[4]
        seq = struct.unpack('<H', data[5:7])[0]
        src_type = data[7]
        src_idx = data[8]
        tgt_type = data[9]
        tgt_idx = data[10]
        cmd = data[11]
        payload = data[12:-2]
        
        logger.info(f"     长度: {length}")
        logger.info(f"     版本: {version}")
        logger.info(f"     序列号: {seq}")
        logger.info(f"     源类型: 0x{src_type:02X}")
        logger.info(f"     目标类型: 0x{tgt_type:02X}")
        logger.info(f"     命令: 0x{cmd:02X}")
        logger.info(f"     数据: {payload.hex()}")
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("\n" + "="*60)
        logger.info("  开始完整测试")
        logger.info("="*60)
        
        # 测试控制端点
        self.test_control_endpoint()
        
        # 测试所有批量端点
        logger.info("\n" + "="*60)
        logger.info("  测试批量端点")
        logger.info("="*60)
        
        endpoints = [
            (0x01, 0x81, "CDC数据"),
            (0x02, 0x83, "Mass Storage"),
            (0x03, 0x84, "调试总线"),
            (0x04, 0x85, "备用通道1"),
            (0x05, 0x86, "主通信协议"),
            (0x06, 0x87, "扩展通道"),
            (0x07, 0x88, "备用通道2"),
        ]
        
        results = {}
        for ep_out, ep_in, name in endpoints:
            success = self.test_bulk_transfer(ep_out, ep_in, name)
            results[name] = success
            time.sleep(0.3)
        
        # 汇总结果
        logger.info("\n" + "="*60)
        logger.info("  测试结果汇总")
        logger.info("="*60)
        
        for name, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"  {status} {name}")
        
        return results


def main():
    print("\n" + "="*60)
    print("  🚁 DJI 设备完整测试")
    print("="*60 + "\n")
    
    test = DJIUltimateTest()
    
    # 查找设备
    if not test.find_device():
        print("  ❌ 未找到设备\n")
        return
    
    print("  ✅ 找到设备\n")
    
    # 解除驱动
    test.detach_all_drivers()
    
    # 重置设备
    test.reset_device()
    
    # 运行测试
    test.run_all_tests()
    
    print("\n" + "="*60)
    print("  测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  用户中断")
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
