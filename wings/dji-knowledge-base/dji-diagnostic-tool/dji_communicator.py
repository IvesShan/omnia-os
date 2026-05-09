#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 设备通信与故障日志分析工具
基于 DJI Assistant 2 协议逆向分析

作者: 无限 (Omnia)
日期: 2026-04-19
"""

import usb.core
import usb.util
import serial
import struct
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class DJICommunicator:
    """DJI 设备通信类"""
    
    # USB 设备信息
    VENDOR_ID = 0x2ca3
    PRODUCT_ID = 0x0020
    INTERFACE_V1 = 5      # 主通信协议接口
    INTERFACE_DBUS = 3    # 调试总线接口
    
    # 设备类型编码
    DEVICE_TYPES = {
        0x12: "Perception (感知模块)",
        0x0a: "Flight Controller (飞控)",
        0x03: "Camera (相机)",
        0x08: "Gimbal (云台)",
        0x10: "PC (电脑)"
    }
    
    # 命令ID
    CMD_QUERY_DEVICE_INFO = 0x88
    CMD_QUERY_COMM_INFO = 0x88
    CMD_ENTER_UPGRADE = 0x07
    CMD_QUERY_STATUS = 0x0C
    CMD_HEARTBEAT = 0xEA
    
    def __init__(self):
        self.device: Optional[usb.core.Device] = None
        self.ep_out = None
        self.ep_in = None
        self.connected = False
        
    def connect_usb(self) -> bool:
        """通过 USB 连接设备"""
        try:
            # 查找设备
            self.device = usb.core.find(
                idVendor=self.VENDOR_ID,
                idProduct=self.PRODUCT_ID
            )
            
            if self.device is None:
                print("❌ 设备未找到")
                return False
            
            print(f"✅ 找到设备: {self.device}")
            
            # 配置设备
            cfg = self.device.get_active_configuration()
            intf = cfg[(self.INTERFACE_V1, 0)]
            
            # 查找批量传输端点
            self.ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            self.ep_in = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            if self.ep_out is None or self.ep_in is None:
                print("❌ 无法找到通信端点")
                return False
            
            print(f"✅ 连接成功")
            print(f"   OUT 端点: {hex(self.ep_out.bEndpointAddress)}")
            print(f"   IN 端点: {hex(self.ep_in.bEndpointAddress)}")
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def connect_serial(self, port: str = "/dev/cu.usbmodem", baudrate: int = 115200) -> bool:
        """通过串口连接设备"""
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1
            )
            print(f"✅ 串口连接成功: {port}")
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ 串口连接失败: {e}")
            return False
    
    def send_command(self, cmd_id: int, target_type: int, target_num: int, 
                     data: bytes = b'') -> Optional[bytes]:
        """
        发送命令到设备
        
        参数:
            cmd_id: 命令ID
            target_type: 目标设备类型
            target_num: 目标设备编号
            data: 附加数据
        
        返回:
            响应数据
        """
        if not self.connected:
            print("❌ 设备未连接")
            return None
        
        try:
            # 构建命令包
            packet = struct.pack(
                '<BBBBH',
                0x0a,        # 源设备类型 (PC)
                0x07,        # 源设备编号
                target_type, # 目标设备类型
                target_num,  # 目标设备编号
                cmd_id       # 命令ID
            )
            
            if data:
                packet += struct.pack('<H', len(data)) + data
            
            # 发送命令
            self.ep_out.write(packet)
            print(f"📤 发送命令: 0x{cmd_id:02X} -> {self.DEVICE_TYPES.get(target_type, 'Unknown')}")
            
            # 接收响应
            response = self.ep_in.read(4096, timeout=5000)
            print(f"📥 接收响应: {len(response)} 字节")
            
            return bytes(response)
            
        except usb.core.USBError as e:
            print(f"❌ USB 通信错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 发送命令失败: {e}")
            return None
    
    def query_device_info(self) -> Optional[Dict]:
        """查询设备信息"""
        response = self.send_command(
            self.CMD_QUERY_DEVICE_INFO,
            0x0a,  # 飞控
            0x00,
            b'QueryDeviceInfo'
        )
        
        if response:
            return {
                "raw_data": response.hex(),
                "length": len(response)
            }
        return None
    
    def query_flight_data(self) -> Optional[Dict]:
        """查询飞行数据"""
        response = self.send_command(
            self.CMD_QUERY_DEVICE_INFO,
            0x0a,  # 飞控
            0x00,
            b'QueryFlightData'
        )
        
        if response:
            # 解析飞行数据（需要根据实际协议完善）
            return {
                'flight_time': 0,  # 需要从响应解析
                'battery_cycles': 0,
                'total_distance': 0.0,
                'raw_data': response.hex(),
            }
        return None
    
    def get_log_list(self) -> Optional[List[str]]:
        """获取日志列表"""
        response = self.send_command(
            self.CMD_QUERY_DEVICE_INFO,
            0x0a,
            0x00,
            b'get_log_list'
        )
        
        if response:
            return ["/blackbox/state/", "/blackbox/vision/"]
        return None
    
    def export_flight_log(self, log_type: str = "state", save_path: str = "./logs") -> str:
        """
        导出飞行日志
        
        参数:
            log_type: 日志类型 (state, vision, gimbal, camera)
            save_path: 保存路径
        """
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        
        print(f"📥 开始导出日志: {log_type}")
        
        # 开始导出
        response = self.send_command(
            self.CMD_QUERY_DEVICE_INFO,
            0x0a,
            0x00,
            f'log_export_start(start)'.encode()
        )
        
        if not response:
            print("❌ 开始导出失败")
            return None
        
        # 下载数据
        log_data = b''
        chunk_count = 0
        
        try:
            while True:
                data = self.ep_in.read(4096, timeout=1000)
                if not data or len(data) == 0:
                    break
                log_data += bytes(data)
                chunk_count += 1
                print(f"   已接收 {chunk_count} 块, {len(log_data)} 字节", end='\r')
        except usb.core.USBError:
            pass
        
        # 结束导出
        self.send_command(
            self.CMD_QUERY_DEVICE_INFO,
            0x0a,
            0x00,
            f'log_export_start(finish)'.encode()
        )
        
        # 保存日志
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.bin"
        filepath = os.path.join(save_path, filename)
        
        with open(filepath, 'wb') as f:
            f.write(log_data)
        
        print(f"\n✅ 日志已保存: {filepath}")
        print(f"   文件大小: {len(log_data)} 字节")
        
        return filepath
    
    def disconnect(self):
        """断开连接"""
        if self.device:
            usb.util.dispose_resources(self.device)
            self.device = None
        self.connected = False
        print("🔌 已断开连接")
