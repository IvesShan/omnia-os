#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 日志解析器
解析 .dat / .bin 飞行日志文件

作者: 无限 (Omnia)
日期: 2026-04-21
"""

import struct
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class FlightRecord:
    """飞行记录"""
    timestamp: float
    flight_time: int  # 秒
    battery_percent: int
    battery_voltage: float
    battery_current: float
    altitude: float
    speed: float
    gps_satellites: int
    gps_latitude: float
    gps_longitude: float
    imu_status: int
    motor_status: int
    gimbal_status: int
    camera_status: int
    temperature: float


class LogParser:
    """日志解析器"""
    
    # 日志类型标识
    LOG_TYPES = {
        b'STAT': 'state',      # 状态日志
        b'VISI': 'vision',     # 视觉日志
        b'GIMB': 'gimbal',     # 云台日志
        b'CAMR': 'camera',     # 相机日志
        b'NAVI': 'navigation', # 导航日志
    }
    
    def __init__(self):
        self.parsed_data = {}
    
    def parse(self, filepath: str) -> Dict[str, Any]:
        """
        解析日志文件
        
        参数:
            filepath: 日志文件路径
        
        返回:
            解析后的数据字典
        """
        if not os.path.exists(filepath):
            print(f"❌ 文件不存在: {filepath}")
            return {}
        
        print(f"📂 解析日志: {os.path.basename(filepath)}")
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # 检测日志类型
        log_type = self._detect_log_type(data)
        print(f"   日志类型: {log_type}")
        
        # 根据类型解析
        if log_type == 'state':
            return self._parse_state_log(data)
        elif log_type == 'vision':
            return self._parse_vision_log(data)
        elif log_type == 'gimbal':
            return self._parse_gimbal_log(data)
        elif log_type == 'camera':
            return self._parse_camera_log(data)
        else:
            return self._parse_generic_log(data)
    
    def _detect_log_type(self, data: bytes) -> str:
        """检测日志类型"""
        # 检查文件头
        if len(data) >= 4:
            header = data[:4]
            if header in self.LOG_TYPES:
                return self.LOG_TYPES[header]
        
        # 根据文件大小和特征判断
        if len(data) > 1000000:  # 大于1MB通常是状态日志
            return 'state'
        elif len(data) > 500000:
            return 'vision'
        else:
            return 'unknown'
    
    def _parse_state_log(self, data: bytes) -> Dict:
        """解析状态日志"""
        result = {
            'log_type': 'state',
            'file_size': len(data),
            'records': [],
            'statistics': {}
        }
        
        # 解析文件头 (假设有文件头结构)
        offset = 0
        if len(data) >= 64:
            # 解析文件头信息
            header = data[:64]
            result['header'] = {
                'magic': header[:4],
                'version': struct.unpack('<I', header[4:8])[0] if len(header) >= 8 else 0,
                'record_count': struct.unpack('<I', header[8:12])[0] if len(header) >= 12 else 0,
            }
            offset = 64
        
        # 解析记录
        record_size = 128  # 假设每条记录128字节
        record_count = 0
        
        while offset + record_size <= len(data):
            record_data = data[offset:offset+record_size]
            
            try:
                record = self._parse_state_record(record_data)
                if record:
                    result['records'].append(record)
                    record_count += 1
            except Exception as e:
                # 解析失败，跳过
                pass
            
            offset += record_size
        
        # 计算统计信息
        if result['records']:
            result['statistics'] = self._calculate_statistics(result['records'])
        
        print(f"   解析记录数: {record_count}")
        return result
    
    def _parse_state_record(self, data: bytes) -> Optional[Dict]:
        """解析单条状态记录"""
        if len(data) < 32:
            return None
        
        try:
            # 根据 DJI 状态日志格式解析
            # 注意：以下偏移量是示例，需要根据实际格式调整
            return {
                'timestamp': struct.unpack('<I', data[0:4])[0],
                'flight_time': struct.unpack('<I', data[4:8])[0],
                'battery_percent': data[8],
                'battery_voltage': struct.unpack('<H', data[9:11])[0] / 100.0,
                'altitude': struct.unpack('<h', data[11:13])[0] / 10.0,
                'speed': struct.unpack('<H', data[13:15])[0] / 100.0,
                'gps_satellites': data[15],
                'imu_status': data[16],
                'motor_status': struct.unpack('<H', data[17:19])[0],
                'temperature': struct.unpack('<h', data[19:21])[0] / 10.0,
            }
        except:
            return None
    
    def _parse_vision_log(self, data: bytes) -> Dict:
        """解析视觉日志"""
        result = {
            'log_type': 'vision',
            'file_size': len(data),
            'vision_data': []
        }
        
        # 视觉日志通常包含图像数据，这里只提取元数据
        offset = 0
        while offset < len(data):
            # 查找视觉数据块标记
            marker = data[offset:offset+4]
            if marker == b'VISI':
                # 解析视觉数据块
                block_size = struct.unpack('<I', data[offset+4:offset+8])[0]
                vision_data = data[offset+8:offset+8+block_size]
                
                result['vision_data'].append({
                    'offset': offset,
                    'size': block_size,
                    'data': vision_data[:64]  # 只保存前64字节用于分析
                })
                
                offset += 8 + block_size
            else:
                offset += 1
        
        return result
    
    def _parse_gimbal_log(self, data: bytes) -> Dict:
        """解析云台日志"""
        result = {
            'log_type': 'gimbal',
            'file_size': len(data),
            'gimbal_records': []
        }
        
        # 解析云台状态记录
        record_size = 64
        offset = 0
        
        while offset + record_size <= len(data):
            record_data = data[offset:offset+record_size]
            
            try:
                record = {
                    'timestamp': struct.unpack('<I', record_data[0:4])[0],
                    'pitch': struct.unpack('<h', record_data[4:6])[0] / 100.0,
                    'roll': struct.unpack('<h', record_data[6:8])[0] / 100.0,
                    'yaw': struct.unpack('<h', record_data[8:10])[0] / 100.0,
                    'status': record_data[10],
                }
                result['gimbal_records'].append(record)
            except:
                pass
            
            offset += record_size
        
        return result
    
    def _parse_camera_log(self, data: bytes) -> Dict:
        """解析相机日志"""
        result = {
            'log_type': 'camera',
            'file_size': len(data),
            'camera_records': []
        }
        
        # 解析相机记录
        record_size = 48
        offset = 0
        
        while offset + record_size <= len(data):
            record_data = data[offset:offset+record_size]
            
            try:
                record = {
                    'timestamp': struct.unpack('<I', record_data[0:4])[0],
                    'iso': struct.unpack('<H', record_data[4:6])[0],
                    'shutter_speed': struct.unpack('<I', record_data[6:10])[0],
                    'aperture': struct.unpack('<H', record_data[10:12])[0] / 100.0,
                    'image_count': struct.unpack('<I', record_data[12:16])[0],
                }
                result['camera_records'].append(record)
            except:
                pass
            
            offset += record_size
        
        return result
    
    def _parse_generic_log(self, data: bytes) -> Dict:
        """通用日志解析"""
        return {
            'log_type': 'unknown',
            'file_size': len(data),
            'hex_preview': data[:64].hex(),
            'ascii_preview': self._bytes_to_ascii(data[:64])
        }
    
    def _calculate_statistics(self, records: List[Dict]) -> Dict:
        """计算统计信息"""
        if not records:
            return {}
        
        flight_times = [r['flight_time'] for r in records]
        battery_percents = [r['battery_percent'] for r in records]
        voltages = [r['battery_voltage'] for r in records]
        temperatures = [r['temperature'] for r in records]
        
        return {
            'total_flight_time': max(flight_times) - min(flight_times),
            'avg_battery': sum(battery_percents) / len(battery_percents),
            'min_battery': min(battery_percents),
            'avg_voltage': sum(voltages) / len(voltages),
            'min_voltage': min(voltages),
            'max_temperature': max(temperatures),
            'avg_temperature': sum(temperatures) / len(temperatures),
        }
    
    def _bytes_to_ascii(self, data: bytes) -> str:
        """将字节转换为可打印ASCII"""
        result = []
        for b in data:
            if 32 <= b <= 126:
                result.append(chr(b))
            else:
                result.append('.')
        return ''.join(result)
    
    def extract_errors(self, parsed_data: Dict) -> List[str]:
        """从解析数据中提取错误信息"""
        errors = []
        
        if 'records' in parsed_data:
            for record in parsed_data['records']:
                # 检查异常值
                if record.get('battery_percent', 100) < 10:
                    errors.append(f"低电量警告: {record['battery_percent']}%")
                
                if record.get('temperature', 0) > 60:
                    errors.append(f"高温警告: {record['temperature']}°C")
                
                if record.get('gps_satellites', 10) < 4:
                    errors.append(f"GPS信号弱: {record['gps_satellites']}颗星")
        
        return errors
    
    def get_flight_summary(self, parsed_data: Dict) -> Dict:
        """获取飞行摘要"""
        summary = {
            'total_records': 0,
            'flight_duration': 0,
            'max_altitude': 0,
            'max_speed': 0,
            'battery_min': 100,
            'temperature_max': 0,
        }
        
        if 'records' in parsed_data and parsed_data['records']:
            records = parsed_data['records']
            summary['total_records'] = len(records)
            
            flight_times = [r.get('flight_time', 0) for r in records]
            altitudes = [r.get('altitude', 0) for r in records]
            speeds = [r.get('speed', 0) for r in records]
            batteries = [r.get('battery_percent', 100) for r in records]
            temperatures = [r.get('temperature', 0) for r in records]
            
            summary['flight_duration'] = max(flight_times) - min(flight_times)
            summary['max_altitude'] = max(altitudes)
            summary['max_speed'] = max(speeds)
            summary['battery_min'] = min(batteries)
            summary['temperature_max'] = max(temperatures)
        
        return summary
