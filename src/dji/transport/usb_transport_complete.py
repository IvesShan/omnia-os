"""
DJI USB 通信传输层（完整版）
基于 libusb 实现 USB Bulk 传输
"""

import usb.core
import usb.util
from typing import Optional, List
import logging
import threading
from dataclasses import dataclass

try:
    from protocols.v1_protocol import DJIPacket, V1Protocol
except ImportError:
    # 当直接运行时使用绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from protocols.v1_protocol import DJIPacket, V1Protocol

logger = logging.getLogger(__name__)


@dataclass
class USBConfig:
    """USB配置"""
    vendor_id: int = 0x2ca3
    product_id: int = 0x0020
    interface_v1: int = 5  # 主通信协议接口
    interface_dbus: int = 3  # 调试总线接口
    endpoint_out: int = 0x01  # 输出端点
    endpoint_in: int = 0x81  # 输入端点
    timeout: int = 2000  # 超时时间 (ms)


def list_dji_devices() -> List[str]:
    """列出所有连接的DJI设备"""
    try:
        devices = usb.core.find(find_all=True, idVendor=0x2ca3)
        result = []
        for dev in devices:
            try:
                serial = dev.serial_number
                result.append(f"DJI-{serial}")
            except Exception:
                result.append(f"DJI-Device-{dev.idProduct:04x}")
        return result
    except Exception:
        return []


class USBTransport:
    """USB传输层"""
    
    def __init__(self, config: Optional[USBConfig] = None):
        self.config = config or USBConfig()
        self.device: Optional[usb.core.Device] = None
        self.protocol = V1Protocol()
        self.is_connected = False
        self._lock = threading.Lock()
        self._kernel_driver_detached = False
        
    def find_device(self) -> Optional[usb.core.Device]:
        """查找DJI设备"""
        try:
            devices = usb.core.find(
                find_all=True,
                idVendor=self.config.vendor_id,
                idProduct=self.config.product_id
            )
            
            device_list = list(devices)
            if device_list:
                logger.info(f"找到 {len(device_list)} 个DJI设备")
                return device_list[0]
            
            logger.warning("未找到DJI设备")
            return None
        except Exception as e:
            logger.error(f"查找设备失败: {e}")
            return None
    
    def connect(self) -> bool:
        """连接设备"""
        try:
            # 查找设备
            self.device = self.find_device()
            if not self.device:
                return False
            
            # 获取设备信息
            try:
                logger.info(f"设备: {self.device.manufacturer} {self.device.product}")
                logger.info(f"序列号: {self.device.serial_number}")
            except Exception:
                logger.info("设备信息不可用")
            
            # 尝试自动探测端点
            if not self._auto_detect_endpoints():
                logger.warning("自动探测端点失败，使用默认配置")
            
            # 配置接口
            if self._setup_interface():
                self.is_connected = True
                logger.info("USB连接成功")
                return True
            
            return False
            
        except usb.core.USBError as e:
            logger.error(f"USB连接失败: {e}")
            return False
    
    def _auto_detect_endpoints(self) -> bool:
        """自动探测端点"""
        try:
            cfg = self.device.get_active_configuration()
            
            for interface in cfg:
                logger.info(f"接口 {interface.bInterfaceNumber}: "
                           f"类={interface.bInterfaceClass}, "
                           f"子类={interface.bInterfaceSubClass}")
                
                # 查找 v1 协议接口
                if interface.bInterfaceNumber == self.config.interface_v1:
                    for endpoint in interface:
                        endpoint_address = endpoint.bEndpointAddress
                        if endpoint_address & 0x80:
                            self.config.endpoint_in = endpoint_address
                            logger.info(f"  输入端点: 0x{endpoint_address:02x}")
                        else:
                            self.config.endpoint_out = endpoint_address
                            logger.info(f"  输出端点: 0x{endpoint_address:02x}")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"探测端点失败: {e}")
            return False
    
    def _setup_interface(self) -> bool:
        """设置接口"""
        try:
            # 检查是否需要解除内核驱动
            if self.device.is_kernel_driver_active(self.config.interface_v1):
                try:
                    self.device.detach_kernel_driver(self.config.interface_v1)
                    self._kernel_driver_detached = True
                    logger.info("已解除内核驱动")
                except usb.core.USBError as e:
                    logger.warning(f"无法解除内核驱动: {e}")
                    # 可能需要 root 权限
                    return False
            
            # 设置配置
            self.device.set_configuration()
            
            # claim接口
            usb.util.claim_interface(self.device, self.config.interface_v1)
            
            logger.info("接口设置成功")
            return True
            
        except usb.core.USBError as e:
            logger.error(f"接口设置失败: {e}")
            logger.error("可能需要 root 权限: sudo python3 ...")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.device:
                # 释放接口
                usb.util.release_interface(self.device, self.config.interface_v1)
                
                # 重新附加内核驱动
                if self._kernel_driver_detached:
                    try:
                        self.device.attach_kernel_driver(self.config.interface_v1)
                    except Exception:
                        pass
                
                usb.util.dispose_resources(self.device)
            
            self.device = None
            self.is_connected = False
            logger.info("已断开连接")
            
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
    
    def send(self, packet: DJIPacket) -> bool:
        """发送数据包"""
        if not self.is_connected or not self.device:
            logger.error("设备未连接")
            return False
        
        try:
            with self._lock:
                data = packet.to_bytes()
                bytes_written = self.device.write(
                    self.config.endpoint_out,
                    data,
                    timeout=self.config.timeout
                )
                
                logger.debug(f"发送 {bytes_written} 字节: cmd=0x{packet.cmd_id:02x}")
                return bytes_written == len(data)
                
        except usb.core.USBError as e:
            logger.error(f"发送失败: {e}")
            return False
    
    def receive(self, timeout: Optional[int] = None) -> Optional[DJIPacket]:
        """接收数据包"""
        if not self.is_connected or not self.device:
            logger.error("设备未连接")
            return None
        
        try:
            with self._lock:
                # 读取数据
                data = self.device.read(
                    self.config.endpoint_in,
                    4096,  # 缓冲区大小
                    timeout=timeout or self.config.timeout
                )
                
                if data:
                    logger.debug(f"接收 {len(data)} 字节")
                    
                    # 解析数据包
                    packet = DJIPacket.from_bytes(bytes(data))
                    return packet
                
                return None
                
        except usb.core.USBError as e:
            if e.errno == 110:  # Timeout
                logger.debug("接收超时")
            else:
                logger.error(f"接收失败: {e}")
            return None
    
    def send_and_receive(self, packet: DJIPacket, timeout: Optional[int] = None) -> Optional[DJIPacket]:
        """发送并接收响应"""
        if self.send(packet):
            return self.receive(timeout)
        return None


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("测试 USB 传输层...")
    
    # 列出设备
    devices = list_dji_devices()
    print(f"\n发现的 DJI 设备: {devices}")
    
    # 尝试连接
    transport = USBTransport()
    if transport.connect():
        print("\n✅ 连接成功！")
        transport.disconnect()
    else:
        print("\n❌ 连接失败（可能需要 root 权限）")
