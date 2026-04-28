"""
DJI v1 通信协议实现
基于 DJI Assistant 2 逆向分析
"""

import struct
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)


class DeviceType(IntEnum):
    """设备类型编码"""
    PERCEPTION = 0x12  # 感知模块
    FLIGHT_CONTROLLER = 0x0a  # 飞控
    CAMERA = 0x03  # 相机
    GIMBAL = 0x08  # 云台
    PC = 0x10  # 电脑端
    BATTERY = 0x0b  # 电池
    GPS = 0x04  # GPS模块
    IMU = 0x05  # IMU
    COMPASS = 0x06  # 指南针
    RC = 0x07  # 遥控器
    WIFI = 0x0e  # WiFi模块
    UNKNOWN = 0xff


class CommandID(IntEnum):
    """命令ID"""
    QUERY_DEVICE_INFO = 0x88  # 查询设备信息
    QUERY_DEVICE_STATUS = 0x0C  # 查询设备状态
    QUERY_COMMUNICATION_INFO = 0x88  # 查询通信信息
    ENTER_UPGRADE = 0x07  # 进入升级模式
    REBOOT_DEVICE = 0x0b  # 重启设备
    COMMAND = 0x41  # 通用命令
    HEARTBEAT = 0xEA  # 心跳包
    RETURN = 0x87  # 返回响应
    ACK = 0x00  # 确认响应


@dataclass
class DJIPacket:
    """DJI数据包结构"""
    header: bytes = b'\x55\xAA'  # 固定头部
    length: int = 0  # 数据长度
    version: int = 0  # 版本号
    seq_number: int = 0  # 序列号
    source_type: int = DeviceType.PC  # 源设备类型
    source_num: int = 0  # 源设备编号
    target_type: int = 0  # 目标设备类型
    target_num: int = 0  # 目标设备编号
    cmd_id: int = 0  # 命令ID
    data: bytes = b''  # 数据内容
    crc: int = 0  # 校验码
    
    def __post_init__(self):
        """计算长度和CRC"""
        self.length = len(self.data) + 10  # 头部之后的字节数
        self.crc = self._calculate_crc()
    
    def _calculate_crc(self) -> int:
        """计算CRC16校验码"""
        # DJI使用的CRC16算法
        crc = 0
        packet_bytes = self.to_bytes(include_crc=False)
        for byte in packet_bytes:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc
    
    def to_bytes(self, include_crc: bool = True) -> bytes:
        """转换为字节数组"""
        result = bytearray()
        result.extend(self.header)
        result.extend(struct.pack('<H', self.length))
        result.append(self.version)
        result.extend(struct.pack('<H', self.seq_number))
        result.append(self.source_type)
        result.append(self.source_num)
        result.append(self.target_type)
        result.append(self.target_num)
        result.append(self.cmd_id)
        result.extend(self.data)
        
        if include_crc:
            result.extend(struct.pack('<H', self.crc))
        
        return bytes(result)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['DJIPacket']:
        """从字节数组解析数据包"""
        if len(data) < 14:  # 最小包长度
            return None
        
        # 检查头部
        if data[:2] != b'\x55\xAA':
            return None
        
        try:
            packet = cls()
            packet.header = data[:2]
            packet.length = struct.unpack('<H', data[2:4])[0]
            packet.version = data[4]
            packet.seq_number = struct.unpack('<H', data[5:7])[0]
            packet.source_type = data[7]
            packet.source_num = data[8]
            packet.target_type = data[9]
            packet.target_num = data[10]
            packet.cmd_id = data[11]
            
            # 提取数据部分
            data_length = packet.length - 10
            if data_length > 0:
                packet.data = data[12:12 + data_length]
            
            # 提取CRC
            crc_offset = 12 + data_length
            if len(data) >= crc_offset + 2:
                packet.crc = struct.unpack('<H', data[crc_offset:crc_offset + 2])[0]
            
            return packet
        except Exception as e:
            logger.error(f"解析数据包失败: {e}")
            return None


