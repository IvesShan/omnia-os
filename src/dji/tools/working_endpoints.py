#!/usr/bin/env python3
"""
DJI 真实通信 - 使用工作的端点
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


class DJIWorkingCommunication:
    """DJI 真实通信 - 使用已验证的端点"""
    
    # 工作的端点配置
    WORKING_ENDPOINTS = [
        {'ep_out': 0x01, 'ep_in': 0x81, 'interface': 1, 'name': 'CDC数据'},
        {'ep_out': 0x04, 'ep_in': 0x85, 'interface': 4, 'name': '备用通道'},
    ]
    
    def __init__(self):
        self.device = None
        self.seq_number = 0
        
    def find_device(self):
        """查找设备"""
        device = usb.core.find(idVendor=0x2ca3)
        if device:
            self.device = device
            serial = usb.util.get_string(device, device.iSerialNumber) if device.iSerialNumber else 'Unknown'
            logger.info(f"找到设备: {serial}")
            return True
        return False
    
    def init_device(self):
        """初始化设备"""
        logger.info("初始化设备...")
        
        # 解除内核驱动
        for cfg in self.device:
            for intf in cfg:
                try:
                    if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                        self.device.detach_kernel_driver(intf.bInterfaceNumber)
                except:
                    pass
        
        # 设置配置
        try:
            self.device.set_configuration()
        except:
            pass
        
        time.sleep(0.1)
        logger.info("设备初始化完成")
    
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
    
    def create_packet(self, target=0x0a, cmd=0x88, data=b''):
        """创建数据包"""
        packet = bytearray()
        packet.extend([0x55, 0xAA])  # 头部
        
        length = len(data) + 10
        packet.extend(struct.pack('<H', length))
        packet.append(0x00)  # 版本
        packet.extend(struct.pack('<H', self.seq_number))
        self.seq_number = (self.seq_number + 1) & 0xFFFF
        
        packet.append(0x10)  # PC
        packet.append(0x00)
        packet.append(target)  # 目标
        packet.append(0x00)
        packet.append(cmd)
        packet.extend(data)
        
        crc = self.calculate_crc(packet[2:])
        packet.extend(struct.pack('<H', crc))
        
        return bytes(packet)
    
    def test_endpoint(self, ep_config):
        """测试单个端点"""
        logger.info(f"\n测试端点: {ep_config['name']} (OUT: 0x{ep_config['ep_out']:02X}, IN: 0x{ep_config['ep_in']:02X})")
        
        # 测试命令列表
        test_commands = [
            ('心跳', 0xea, b''),
            ('查询设备信息', 0x88, b''),
            ('查询状态', 0x0c, b''),
        ]
        
        success_count = 0
        
        for name, cmd, data in test_commands:
            logger.info(f"\n  [{name}] 命令: 0x{cmd:02X}")
            
            packet = self.create_packet(cmd=cmd, data=data)
            logger.info(f"    发送: {packet.hex()}")
            
            try:
                # 发送
                bytes_sent = self.device.write(ep_config['ep_out'], packet, timeout=1000)
                logger.info(f"    ✅ 发送成功: {bytes_sent} 字节")
                
                # 接收
                time.sleep(0.1)
                try:
                    response = self.device.read(ep_config['ep_in'], 512, timeout=2000)
                    logger.info(f"    ✅ 接收成功: {len(response)} 字节")
                    logger.info(f"    数据: {response.hex()}")
                    
                    # 解析响应
                    if len(response) >= 14:
                        if response[0] == 0x55 and response[1] == 0xAA:
                            resp_cmd = response[11]
                            logger.info(f"    响应命令: 0x{resp_cmd:02X}")
                    
                    success_count += 1
                    
                except usb.core.USBError as e:
                    if e.errno == 110:
                        logger.warning(f"    ⚠️  接收超时")
                    else:
                        logger.error(f"    ❌ 接收失败: {e}")
                        
            except Exception as e:
                logger.error(f"    ❌ 发送失败: {e}")
            
            time.sleep(0.2)
        
        return success_count
    
    def run_tests(self):
        """运行所有测试"""
        logger.info("\n" + "="*60)
        logger.info("  开始测试所有工作端点")
        logger.info("="*60)
        
        results = {}
        
        for ep_config in self.WORKING_ENDPOINTS:
            success = self.test_endpoint(ep_config)
            results[ep_config['name']] = success
            time.sleep(0.5)
        
        # 汇总结果
        logger.info("\n" + "="*60)
        logger.info("  测试结果汇总")
        logger.info("="*60)
        
        for name, count in results.items():
            logger.info(f"  {name}: {count}/3 成功")
        
        return results


def main():
    print("\n" + "="*60)
    print("  🚁 DJI 真实通信测试 - 工作端点")
    print("="*60 + "\n")
    
    comm = DJIWorkingCommunication()
    
    if not comm.find_device():
        print("  ❌ 未找到设备\n")
        return
    
    comm.init_device()
    
    results = comm.run_tests()
    
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
