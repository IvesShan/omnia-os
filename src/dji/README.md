# DJI 无人机通信模块

DJI消费级无人机通信和诊断模块，支持USB和串口连接。

## 功能特性

- ✅ USB Bulk 传输通信
- ✅ 串口通信
- ✅ DJI v1 协议实现
- ✅ 设备自动发现
- ✅ 设备信息查询
- ✅ 设备状态监控
- ✅ 心跳维护

## 支持的设备

### 无人机
- Mini系列: Mini SE/2/3/4 Pro
- Air系列: Air 2S, Mavic Air 2
- Mavic系列: Mavic 3/2系列
- Phantom系列: Phantom 4系列
- FPV系列: DJI FPV, Avata

### 遥控器
- RC-N1, RC Pro, RC Plus, RC Motion 2

### 飞行眼镜
- Goggles 2/3, FPV Goggles V2

## 安装

```bash
cd src/dji
pip install -r requirements.txt
```

## 快速开始

### 1. 扫描设备

```python
from dji import DJIDeviceManager, list_dji_devices

# 列出所有DJI USB设备
devices = list_dji_devices()
for dev in devices:
    print(f"{dev['product']} - {dev['serial_number']}")

# 列出串口
from dji import SerialTransport
ports = SerialTransport.find_dji_ports()
print(f"DJI串口: {ports}")
```

### 2. 连接设备

```python
from dji import DJIDeviceManager

manager = DJIDeviceManager()

# USB连接
if manager.connect_usb():
    print("USB连接成功")
    
    # 扫描设备
    devices = manager.scan_devices()
    print(manager.get_device_summary())
    
    # 断开连接
    manager.disconnect()

# 串口连接
if manager.connect_serial("/dev/ttyUSB0"):
    print("串口连接成功")
    manager.disconnect()
```

### 3. 查询设备信息

```python
from dji import DJIDeviceManager, DeviceType

manager = DJIDeviceManager()
if manager.connect_usb():
    # 获取飞控
    fc = manager.get_flight_controller()
    if fc:
        print(f"型号: {fc.model_name}")
        print(f"固件: {fc.firmware_version}")
        print(f"序列号: {fc.serial_number}")
    
    # 获取相机
    camera = manager.get_camera()
    if camera:
        print(f"相机: {camera.model_name}")
    
    manager.disconnect()
```

### 4. 监控设备状态

```python
from dji import DJIDeviceManager, DeviceType

manager = DJIDeviceManager()
if manager.connect_usb():
    # 启动心跳
    manager.start_heartbeat(interval=1.0)
    
    # 更新状态
    status = manager.update_device_status(DeviceType.FLIGHT_CONTROLLER)
    if status:
        print(f"温度: {status.get('temperature')}°C")
        print(f"电量: {status.get('battery_percent')}%")
        print(f"错误代码: {status.get('error_code')}")
    
    manager.stop_heartbeat()
    manager.disconnect()
```

## 协议说明

### 数据包格式

```
+--------+--------+--------+--------+--------+--------+
| Header | Length | Type   | Cmd    | Data   | CRC    |
| 2 bytes| 2 bytes| 1 byte | 1 byte | N bytes| 2 bytes|
+--------+--------+--------+--------+--------+--------+
```

### 命令ID

| 命令ID | 名称 | 功能 |
|-------|------|------|
| 0x88 | QueryDeviceInfo | 查询设备信息 |
| 0x0C | QueryDeviceStatus | 查询设备状态 |
| 0x07 | EnterUpgrade | 进入升级模式 |
| 0x0b | RebootDevice | 重启设备 |
| 0xEA | Heartbeat | 心跳包 |
| 0x87 | Return | 返回响应 |

### 设备类型

| 编码 | 设备类型 |
|-----|---------|
| 0x12 | 感知模块 |
| 0x0a | 飞控 |
| 0x03 | 相机 |
| 0x08 | 云台 |
| 0x0b | 电池 |
| 0x07 | 遥控器 |

## 测试

```bash
# 运行测试
python src/dji/tests/test_connection.py

# 或使用pytest
pytest src/dji/tests/
```

## 目录结构

```
src/dji/
├── __init__.py              # 模块入口
├── requirements.txt         # 依赖
├── README.md               # 文档
├── protocols/
│   └── v1_protocol.py      # DJI v1协议实现
├── transport/
│   ├── usb_transport.py    # USB传输层
│   └── serial_transport.py # 串口传输层
├── core/
│   └── device_manager.py   # 设备管理器
└── tests/
    └── test_connection.py  # 测试脚本
```

## 注意事项

1. **权限**: Linux下需要配置USB权限或使用sudo
   ```bash
   # 添加udev规则
   echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2ca3", MODE="0666"' | sudo tee /etc/udev/rules.d/99-dji.rules
   sudo udevadm control --reload-rules
   ```

2. **驱动**: 某些设备可能需要解除内核驱动占用

3. **安全**: 请勿在生产环境中使用，仅供学习和研究

## 参考资料

- DJI Assistant 2 (Consumer Drones Series) v2.1.39
- DJI USB Vendor ID: 0x2ca3
- 知识库: `/knowledge_base/dji/`

## 许可证

仅供学习和研究使用。
