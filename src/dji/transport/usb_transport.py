"""
DJI USB 通信传输层
基于 libusb 实现 USB Bulk 传输
"""

import usb.core
import usb.util
from typing import Optional, List, Tuple
import logging
import threading
import time
from dataclasses import dataclass

from ..protocols.v1_protocol import DJIPacket, V1Protocol

logger = logging.getLogger(__name__)


@dataclass
class USBConfig:
    """USB配置"""
    vendor_id: int = 0x2ca3
    product_id: int = 0x0020
    interface_v1: int = 5  # 主通信协议接口
    interface_dbus: int = 3  # 调试总线接口
    endpoint_out: int = 0x01  # 输出端点 (需要实际探测)
    endpoint_in: int = 0x81  # 输入端点 (需要实际探测)
    timeout: int = 1000  # 超时时间 (ms)


class USBTransport:
    """USB传输层"""
    
    def __init__(self, config: Optional[USBConfig] = None):
        self.config = config or USBConfig()
        self.device: Optional[usb.core.Device] = None
        self.protocol = V1Protocol()
        self.is_connected = False
        self._lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        
    def find_device(self) -> Optional[usb.core.Device]:
        """查找DJI设备"""
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
    
    def connect(self) -> bool:
        """连接设备"""
        try:
            # 查找设备
            self.device = self.find_device()
            if not self.device:
                return False
            
            # 获取设备信息
            logger.info(f"设备: {self.device.manufacturer} {self.device.product}")
            logger.info(f"序列号: {self.device.serial_number}")
            
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
            for interface in self.device.get_active_configuration():
                if self.device.is_kernel_driver_active(interface.bInterfaceNumber):
                    try:
                        self.device.detach_kernel_driver(interface.bInterfaceNumber)
                        logger.info(f"已解除内核驱动: 接口 {interface.bInterfaceNumber}")
                    except usb.core.USBError as e:
                        logger.warning(f"无法解除内核驱动: {e}")
            
            # 设置配置
            self.device.set_configuration()
            
            return True
            
        except usb.core.USBError as e:
            logger.error(f"设置接口失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_heartbeat()
        self.is_connected = False
        
        if self.device:
            try:
                usb.util.dispose_resources(self.device)
            except Exception:
                pass
            self.device = None
        
        logger.info("USB已断开")
    
    def send_packet(self, packet: DJIPacket, timeout: Optional[int] = None) -> bool:
        """发送数据包"""
        if not self.is_connected or not self.device:
            logger.error("设备未连接")
            return False
        
        timeout = timeout or self.config.timeout
        
        try:
            with self._lock:
                data = packet.to_bytes()
                bytes_written = self.device.write(
                    self.config.endpoint_out,
                    data,
                    timeout=timeout
                )
                
                logger.debug(f"发送 {bytes_written} 字节: {data.hex()}")
                return bytes_written == len(data)
                
        except usb.core.USBError as e:
            logger.error(f"发送失败: {e}")
            return False
    
    def receive_packet(self, timeout: Optional[int] = None) -> Optional[DJIPacket]:
        """接收数据包"""
        if not self.is_connected or not self.device:
            logger.error("设备未连接")
            return None
        
        timeout = timeout or self.config.timeout
        
        try:
            with self._lock:
                data = self.device.read(
                    self.config.endpoint_in,
                    4096,  # 最大读取长度
                    timeout=timeout
                )
                
                if data:
                    logger.debug(f"接收 {len(data)} 字节: {bytes(data).hex()}")
                    return DJIPacket.from_bytes(bytes(data))
                
                return None
                
        except usb.core.USBError as e:
            if e.errno != 110:  # 超时不报错
                logger.error(f"接收失败: {e}")
            return None
    
    def send_and_receive(self, packet: DJIPacket, timeout: Optional[int] = None) -> Optional[dict]:
        """发送并接收响应"""
        if not self.send_packet(packet, timeout):
            return None
        
        # 等待响应
        start_time = time.time()
        timeout = (timeout or self.config.timeout) / 1000.0
        
        while time.time() - start_time < timeout:
            response = self.receive_packet(100)
            if response:
                parsed = self.protocol.parse_response(response.to_bytes())
                if parsed and parsed.get('seq_number') == packet.seq_number:
                    return parsed
        
        logger.warning("响应超时")
        return None
    
    def query_device_info(self, device_type: int = 0x0a, device_num: int = 0) -> Optional[dict]:
        """查询设备信息"""
        packet = self.protocol.build_query_device_info(device_type, device_num)
        return self.send_and_receive(packet)
    
    def query_device_status(self, device_type: int = 0x0a, device_num: int = 0) -> Optional[dict]:
        """查询设备状态"""
        packet = self.protocol.build_query_device_status(device_type, device_num)
        return self.send_and_receive(packet)
    
    def start_heartbeat(self, interval: float = 1.0):
        """启动心跳"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval,),
            daemon=True
        )
        self._heartbeat_thread.start()
        logger.info("心跳已启动")
    
    def stop_heartbeat(self):
        """停止心跳"""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
            self._heartbeat_thread = None
        logger.info("心跳已停止")
    
    def _heartbeat_loop(self, interval: float):
        """心跳循环"""
        while self._heartbeat_running and self.is_connected:
            try:
                packet = self.protocol.build_heartbeat()
                self.send_packet(packet)
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
            
            time.sleep(interval)
    
    def scan_devices(self) -> List[dict]:
        """扫描所有连接的DJI设备"""
        devices_info = []
        
        # 扫描各设备类型
        device_types = [
            (0x0a, "飞控"),
            (0x03, "相机"),
            (0x08, "云台"),
            (0x12, "感知模块"),
            (0x0b, "电池"),
            (0x07, "遥控器"),
        ]
        
        for dev_type, dev_name in device_types:
            try:
                info = self.query_device_info(dev_type, 0)
                if info and info.get('model_code'):
                    info['device_type'] = dev_type
                    info['device_name'] = dev_name
                    devices_info.append(info)
            except Exception as e:
                logger.debug(f"查询 {dev_name} 失败: {e}")
        
        return devices_info


def list_dji_devices() -> List[dict]:
    """列出所有DJI设备"""
    devices = usb.core.find(
        find_all=True,
        idVendor=0x2ca3
    )
    
    result = []
    for dev in devices:
        try:
            result.append({
                'vendor_id': hex(dev.idVendor),
                'product_id': hex(dev.idProduct),
                'manufacturer': dev.manufacturer,
                'product': dev.product,
                'serial_number': dev.serial_number,
            })
        except Exception:
            result.append({
                'vendor_id': hex(dev.idVendor),
                'product_id': hex(dev.idProduct),
            })
    
    return result
