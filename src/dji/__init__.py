"""
DJI 无人机通信模块
用于连接和诊断DJI消费级无人机
"""

from .protocols.v1_protocol import (
    DJIPacket,
    V1Protocol,
    DeviceType,
    CommandID,
    get_device_name,
    DEVICE_MODEL_MAP,
)

from .transport.usb_transport import (
    USBTransport,
    USBConfig,
    list_dji_devices,
)

from .transport.serial_transport import (
    SerialTransport,
    SerialConfig,
)

from .core.device_manager import (
    DJIDeviceManager,
    DeviceInfo,
)

__version__ = '1.0.0'
__author__ = 'Omnia AI'

__all__ = [
    # 协议
    'DJIPacket',
    'V1Protocol',
    'DeviceType',
    'CommandID',
    'get_device_name',
    'DEVICE_MODEL_MAP',
    
    # USB传输
    'USBTransport',
    'USBConfig',
    'list_dji_devices',
    
    # 串口传输
    'SerialTransport',
    'SerialConfig',
    
    # 设备管理
    'DJIDeviceManager',
    'DeviceInfo',
]