class V1Protocol:
    """DJI v1 协议处理器"""
    
    def __init__(self):
        self.seq_number = 0
        self.timeout = 1.0  # 默认超时时间
        self.retry_count = 3  # 重试次数
        
    def _get_next_seq(self) -> int:
        """获取下一个序列号"""
        self.seq_number = (self.seq_number + 1) & 0xFFFF
        return self.seq_number
    
    def build_query_device_info(self, target_type: int, target_num: int = 0) -> DJIPacket:
        """构建查询设备信息命令"""
        return DJIPacket(
            seq_number=self._get_next_seq(),
            source_type=DeviceType.PC,
            source_num=0,
            target_type=target_type,
            target_num=target_num,
            cmd_id=CommandID.QUERY_DEVICE_INFO,
            data=b''
        )
    
    def build_query_device_status(self, target_type: int, target_num: int = 0) -> DJIPacket:
        """构建查询设备状态命令"""
        return DJIPacket(
            seq_number=self._get_next_seq(),
            source_type=DeviceType.PC,
            source_num=0,
            target_type=target_type,
            target_num=target_num,
            cmd_id=CommandID.QUERY_DEVICE_STATUS,
            data=b''
        )
    
    def build_heartbeat(self) -> DJIPacket:
        """构建心跳包"""
        return DJIPacket(
            seq_number=self._get_next_seq(),
            source_type=DeviceType.PC,
            source_num=0,
            target_type=DeviceType.FLIGHT_CONTROLLER,
            target_num=0,
            cmd_id=CommandID.HEARTBEAT,
            data=b''
        )
    
    def build_enter_upgrade(self, target_type: int, target_num: int = 0) -> DJIPacket:
        """构建进入升级模式命令"""
        return DJIPacket(
            seq_number=self._get_next_seq(),
            source_type=DeviceType.PC,
            source_num=0,
            target_type=target_type,
            target_num=target_num,
            cmd_id=CommandID.ENTER_UPGRADE,
            data=b''
        )
    
    def build_reboot(self, target_type: int, target_num: int = 0) -> DJIPacket:
        """构建重启设备命令"""
        return DJIPacket(
            seq_number=self._get_next_seq(),
            source_type=DeviceType.PC,
            source_num=0,
            target_type=target_type,
            target_num=target_num,
            cmd_id=CommandID.REBOOT_DEVICE,
            data=b''
        )
    
    def parse_response(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析响应数据"""
        packet = DJIPacket.from_bytes(data)
        if not packet:
            return None
        
        result = {
            'cmd_id': packet.cmd_id,
            'seq_number': packet.seq_number,
            'source_type': packet.source_type,
            'source_num': packet.source_num,
            'target_type': packet.target_type,
            'target_num': packet.target_num,
            'data': packet.data,
            'raw_packet': packet
        }
        
        # 解析特定命令的响应
        if packet.cmd_id == CommandID.RETURN:
            result['response_type'] = 'return'
            if len(packet.data) >= 2:
                result['ret_code'] = packet.data[0]
                result['seq_number_response'] = struct.unpack('<H', packet.data[1:3])[0] if len(packet.data) >= 3 else 0
        
        elif packet.cmd_id == CommandID.QUERY_DEVICE_INFO:
            result['response_type'] = 'device_info'
            result.update(self._parse_device_info(packet.data))
        
        elif packet.cmd_id == CommandID.QUERY_DEVICE_STATUS:
            result['response_type'] = 'device_status'
            result.update(self._parse_device_status(packet.data))
        
        return result
    
    def _parse_device_info(self, data: bytes) -> Dict[str, Any]:
        """解析设备信息响应"""
        info = {}
        
        if len(data) < 20:
            return info
        
        try:
            # 设备型号代码 (例如: wm161)
            model_code = data[0:6].decode('ascii', errors='ignore').strip('\x00')
            info['model_code'] = model_code
            
            # 固件版本
            if len(data) >= 10:
                firmware_version = f"{data[6]}.{data[7]}.{data[8]}.{data[9]}"
                info['firmware_version'] = firmware_version
            
            # 序列号
            if len(data) >= 30:
                serial_number = data[10:30].decode('ascii', errors='ignore').strip('\x00')
                info['serial_number'] = serial_number
            
        except Exception as e:
            logger.error(f"解析设备信息失败: {e}")
        
        return info
    
    def _parse_device_status(self, data: bytes) -> Dict[str, Any]:
        """解析设备状态响应"""
        status = {}
        
        if len(data) < 10:
            return status
        
        try:
            # 状态标志位
            status['flags'] = data[0]
            
            # 错误代码
            if len(data) >= 3:
                status['error_code'] = struct.unpack('<H', data[1:3])[0]
            
            # 温度
            if len(data) >= 5:
                status['temperature'] = struct.unpack('<H', data[3:5])[0] / 10.0
            
            # 电压
            if len(data) >= 7:
                status['voltage'] = struct.unpack('<H', data[5:7])[0] / 1000.0
            
            # 电池百分比
            if len(data) >= 8:
                status['battery_percent'] = data[7]
            
        except Exception as e:
            logger.error(f"解析设备状态失败: {e}")
        
        return status


# 设备型号映射
DEVICE_MODEL_MAP = {
    'wm160': 'Mini SE',
    'wm161': 'Mini 2',
    'wm1615': 'Mini 2 SE',
    'wm163': 'Mini 3',
    'wm1605': 'Mini 3 Pro',
    'wm170': 'Mini 4 Pro',
    'wm231': 'Air 2S',
    'wm232': 'Mavic Air 2',
    'wm240': 'Mavic 3',
    'wm245': 'Mavic 3 Classic',
    'wm246': 'Mavic 3 Pro',
    'wm260': 'Mavic 2 Pro',
    'wm2605': 'Mavic 2 Zoom',
    'wm334': 'Phantom 4',
    'wm336': 'Phantom 4 Pro',
    'rc221': 'RC-N1',
    'rc430': 'RC Pro',
    'rc600': 'RC Plus',
    'wa140': 'Goggles 2',
    'wa152': 'Goggles 3',
    'hg330': 'DJI FPV',
    'hg910': 'Avata',
}


def get_device_name(model_code: str) -> str:
    """根据型号代码获取设备名称"""
    return DEVICE_MODEL_MAP.get(model_code.lower(), f'Unknown ({model_code})')
