"""
DJI 设备管理器
统一管理USB和串口连接，提供设备发现和通信功能
"""

from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
import logging
import time

from ..protocols.v1_protocol import DeviceType, CommandID, get_device_name
from ..transport.usb_transport import USBTransport, USBConfig, list_dji_devices
from ..transport.serial_transport import SerialTransport, SerialConfig

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """设备信息"""
    device_type: int
    device_type_name: str
    device_num: int
    model_code: str
    model_name: str
    firmware_version: str
    serial_number: str
    status: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        return {
            'device_type': self.device_type,
            'device_type_name': self.device_type_name,
            'device_num': self.device_num,
            'model_code': self.model_code,
            'model_name': self.model_name,
            'firmware_version': self.firmware_version,
            'serial_number': self.serial_number,
            'status': self.status,
        }


class DJIDeviceManager:
    """DJI设备管理器"""
    
    def __init__(self):
        self.transport: Optional[Union[USBTransport, SerialTransport]] = None
        self.connected_devices: List[DeviceInfo] = []
        self.connection_type: Optional[str] = None  # 'usb' or 'serial'
        
    def connect_usb(self, vendor_id: int = 0x2ca3, product_id: int = 0x0020) -> bool:
        """通过USB连接"""
        try:
            config = USBConfig(vendor_id=vendor_id, product_id=product_id)
            self.transport = USBTransport(config)
            
            if self.transport.connect():
                self.connection_type = 'usb'
                logger.info("USB连接成功")
                return True
            else:
                self.transport = None
                return False
                
        except Exception as e:
            logger.error(f"USB连接失败: {e}")
            return False
    
    def connect_serial(self, port: Optional[str] = None, baudrate: int = 115200) -> bool:
        """通过串口连接"""
        try:
            config = SerialConfig(port=port or "/dev/ttyUSB0", baudrate=baudrate)
            self.transport = SerialTransport(config)
            
            if self.transport.connect(port):
                self.connection_type = 'serial'
                logger.info("串口连接成功")
                return True
            else:
                self.transport = None
                return False
                
        except Exception as e:
            logger.error(f"串口连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.transport:
            self.transport.disconnect()
            self.transport = None
        
        self.connected_devices.clear()
        self.connection_type = None
        logger.info("已断开连接")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.transport is not None and self.transport.is_connected
    
    def scan_devices(self) -> List[DeviceInfo]:
        """扫描所有设备"""
        if not self.is_connected():
            logger.warning("未连接设备")
            return []
        
        self.connected_devices.clear()
        
        # 扫描各设备类型
        device_types = [
            (DeviceType.FLIGHT_CONTROLLER, "飞控"),
            (DeviceType.CAMERA, "相机"),
            (DeviceType.GIMBAL, "云台"),
            (DeviceType.PERCEPTION, "感知模块"),
            (DeviceType.BATTERY, "电池"),
            (DeviceType.RC, "遥控器"),
            (DeviceType.GPS, "GPS模块"),
            (DeviceType.IMU, "IMU"),
        ]
        
        for dev_type, dev_name in device_types:
            for dev_num in range(3):  # 尝试多个编号
                try:
                    info = self.transport.query_device_info(dev_type, dev_num)
                    
                    if info and info.get('model_code'):
                        device = DeviceInfo(
                            device_type=dev_type,
                            device_type_name=dev_name,
                            device_num=dev_num,
                            model_code=info.get('model_code', 'unknown'),
                            model_name=get_device_name(info.get('model_code', '')),
                            firmware_version=info.get('firmware_version', 'unknown'),
                            serial_number=info.get('serial_number', 'unknown'),
                        )
                        
                        # 查询设备状态
                        status = self.transport.query_device_status(dev_type, dev_num)
                        if status:
                            device.status = status
                        
                        self.connected_devices.append(device)
                        logger.info(f"发现设备: {device.model_name} ({dev_name})")
                        
                except Exception as e:
                    logger.debug(f"查询 {dev_name}#{dev_num} 失败: {e}")
        
        return self.connected_devices
    
    def get_device(self, device_type: int, device_num: int = 0) -> Optional[DeviceInfo]:
        """获取指定设备"""
        for device in self.connected_devices:
            if device.device_type == device_type and device.device_num == device_num:
                return device
        return None
    
    def get_flight_controller(self) -> Optional[DeviceInfo]:
        """获取飞控设备"""
        return self.get_device(DeviceType.FLIGHT_CONTROLLER)
    
    def get_camera(self, camera_num: int = 0) -> Optional[DeviceInfo]:
        """获取相机设备"""
        return self.get_device(DeviceType.CAMERA, camera_num)
    
    def get_gimbal(self, gimbal_num: int = 0) -> Optional[DeviceInfo]:
        """获取云台设备"""
        return self.get_device(DeviceType.GIMBAL, gimbal_num)
    
    def get_perception(self) -> Optional[DeviceInfo]:
        """获取感知模块"""
        return self.get_device(DeviceType.PERCEPTION)
    
    def get_battery(self, battery_num: int = 0) -> Optional[DeviceInfo]:
        """获取电池"""
        return self.get_device(DeviceType.BATTERY, battery_num)
    
    def update_device_status(self, device_type: int, device_num: int = 0) -> Optional[Dict[str, Any]]:
        """更新设备状态"""
        if not self.is_connected():
            return None
        
        status = self.transport.query_device_status(device_type, device_num)
        
        if status:
            device = self.get_device(device_type, device_num)
            if device:
                device.status = status
        
        return status
    
    def update_all_status(self) -> Dict[int, Dict[str, Any]]:
        """更新所有设备状态"""
        statuses = {}
        
        for device in self.connected_devices:
            status = self.update_device_status(device.device_type, device.device_num)
            if status:
                statuses[device.device_type] = status
        
        return statuses
    
    def start_heartbeat(self, interval: float = 1.0):
        """启动心跳"""
        if self.transport:
            self.transport.start_heartbeat(interval)
    
    def stop_heartbeat(self):
        """停止心跳"""
        if self.transport:
            self.transport.stop_heartbeat()
    
    @staticmethod
    def list_available_devices() -> List[dict]:
        """列出所有可用的DJI设备"""
        devices = []
        
        # 列出USB设备
        usb_devices = list_dji_devices()
        for dev in usb_devices:
            dev['connection_type'] = 'usb'
            devices.append(dev)
        
        # 列出串口设备
        serial_ports = SerialTransport.find_dji_ports()
        for port in serial_ports:
            devices.append({
                'device': port,
                'connection_type': 'serial',
            })
        
        return devices
    
    def get_device_summary(self) -> str:
        """获取设备摘要"""
        if not self.connected_devices:
            return "未发现设备"
        
        lines = [f"已连接 {len(self.connected_devices)} 个设备:\n"]
        
        for i, device in enumerate(self.connected_devices, 1):
            lines.append(f"{i}. {device.model_name} ({device.device_type_name})")
            lines.append(f"   型号: {device.model_code}")
            lines.append(f"   固件: {device.firmware_version}")
            lines.append(f"   序列号: {device.serial_number}")
            
            if device.status:
                if 'error_code' in device.status:
                    lines.append(f"   错误代码: 0x{device.status['error_code']:04x}")
                if 'temperature' in device.status:
                    lines.append(f"   温度: {device.status['temperature']:.1f}°C")
                if 'battery_percent' in device.status:
                    lines.append(f"   电量: {device.status['battery_percent']}%")
            
            lines.append("")
        
        return '\n'.join(lines)
