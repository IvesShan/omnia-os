#!/usr/bin/env python3
"""
DJI 真实通信实现
使用 sudo 权限进行 USB Bulk 传输
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import usb.core
import usb.util
import logging
import struct

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DJIRealCommunication:
    """DJI 真实通信类"""
    
    def __init__(self):
        self.device = None
        self.interface_num = 5
        self.endpoint_out = 0x05
        self.endpoint_in = 0x86
        self.seq_number = 0
        
    def find_device(self):
        """查找 DJI 设备"""
        devices = list(usb.core.find(find_all=True, idVendor=0x2ca3))
        
        if devices:
            self.device = devices[0]
            logger.info(f"找到设备: {self.device.serial_number if hasattr(self.device, 'serial_number') else 'Unknown'}")
            return True
        
        logger.error("未找到 DJI 设备")
        return False
    
    def connect(self):
        """连接设备"""
        try:
            # 解除内核驱动
            if self.device.is_kernel_driver_active(self.interface_num):
                self.device.detach_kernel_driver(self.interface_num)
                logger.info("已解除内核驱动")
            
            # 设置配置
            self.device.set_configuration()
            
            # 占用接口
            usb.util.claim_interface(self.device, self.interface_num)
            
            logger.info("连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.device:
                usb.util.release_interface(self.device, self.interface_num)
                usb.util.dispose_resources(self.device)
            
            logger.info("已断开连接")
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
    
    def calculate_crc(self, data):
        """计算 CRC16 校验码"""
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
    
    def create_packet(self, target_type, cmd_id, data=b''):
        """创建 DJI 数据包"""
        # 数据包结构:
        # [头部 2字节] [长度 2字节] [版本 1字节] [序列号 2字节]
        # [源设备类型 1字节] [源设备编号 1字节]
        # [目标设备类型 1字节] [目标设备编号 1字节]
        # [命令ID 1字节] [数据 N字节] [CRC 2字节]
        
        packet = bytearray()
        packet.extend([0x55, 0xAA])  # 头部
        
        length = len(data) + 10  # 数据长度 + 头部之后的字节数
        packet.extend(struct.pack('<H', length))  # 长度
        packet.append(0x00)  # 版本
        packet.extend(struct.pack('<H', self.seq_number))  # 序列号
        self.seq_number += 1
        
        packet.append(0x10)  # 源设备类型 (PC)
        packet.append(0x00)  # 源设备编号
        packet.append(target_type)  # 目标设备类型
        packet.append(0x00)  # 目标设备编号
        packet.append(cmd_id)  # 命令ID
        packet.extend(data)  # 数据
        
        # 计算 CRC
        crc = self.calculate_crc(packet)
        packet.extend(struct.pack('<H', crc))
        
        return bytes(packet)
    
    def send_packet(self, packet):
        """发送数据包"""
        try:
            bytes_written = self.device.write(
                self.endpoint_out,
                packet,
                timeout=2000
            )
            
            logger.info(f"发送 {bytes_written} 字节")
            logger.debug(f"数据: {' '.join(f'{b:02x}' for b in packet)}")
            
            return bytes_written == len(packet)
            
        except Exception as e:
            logger.error(f"发送失败: {e}")
            return False
    
    def receive_packet(self, timeout=3000):
        """接收数据包"""
        try:
            data = self.device.read(
                self.endpoint_in,
                4096,
                timeout=timeout
            )
            
            logger.info(f"接收 {len(data)} 字节")
            logger.debug(f"数据: {' '.join(f'{b:02x}' for b in data[:20])}")
            
            return bytes(data)
            
        except usb.core.USBError as e:
            if e.errno == 110:  # Timeout
                logger.warning("接收超时")
            else:
                logger.error(f"接收失败: {e}")
            return None
    
    def query_device_info(self, device_type=0x0A):
        """查询设备信息（飞控）"""
        logger.info(f"查询设备信息: 设备类型=0x{device_type:02x}")
        
        # 创建查询数据包
        packet = self.create_packet(device_type, 0x88, b'')
        
        # 发送
        if not self.send_packet(packet):
            return None
        
        # 接收响应
        response = self.receive_packet()
        
        if response:
            return self.parse_device_info(response)
        
        return None
    
    def parse_device_info(self, data):
        """解析设备信息"""
        if len(data) < 14:
            logger.error("数据太短")
            return None
        
        # 检查头部
        if data[:2] != b'\x55\xAA':
            logger.error("无效的头部")
            return None
        
        # 解析
        length = struct.unpack('<H', data[2:4])[0]
        seq_number = struct.unpack('<H', data[5:7])[0]
        source_type = data[7]
        target_type = data[9]
        cmd_id = data[11]
        
        logger.info(f"响应: 命令=0x{cmd_id:02x}, 源设备=0x{source_type:02x}, 长度={length}")
        
        # 提取数据部分
        if len(data) > 14:
            device_data = data[12:-2]
            logger.info(f"设备数据: {' '.join(f'{b:02x}' for b in device_data[:20])}")
            
            return {
                'raw': data,
                'length': length,
                'seq_number': seq_number,
                'source_type': source_type,
                'target_type': target_type,
                'cmd_id': cmd_id,
                'data': device_data
            }
        
        return {
            'raw': data,
            'length': length,
            'cmd_id': cmd_id
        }


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  🚁 DJI 真实通信测试")
    print("="*60)
    
    # 检查权限
    if os.geteuid() != 0:
        print("\n  ❌ 需要 root 权限")
        print("  使用: sudo python3 real_communication.py")
        return
    
    comm = DJIRealCommunication()
    
    # 查找设备
    if not comm.find_device():
        print("\n  ❌ 未找到设备")
        return
    
    # 连接
    if not comm.connect():
        print("\n  ❌ 连接失败")
        return
    
    try:
        # 测试查询设备信息
        print("\n" + "="*60)
        print("  📋 查询设备信息")
        print("="*60)
        
        result = comm.query_device_info(device_type=0x0A)  # 飞控
        
        if result:
            print("\n  ✅ 查询成功！")
            print(f"  命令ID: 0x{result['cmd_id']:02x}")
            if 'data' in result:
                print(f"  数据长度: {len(result['data'])} 字节")
        else:
            print("\n  ❌ 查询失败")
        
    finally:
        # 断开连接
        comm.disconnect()
    
    print("\n" + "="*60)
    print("  ✅ 测试完成")
    print("="*60)


if __name__ == '__main__':
    main()
