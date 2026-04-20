#!/usr/bin/env python3
"""
DJI 真实通信实现 v2
解决内核驱动问题，实现完整通信流程
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


class DJIRealCommunicationV2:
    """DJI 真实通信类 v2"""
    
    # 设备类型
    DEVICE_TYPE_PC = 0x10
    DEVICE_TYPE_FC = 0x0a  # 飞控
    DEVICE_TYPE_CAMERA = 0x03
    DEVICE_TYPE_GIMBAL = 0x08
    DEVICE_TYPE_PERCEPTION = 0x12  # 感知模块
    
    # 命令ID
    CMD_QUERY_DEVICE_INFO = 0x88
    CMD_QUERY_DEVICE_STATUS = 0x0C
    CMD_HEARTBEAT = 0xEA
    CMD_ENTER_UPGRADE = 0x07
    
    def __init__(self):
        self.device = None
        self.interface_num = 5
        self.endpoint_out = 0x05
        self.endpoint_in = 0x86
        self.seq_number = 0
        self.attached_drivers = []
        
    def find_device(self):
        """查找 DJI 设备"""
        devices = list(usb.core.find(find_all=True, idVendor=0x2ca3))
        
        if devices:
            self.device = devices[0]
            serial = usb.util.get_string(self.device, self.device.iSerialNumber) if self.device.iSerialNumber else 'Unknown'
            manufacturer = usb.util.get_string(self.device, self.device.iManufacturer) if self.device.iManufacturer else 'Unknown'
            product = usb.util.get_string(self.device, self.device.iProduct) if self.device.iProduct else 'Unknown'
            
            logger.info(f"找到设备: {serial}")
            logger.info(f"  制造商: {manufacturer}")
            logger.info(f"  产品: {product}")
            return True
        
        logger.error("未找到 DJI 设备")
        return False
    
    def connect(self):
        """连接设备"""
        try:
            # 检查并解除所有接口的内核驱动
            for cfg in self.device:
                for intf in cfg:
                    interface_number = intf.bInterfaceNumber
                    try:
                        if self.device.is_kernel_driver_active(interface_number):
                            self.device.detach_kernel_driver(interface_number)
                            self.attached_drivers.append(interface_number)
                            logger.info(f"已解除接口 {interface_number} 的内核驱动")
                    except Exception as e:
                        logger.warning(f"接口 {interface_number} 解除驱动失败: {e}")
            
            # 设置配置
            try:
                self.device.set_configuration()
                logger.info("已设置设备配置")
            except Exception as e:
                logger.warning(f"设置配置失败（可能已设置）: {e}")
            
            # 等待设备稳定
            time.sleep(0.1)
            
            logger.info("连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.device:
                # 释放资源
                usb.util.dispose_resources(self.device)
                
                # 重新附加内核驱动
                for interface_number in self.attached_drivers:
                    try:
                        usb.util.claim_interface(self.device, interface_number)
                        self.device.attach_kernel_driver(interface_number)
                        usb.util.release_interface(self.device, interface_number)
                        logger.info(f"已重新附加接口 {interface_number} 的内核驱动")
                    except Exception as e:
                        logger.warning(f"重新附加驱动失败: {e}")
            
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
        self.seq_number = (self.seq_number + 1) & 0xFFFF
        
        packet.append(self.DEVICE_TYPE_PC)  # 源设备类型
        packet.append(0x00)  # 源设备编号
        packet.append(target_type)  # 目标设备类型
        packet.append(0x00)  # 目标设备编号
        packet.append(cmd_id)  # 命令ID
        packet.extend(data)  # 数据
        
        # 计算CRC（不包括头部）
        crc = self.calculate_crc(packet[2:])
        packet.extend(struct.pack('<H', crc))
        
        return bytes(packet)
    
    def send_packet(self, packet, timeout=1000):
        """发送数据包"""
        try:
            bytes_written = self.device.write(self.endpoint_out, packet, timeout=timeout)
            logger.info(f"已发送 {bytes_written} 字节")
            logger.debug(f"数据: {packet.hex()}")
            return bytes_written
        except Exception as e:
            logger.error(f"发送失败: {e}")
            return 0
    
    def receive_packet(self, timeout=1000, max_length=512):
        """接收数据包"""
        try:
            data = self.device.read(self.endpoint_in, max_length, timeout=timeout)
            logger.info(f"已接收 {len(data)} 字节")
            logger.debug(f"数据: {data.hex()}")
            return data
        except usb.core.USBError as e:
            if e.errno == 110:  # Timeout
                logger.warning("接收超时")
            else:
                logger.error(f"接收失败: {e}")
            return None
        except Exception as e:
            logger.error(f"接收失败: {e}")
            return None
    
    def parse_packet(self, data):
        """解析数据包"""
        if len(data) < 14:
            logger.error("数据包太短")
            return None
        
        # 检查头部
        if data[0] != 0x55 or data[1] != 0xAA:
            logger.error("无效的头部")
            return None
        
        # 解析字段
        length = struct.unpack('<H', data[2:4])[0]
        version = data[4]
        seq_number = struct.unpack('<H', data[5:7])[0]
        source_type = data[7]
        source_index = data[8]
        target_type = data[9]
        target_index = data[10]
        cmd_id = data[11]
        payload = data[12:-2]
        crc = struct.unpack('<H', data[-2:])[0]
        
        # 验证CRC
        calculated_crc = self.calculate_crc(data[2:-2])
        if calculated_crc != crc:
            logger.warning(f"CRC校验失败: 计算值 {calculated_crc:04X}, 接收值 {crc:04X}")
        
        return {
            'length': length,
            'version': version,
            'seq_number': seq_number,
            'source_type': source_type,
            'source_index': source_index,
            'target_type': target_type,
            'target_index': target_index,
            'cmd_id': cmd_id,
            'payload': payload,
            'crc': crc,
            'crc_valid': calculated_crc == crc
        }
    
    def query_device_info(self):
        """查询设备信息"""
        logger.info("查询设备信息...")
        
        # 发送查询命令
        packet = self.create_packet(self.DEVICE_TYPE_FC, self.CMD_QUERY_DEVICE_INFO)
        if self.send_packet(packet) == 0:
            return None
        
        # 接收响应
        response = self.receive_packet(timeout=2000)
        if response is None:
            return None
        
        # 解析响应
        parsed = self.parse_packet(response)
        if parsed is None:
            return None
        
        logger.info(f"收到响应: 命令ID=0x{parsed['cmd_id']:02X}, 数据长度={len(parsed['payload'])}")
        return parsed
    
    def send_heartbeat(self):
        """发送心跳"""
        logger.info("发送心跳...")
        
        packet = self.create_packet(self.DEVICE_TYPE_FC, self.CMD_HEARTBEAT)
        if self.send_packet(packet) == 0:
            return False
        
        response = self.receive_packet(timeout=1000)
        if response:
            parsed = self.parse_packet(response)
            if parsed:
                logger.info(f"心跳响应: 命令ID=0x{parsed['cmd_id']:02X}")
                return True
        
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  🚁 DJI 真实通信测试 v2")
    print("="*60 + "\n")
    
    comm = DJIRealCommunicationV2()
    
    # 查找设备
    if not comm.find_device():
        print("  ❌ 未找到设备")
        return
    
    # 连接设备
    if not comm.connect():
        print("  ❌ 连接失败")
        return
    
    try:
        print("  ✅ 连接成功\n")
        
        # 测试1: 发送心跳
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  测试 1: 发送心跳")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        if comm.send_heartbeat():
            print("  ✅ 心跳成功\n")
        else:
            print("  ⚠️  心跳无响应\n")
        
        time.sleep(0.5)
        
        # 测试2: 查询设备信息
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  测试 2: 查询设备信息")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        result = comm.query_device_info()
        if result:
            print(f"  ✅ 查询成功")
            print(f"     命令ID: 0x{result['cmd_id']:02X}")
            print(f"     数据长度: {len(result['payload'])}")
            print(f"     CRC校验: {'✅' if result['crc_valid'] else '❌'}\n")
        else:
            print("  ⚠️  查询无响应\n")
        
        # 测试3: 循环测试
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  测试 3: 持续通信测试 (5次)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        success_count = 0
        for i in range(5):
            print(f"  [{i+1}/5] 发送心跳...", end=" ")
            if comm.send_heartbeat():
                print("✅")
                success_count += 1
            else:
                print("❌")
            time.sleep(0.5)
        
        print(f"\n  成功率: {success_count}/5 ({success_count*20}%)\n")
        
    finally:
        # 断开连接
        comm.disconnect()
    
    print("="*60)
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
