"""
DJI 串口通信传输层
用于通过串口连接无人机
"""

import serial
import serial.tools.list_ports
from typing import Optional, List
import logging
import threading
import time
from dataclasses import dataclass

from ..protocols.v1_protocol import DJIPacket, V1Protocol

logger = logging.getLogger(__name__)


@dataclass
class SerialConfig:
    """串口配置"""
    port: str = "/dev/ttyUSB0"  # Linux
    # port: str = "COM3"  # Windows
    # port: str = "/dev/cu.usbmodem"  # macOS
    baudrate: int = 115200
    bytesize: int = serial.EIGHTBITS
    parity: str = serial.PARITY_NONE
    stopbits: int = serial.STOPBITS_ONE
    timeout: float = 1.0  # 读超时
    write_timeout: float = 1.0  # 写超时


class SerialTransport:
    """串口传输层"""
    
    def __init__(self, config: Optional[SerialConfig] = None):
        self.config = config or SerialConfig()
        self.serial: Optional[serial.Serial] = None
        self.protocol = V1Protocol()
        self.is_connected = False
        self._lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._receive_buffer = bytearray()
    
    @staticmethod
    def list_ports() -> List[dict]:
        """列出所有可用串口"""
        ports = serial.tools.list_ports.comports()
        result = []
        
        for port in ports:
            result.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'vid': hex(port.vid) if port.vid else None,
                'pid': hex(port.pid) if port.pid else None,
                'manufacturer': port.manufacturer or '',
                'product': port.product or '',
                'serial_number': port.serial_number or '',
            })
        
        return result
    
    @staticmethod
    def find_dji_ports() -> List[str]:
        """查找DJI设备的串口"""
        ports = SerialTransport.list_ports()
        dji_ports = []
        
        for port in ports:
            # DJI USB Vendor ID: 0x2ca3
            if port.get('vid') == '0x2ca3':
                dji_ports.append(port['device'])
            # 也检查描述中是否包含DJI
            elif 'dji' in port.get('description', '').lower():
                dji_ports.append(port['device'])
            elif 'dji' in (port.get('manufacturer') or '').lower():
                dji_ports.append(port['device'])
        
        return dji_ports
    
    def connect(self, port: Optional[str] = None) -> bool:
        """连接串口"""
        try:
            # 如果没有指定端口，尝试自动查找
            if port:
                self.config.port = port
            else:
                dji_ports = self.find_dji_ports()
                if dji_ports:
                    self.config.port = dji_ports[0]
                    logger.info(f"自动找到DJI设备: {self.config.port}")
                else:
                    logger.warning("未找到DJI设备，使用默认端口")
            
            # 打开串口
            self.serial = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout,
                write_timeout=self.config.write_timeout
            )
            
            # 清空缓冲区
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self._receive_buffer.clear()
            
            self.is_connected = True
            logger.info(f"串口连接成功: {self.config.port} @ {self.config.baudrate}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"串口连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_heartbeat()
        self.is_connected = False
        
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except:
                pass
            self.serial = None
        
        logger.info("串口已断开")
    
    def send_packet(self, packet: DJIPacket, timeout: Optional[float] = None) -> bool:
        """发送数据包"""
        if not self.is_connected or not self.serial:
            logger.error("设备未连接")
            return False
        
        try:
            with self._lock:
                data = packet.to_bytes()
                bytes_written = self.serial.write(data)
                
                logger.debug(f"发送 {bytes_written} 字节: {data.hex()}")
                return bytes_written == len(data)
                
        except serial.SerialException as e:
            logger.error(f"发送失败: {e}")
            return False
    
    def receive_packet(self, timeout: Optional[float] = None) -> Optional[DJIPacket]:
        """接收数据包"""
        if not self.is_connected or not self.serial:
            logger.error("设备未连接")
            return None
        
        timeout = timeout or self.config.timeout
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                # 读取可用数据
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    self._receive_buffer.extend(data)
                
                # 尝试解析数据包
                packet = self._parse_buffer()
                if packet:
                    return packet
                
                time.sleep(0.01)  # 短暂等待
            
            return None
            
        except serial.SerialException as e:
            logger.error(f"接收失败: {e}")
            return None
    
    def _parse_buffer(self) -> Optional[DJIPacket]:
        """从缓冲区解析数据包"""
        while len(self._receive_buffer) >= 14:  # 最小包长度
            # 查找包头
            if self._receive_buffer[0:2] != b'\x55\xAA':
                self._receive_buffer.pop(0)
                continue
            
            # 读取长度
            length = int.from_bytes(self._receive_buffer[2:4], 'little')
            total_length = 4 + length + 2  # 头部(2) + 长度字段(2) + 数据 + CRC(2)
            
            if len(self._receive_buffer) < total_length:
                return None  # 数据不完整，继续等待
            
            # 提取完整数据包
            packet_data = bytes(self._receive_buffer[:total_length])
            self._receive_buffer = self._receive_buffer[total_length:]
            
            # 解析数据包
            packet = DJIPacket.from_bytes(packet_data)
            if packet:
                logger.debug(f"接收数据包: {packet_data.hex()}")
                return packet
        
        return None
    
    def send_and_receive(self, packet: DJIPacket, timeout: Optional[float] = None) -> Optional[dict]:
        """发送并接收响应"""
        if not self.send_packet(packet, timeout):
            return None
        
        # 等待响应
        timeout = timeout or self.config.timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.receive_packet(0.1)
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
