# DJI 通信协议详细规范

## 📡 协议概述

DJI Assistant 2 使用自定义的 **v1 协议** 进行设备通信，支持 USB 和串口两种连接方式。

---

## 🔌 连接方式

### 1. USB连接

```python
# USB设备信息
VENDOR_ID = 0x2ca3
PRODUCT_ID = 0x0020

# 接口定义
INTERFACE_V1 = 5      # 主通信协议接口
INTERFACE_DBUS = 3    # 调试总线接口

# 端点类型
ENDPOINT_OUT = 0x??   # 输出端点（发送命令）
ENDPOINT_IN = 0x??    # 输入端点（接收响应）
```

### 2. 串口连接

```python
# 串口配置
PORT = "/dev/cu.usbmodem"  # macOS
PORT = "/dev/ttyUSB0"      # Linux
PORT = "COM?"              # Windows

BAUDRATE = 115200  # 默认波特率
TIMEOUT = 1        # 超时时间（秒）
```

---

## 📦 数据包格式

### 发送数据包格式

```
+--------+--------+--------+--------+--------+--------+
| Header | Length | Type   | Cmd    | Data   | CRC    |
| 2 bytes| 2 bytes| 1 byte | 1 byte | N bytes| 2 bytes|
+--------+--------+--------+--------+--------+--------+

Header: 固定头部 (0x55 0xAA)
Length: 数据长度（不含头部和CRC）
Type: 设备类型
Cmd: 命令ID
Data: 数据内容
CRC: 校验码
```

### 命令格式示例

```
send 0_0x88 QueryDeviceInfo from {source_type} 0{source_num} to {target_type} 0{target_num} command: {cmd_id}
```

### 响应格式示例

```
return 0_0x87 from {source_type} 0{source_num} to {target_type} 0{target_num}, ret_code: {code}, seq_number: {seq}
```

---

## 🎯 命令ID列表

### 查询类命令

| 命令ID | 名称 | 功能 | 参数 |
|-------|------|------|------|
| 0x88 | QueryDeviceInfo | 查询设备信息 | 设备类型、编号 |
| 0x88 | QueryCommunicationInfo | 查询通信信息 | - |
| 0x0C | QueryDeviceStatus | 查询设备状态 | - |

### 控制类命令

| 命令ID | 名称 | 功能 | 参数 |
|-------|------|------|------|
| 0x07 | EnterUpgrade | 进入升级模式 | - |
| 0x0b | RebootDevice | 重启设备 | - |
| 0x41 | Command | 通用命令 | 子命令ID |
| 0xEA | Heartbeat | 心跳包 | - |

### 响应命令

| 命令ID | 名称 | 功能 |
|-------|------|------|
| 0x87 | Return | 返回响应 |
| 0x?? | Ack | 确认响应 |

---

## 🔄 通信流程

### 1. 设备连接流程

```
PC端                        设备端
  |                            |
  |------ QueryDeviceInfo ---->|
  |                            |
  |<----- Return (设备信息) ----|
  |                            |
  |------ Heartbeat ---------->|
  |                            |
  |<----- Heartbeat ACK -------|
  |                            |
  |   [连接建立成功]            |
```

### 2. 进入升级模式流程

```
PC端                        设备端
  |                            |
  |------ EnterUpgrade (0x07) ->|
  |                            |
  |<----- Return (确认) --------|
  |                            |
  |------ QueryStatus (0x0C) -->|
  |                            |
  |<----- Return (状态: loader)-|
  |                            |
  |   [进入升级模式成功]         |
```

### 3. 日志导出流程

```
PC端                        设备端
  |                            |
  |------ GetLogList --------->|
  |                            |
  |<----- Return (日志列表) ----|
  |                            |
  |------ LogExportStart ----->|
  |                            |
  |<----- LogData (数据流) -----|
  |                            |
  |------ LogExportStop ------>|
  |                            |
  |   [日志导出完成]            |
```

---

## 📝 命令详细说明

### QueryDeviceInfo (0x88)

**功能**: 查询设备基本信息

**请求格式**:
```
{
  "source_type": 0x10,    // PC端
  "source_num": 0x07,     // 编号7
  "target_type": 0x0a,    // 飞控
  "target_num": 0x00,     // 主设备
  "cmd_id": 0x88
}
```

**响应数据**:
```json
{
  "device_type": "0x0a",
  "device_num": "0x00",
  "product_type": "wm231",
  "firmware_version": "v01.00.0500",
  "serial_number": "xxxxxxxxxxxx",
  "hardware_version": "1.0"
}
```

### EnterUpgrade (0x07)

**功能**: 进入固件升级模式

**请求格式**:
```
{
  "source_type": 0x10,
  "source_num": 0x07,
  "target_type": 0x0a,
  "target_num": 0x00,
  "cmd_id": 0x07
}
```

**响应数据**:
```json
{
  "status": "success",
  "new_mode": "loader"
}
```

**错误代码**:
- `0xFE`: 进入升级模式失败

### QueryDeviceStatus (0x0C)

**功能**: 查询设备当前状态

**响应数据**:
```json
{
  "status": "normal|loader|error",
  "battery_level": 85,
  "temperature": 45,
  "modules": {
    "gimbal": "ok",
    "camera": "ok",
    "gps": "ok",
    "imu": "ok"
  }
}
```

### Heartbeat (0xEA)

**功能**: 保持连接活跃

