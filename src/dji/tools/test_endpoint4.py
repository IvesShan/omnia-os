#!/usr/bin/env python3
"""
DJI 真实通信 - 测试工作的端点 0x04/0x85
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


class DJIEndpoint4Test:
    """测试端点 0x04/0x85"""
    
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
    
    def init_device(self):
        """初始化设备"""
        logger.info("初始化设备...")
        
        # 解除驱动
        for cfg in self.device:
            for intf in cfg:
                try:
                    if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                        self.device.detach_kernel_driver(intf.bInterfaceNumber)
                except Exception:
                    pass
        
        # 重置
        try:
            self.device.reset()
            logger.info("设备已重置")
            time.sleep(1)
        except Exception:
            pass
    
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
        packet.extend(struct.pack('<H', self.seq))
        self.seq = (self.seq + 1) & 0xFFFF
        
        packet.append(0x10)  # PC
        packet.append(0x00)
        packet.append(target)  # 目标
        packet.append(0x00)
        packet.append(cmd)
        packet.extend(data)
        
        crc = self.calculate_crc(packet[2:])
        packet.extend(struct.pack('<H', crc))
        
        return bytes(packet)
    
    def parse_response(self, data):
        """解析响应"""
        if len(data) < 14:
            logger.error("数据太短")
            return None
        
        if data[0] != 0x55 or data[1] != 0xAA:
            logger.error("无效头部")
            return None
        
        length = struct.unpack('<H', data[2:4])[0]
        version = data[4]
        seq = struct.unpack('<H', data[5:7])[0]
        src_type = data[7]
        src_idx = data[8]
        tgt_type = data[9]
        tgt_idx = data[10]
        cmd = data[11]
        payload = data[12:-2]
        crc = struct.unpack('<H', data[-2:])[0]
        
        logger.info("\n📦 解析响应:")
        logger.info(f"  长度: {length}")
        logger.info(f"  版本: {version}")
        logger.info(f"  序列号: {seq}")
        logger.info(f"  源设备类型: 0x{src_type:02X}")
        logger.info(f"  源设备编号: {src_idx}")
        logger.info(f"  目标设备类型: 0x{tgt_type:02X}")
        logger.info(f"  目标设备编号: {tgt_idx}")
        logger.info(f"  命令ID: 0x{cmd:02X}")
        logger.info(f"  数据长度: {len(payload)}")
        logger.info(f"  数据: {bytes(payload).hex()}")
        logger.info(f"  CRC: 0x{crc:04X}")
        
        return {
            'length': length,
            'version': version,
            'seq': seq,
            'src_type': src_type,
            'src_idx': src_idx,
            'tgt_type': tgt_type,
            'tgt_idx': tgt_idx,
            'cmd': cmd,
            'payload': bytes(payload),
            'crc': crc
        }
    
    def send_and_receive(self, packet, timeout=2000):
        """发送并接收"""
        logger.info(f"\n📤 发送: {packet.hex()}")
        
        try:
            # 发送
            sent = self.device.write(0x04, packet, timeout=1000)
            logger.info(f"✅ 发送成功: {sent} 字节")
            
            # 接收
            time.sleep(0.1)
            data = self.device.read(0x85, 512, timeout=timeout)
            
            # 转换为 bytes
            data_bytes = bytes(data)
            logger.info(f"✅ 接收成功: {len(data_bytes)} 字节")
            logger.info(f"📥 接收: {data_bytes.hex()}")
            
            return data_bytes
            
        except Exception as e:
            logger.error(f"❌ 通信失败: {e}")
            return None
    
    def run_tests(self):
        """运行测试"""
        logger.info("\n" + "="*60)
        logger.info("  测试端点 0x04/0x85")
        logger.info("="*60)
        
        # 测试命令列表
        tests = [
            ("心跳", 0xEA, b''),
            ("查询设备信息", 0x88, b''),
            ("查询状态", 0x0C, b''),
            ("进入升级模式", 0x07, b''),
        ]
        
        results = []
        
        for name, cmd, data in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"  测试: {name}")
            logger.info(f"{'='*60}")
            
            packet = self.create_packet(cmd=cmd, data=data)
            response = self.send_and_receive(packet)
            
            if response:
                parsed = self.parse_response(response)
                if parsed:
                    results.append((name, True, parsed))
                else:
                    results.append((name, False, None))
            else:
                results.append((name, False, None))
            
            time.sleep(0.5)
        
        # 汇总
        logger.info("\n" + "="*60)
        logger.info("  测试结果汇总")
        logger.info("="*60 + "\n")
        
        for name, success, parsed in results:
            status = "✅" if success else "❌"
            logger.info(f"{status} {name}")
            if parsed:
                logger.info(f"   命令: 0x{parsed['cmd']:02X}, 数据长度: {len(parsed['payload'])}")


def main():
    print("\n" + "="*60)
    print("  🚁 DJI 真实通信测试 - 端点 0x04/0x85")
    print("="*60 + "\n")
    
    test = DJIEndpoint4Test()
    
    if not test.find_device():
        print("  ❌ 未找到设备\n")
        return
    
    print("  ✅ 找到设备\n")
    
    test.init_device()
    test.run_tests()
    
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
