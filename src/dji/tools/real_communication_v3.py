#!/usr/bin/env python3
"""
DJI 真实通信实现 v3
尝试多种初始化方式和接口
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


class DJIRealCommunicationV3:
    """DJI 真实通信类 v3"""
    
    # 设备类型
    DEVICE_TYPE_PC = 0x10
    DEVICE_TYPE_FC = 0x0a
    
    # 命令ID
    CMD_QUERY_DEVICE_INFO = 0x88
    CMD_HEARTBEAT = 0xEA
    
    # 接口配置（多个候选）
    INTERFACES = [
        {'num': 5, 'ep_out': 0x05, 'ep_in': 0x86, 'name': '主通信协议'},
        {'num': 3, 'ep_out': 0x03, 'ep_in': 0x84, 'name': '调试总线'},
        {'num': 4, 'ep_out': 0x04, 'ep_in': 0x85, 'name': '备用通道'},
        {'num': 6, 'ep_out': 0x06, 'ep_in': 0x87, 'name': '扩展通道'},
        {'num': 1, 'ep_out': 0x01, 'ep_in': 0x81, 'name': 'CDC数据'},
    ]
    
    def __init__(self):
        self.device = None
        self.current_interface = None
        self.seq_number = 0
        
    def find_device(self):
        """查找 DJI 设备"""
        device = usb.core.find(idVendor=0x2ca3)
        if device:
            self.device = device
            serial = usb.util.get_string(device, device.iSerialNumber) if device.iSerialNumber else 'Unknown'
            logger.info(f"找到设备: {serial}")
            return True
        return False
    
    def try_interface(self, interface_config):
        """尝试使用指定接口"""
        logger.info(f"\n尝试接口 {interface_config['num']} ({interface_config['name']})...")
        
        try:
            # 解除内核驱动
            if self.device.is_kernel_driver_active(interface_config['num']):
                self.device.detach_kernel_driver(interface_config['num'])
                logger.info(f"  已解除内核驱动")
            
            # 设置配置
            try:
                self.device.set_configuration()
            except:
                pass
            
            # 等待稳定
            time.sleep(0.1)
            
            # 尝试发送测试数据
            test_packet = self.create_simple_test()
            
            try:
                bytes_written = self.device.write(
                    interface_config['ep_out'], 
                    test_packet, 
                    timeout=1000
                )
                logger.info(f"  ✅ 发送成功: {bytes_written} 字节")
                
                # 尝试接收
                try:
                    data = self.device.read(
                        interface_config['ep_in'], 
                        512, 
                        timeout=1000
                    )
                    logger.info(f"  ✅ 接收成功: {len(data)} 字节")
                    logger.info(f"  数据: {data.hex()}")
                    return True
                except usb.core.USBError as e:
                    if e.errno == 110:  # Timeout
                        logger.warning(f"  ⚠️  接收超时（但发送成功）")
                        return True
                    else:
                        logger.error(f"  ❌ 接收失败: {e}")
                        
            except usb.core.USBError as e:
                logger.error(f"  ❌ 发送失败: {e}")
                
        except Exception as e:
            logger.error(f"  ❌ 接口初始化失败: {e}")
        
        return False
    
    def create_simple_test(self):
        """创建简单的测试数据包"""
        # 简单的查询命令
        packet = bytearray()
        packet.extend([0x55, 0xAA])  # 头部
        packet.extend(struct.pack('<H', 10))  # 长度
        packet.append(0x00)  # 版本
        packet.extend(struct.pack('<H', 0))  # 序列号
        packet.append(self.DEVICE_TYPE_PC)  # 源类型
        packet.append(0x00)  # 源编号
        packet.append(self.DEVICE_TYPE_FC)  # 目标类型
        packet.append(0x00)  # 目标编号
        packet.append(self.CMD_QUERY_DEVICE_INFO)  # 命令
        
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
    
    def test_all_interfaces(self):
        """测试所有接口"""
        logger.info("\n" + "="*60)
        logger.info("  测试所有可用接口")
        logger.info("="*60)
        
        for interface_config in self.INTERFACES:
            if self.try_interface(interface_config):
                self.current_interface = interface_config
                logger.info(f"\n  🎉 找到可用接口: {interface_config['name']}")
                return True
            time.sleep(0.2)
        
        return False
    
    def send_command(self, cmd_id, data=b''):
        """发送命令"""
        if not self.current_interface:
            logger.error("未选择接口")
            return None
        
        packet = self.create_packet(self.DEVICE_TYPE_FC, cmd_id, data)
        
        try:
            # 发送
            bytes_written = self.device.write(
                self.current_interface['ep_out'],
                packet,
                timeout=1000
            )
            logger.info(f"发送 {bytes_written} 字节: {packet.hex()}")
            
            # 接收
            response = self.device.read(
                self.current_interface['ep_in'],
                512,
                timeout=2000
            )
            logger.info(f"接收 {len(response)} 字节: {response.hex()}")
            return response
            
        except Exception as e:
            logger.error(f"通信失败: {e}")
            return None
    
    def create_packet(self, target_type, cmd_id, data=b''):
        """创建数据包"""
        packet = bytearray()
        packet.extend([0x55, 0xAA])
        
        length = len(data) + 10
        packet.extend(struct.pack('<H', length))
        packet.append(0x00)
        packet.extend(struct.pack('<H', self.seq_number))
        self.seq_number = (self.seq_number + 1) & 0xFFFF
        
        packet.append(self.DEVICE_TYPE_PC)
        packet.append(0x00)
        packet.append(target_type)
        packet.append(0x00)
        packet.append(cmd_id)
        packet.extend(data)
        
        crc = self.calculate_crc(packet[2:])
        packet.extend(struct.pack('<H', crc))
        
        return bytes(packet)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  🚁 DJI 真实通信测试 v3")
    print("="*60 + "\n")
    
    comm = DJIRealCommunicationV3()
    
    # 查找设备
    if not comm.find_device():
        print("  ❌ 未找到设备\n")
        return
    
    # 测试所有接口
    if comm.test_all_interfaces():
        print("\n" + "="*60)
        print("  测试通信")
        print("="*60 + "\n")
        
        # 尝试发送命令
        for i in range(3):
            print(f"\n[{i+1}/3] 发送心跳命令...")
            response = comm.send_command(0xEA)
            if response:
                print(f"  ✅ 收到响应")
            else:
                print(f"  ❌ 无响应")
            time.sleep(0.5)
    else:
        print("\n  ❌ 所有接口都不可用")
    
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