**发送频率**: 每5秒

**请求格式**:
```json
{
  "timestamp": 1234567890
}
```

**响应格式**:
```json
{
  "status": "alive",
  "timestamp": 1234567891
}
```

---

## 🔧 路由配置

### 路由表结构

```json
{
  "self_dev_type": 10,    // PC端类型
  "self_dev_num": 7,      // PC端编号
  "route_table": [
    {
      "device_type": 18,   // 感知模块
      "device_num": 4,
      "if_name": "sv",
      "proto_name": "v1"
    },
    {
      "device_type": 18,
      "device_num": 0,
      "if_name": "sv",
      "proto_name": "v1"
    },
    {
      "device_type": 3,    // 相机
      "device_num": 0,
      "if_name": "sv",
      "proto_name": "v1"
    }
  ]
}
```

### 设备拓扑结构

```json
{
  "topology": [
    {
      "node1_dev_type": "0x12",  // 感知模块
      "node1_dev_num": "0x04",
      "node2_dev_type": "0x12",
      "node2_dev_num": "0x00",
      "weight": 1
    },
    {
      "node1_dev_type": "0x12",
      "node1_dev_num": "0x04",
      "node2_dev_type": "0x0a",  // 飞控
      "node2_dev_num": "0x07",
      "weight": 1
    }
  ]
}
```

---

## 💻 Python实现示例

### 基础通信类

```python
import usb.core
import usb.util
import struct
import json

class DJICommunicator:
    """DJI设备通信类"""
    
    VENDOR_ID = 0x2ca3
    PRODUCT_ID = 0x0020
    INTERFACE_V1 = 5
    
    def __init__(self):
        self.device = None
        self.ep_out = None
        self.ep_in = None
        
    def connect(self):
        """连接设备"""
        # 查找设备
        self.device = usb.core.find(
            idVendor=self.VENDOR_ID,
            idProduct=self.PRODUCT_ID
        )
        
        if self.device is None:
            raise Exception("设备未找到")
        
        # 配置接口
        cfg = self.device.get_active_configuration()
        intf = cfg[(self.INTERFACE_V1, 0)]
        
        # 获取端点
        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT
        )
        
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN
        )
        
        print("连接成功")
        
    def send_command(self, cmd_id, data=None):
        """发送命令"""
        packet = self._build_packet(cmd_id, data)
        self.ep_out.write(packet)
        return self._read_response()
    
    def _build_packet(self, cmd_id, data):
        """构建数据包"""
        header = bytes([0x55, 0xAA])
        length = struct.pack('<H', len(data) if data else 0)
        cmd = bytes([cmd_id])
        data = data if data else b''
        crc = self._calculate_crc(header + length + cmd + data)
        return header + length + cmd + data + crc
    
    def _read_response(self):
        """读取响应"""
        response = self.ep_in.read(1024, timeout=5000)
        return self._parse_response(response)
    
    def _parse_response(self, data):
        """解析响应"""
        # TODO: 实现响应解析
        return data
    
    def _calculate_crc(self, data):
        """计算CRC校验"""
        # TODO: 实现CRC计算
        return bytes([0x00, 0x00])
    
    def query_device_info(self):
        """查询设备信息"""
        return self.send_command(0x88)
    
    def query_device_status(self):
        """查询设备状态"""
        return self.send_command(0x0C)
    
    def enter_upgrade_mode(self):
        """进入升级模式"""
        return self.send_command(0x07)
    
    def send_heartbeat(self):
        """发送心跳"""
        return self.send_command(0xEA)
```

### 使用示例

```python
# 创建通信实例
comm = DJICommunicator()

# 连接设备
comm.connect()

# 查询设备信息
device_info = comm.query_device_info()
print(f"设备信息: {device_info}")

# 查询设备状态
status = comm.query_device_status()
print(f"设备状态: {status}")

# 发送心跳
comm.send_heartbeat()
```

---

## 📊 日志导出协议

### 日志类型

```
/blackbox/vision/          # 视觉系统日志
/blackbox/state/           # 状态日志
/blackbox/mov/             # 运动日志
/blackbox/dji_perception/  # 感知系统日志
/blackbox/navigation/      # 导航日志
/blackbox/gimbal/          # 云台日志
/blackbox/camera/          # 相机日志
/blackbox/logger/          # 记录器日志
```

### 日志导出命令

```python
def get_log_list(comm):
    """获取日志列表"""
    # 发送获取日志列表命令
    response = comm.send_command(0x??, {"action": "get_log_list"})
    return response

def export_log(comm, log_path):
    """导出指定日志"""
    # 开始导出
    comm.send_command(0x??, {"action": "log_export_start", "path": log_path})
    
    # 读取数据流
    log_data = b''
    while True:
        chunk = comm._read_response()
        if chunk is None:
            break
        log_data += chunk
    
    # 停止导出
    comm.send_command(0x??, {"action": "log_export_stop"})
    
    return log_data
```

---

## ⚠️ 注意事项

1. **权限问题**: Linux下需要配置udev规则或使用sudo
2. **驱动冲突**: Windows下可能需要禁用其他驱动
3. **超时设置**: 建议设置5-10秒超时
4. **重试机制**: 通信失败时建议重试3次
5. **并发限制**: 不支持多线程同时通信

---

*通信协议版本: v1.0*
*最后更新: 2026-04-19*
*维护者: Omnia AIOS*
