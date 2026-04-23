# DJI 无人机知识库

## 📋 概述
- **来源**: DJI Assistant 2 (Consumer Drones Series) v2.1.39
- **架构**: Electron + Qt + Ogre3D
- **创建日期**: 2026-04-19
- **用途**: 故障诊断软件开发参考

---

## 🚁 支持的设备型号

### 消费级无人机 (WM系列)

| 型号代码 | 产品名称 | 电池阈值 |
|---------|---------|---------|
| wm160 | Mini SE | 15% |
| wm161 | Mini 2 | 15% |
| wm1615 | Mini 2 SE | 15% |
| wm163 | Mini 3 | 15% |
| wm1605 | Mini 3 Pro | 15% |
| wm170 | Mini 4 Pro | - |
| wm231 | Air 2S | 20% |
| wm232 | Mavic Air 2 | 20% |
| wm240 | Mavic 3 | - |
| wm245 | Mavic 3 Classic | - |
| wm246 | Mavic 3 Pro | - |
| wm260 | Mavic 2 Pro | - |
| wm2605 | Mavic 2 Zoom | - |
| wm261 | Mavic 2 Enterprise | - |
| wm265e | Mavic 2 Enterprise Advanced | - |
| wm265m | Mavic 2 Enterprise Dual | - |
| wm265t | Mavic 2 Enterprise Thermal | - |
| wm334 | Phantom 4 | - |
| wm336 | Phantom 4 Pro | - |
| wm630 | Phantom 4 RTK | - |
| wm169 | Spark | - |

### 遥控器 (RC系列)

| 型号代码 | 产品名称 |
|---------|---------|
| rc221 | RC-N1 |
| rc430 | RC Pro |
| rc600 | RC Plus |
| rc150 | RC Mini |
| rc160 | RC Motion 2 |
| rc170 | FPV Remote Controller 2 |

### 飞行眼镜/图传 (WA系列)

| 型号代码 | 产品名称 |
|---------|---------|
| wa020 | Goggles | 
| wa140 | Goggles 2 |
| wa141 | Goggles 2 (V2) |
| wa150 | Goggles Integra |
| wa151 | Goggles Integra 2 |
| wa152 | Goggles 3 |
| wa233 | FPV Goggles V2 |
| wa234 | FPV Goggles V2 (V2) |
| wa520 | Goggles RE |
| wa521 | Goggles RE V2 |
| wa530 | Goggles RE 2 |
| wa720 | DJI FPV Goggles |

### 其他设备

| 型号代码 | 产品名称 |
|---------|---------|
| hg330 | DJI FPV |
| hg330_ds | DJI FPV (Dual System) |
| hg330_vtx | FPV VTX |
| hg910 | Avata |
| ag410_bs | Agras T40 Battery Station |
| gd610 | DJI Action 2 |

---

## 🔌 USB 通信协议

### 设备信息
```json
{
  "vendor_id": "0x2ca3",
  "product_id": "0x0020",
  "interfaces": {
    "interface_3": "dbus (调试总线)",
    "interface_5": "v1 (主通信协议)"
  }
}
```

### 设备类型编码

| 编码 | 设备类型 |
|-----|---------|
| 0x12 | 感知模块 (Perception) |
| 0x0a | 飞控 (Flight Controller) |
| 0x03 | 相机 (Camera) |
| 0x08 | 云台 (Gimbal) |
| 0x10 | PC (电脑端) |

### 命令ID

| 命令ID | 功能 | 说明 |
|-------|------|------|
| 0x88 | QueryDeviceInfo | 查询设备信息 |
| 0x88 | QueryCommunicationInfo | 查询通信信息 |
| 0x41 | Command ID | 通用命令 |
| 0x07 | Enter Upgrade | 进入升级模式 |
| 0x0C | Query Device Status | 查询设备状态 |
| 0xEA | Heartbeat | 心跳包 |
| 0x0b | RebootDevice | 重启设备 |
| 0x87 | Return | 返回响应 |

### 命令格式
```
发送命令格式:
[设备类型] [设备编号] [命令ID] [数据]

示例:
send 0_0x88 QueryDeviceInfo from {source_type} 0{source_num} to {target_type} 0{target_num} command: {cmd_id}

返回格式:
return 0_0x87 from {source_type} 0{source_num} to {target_type} 0{target_num}, ret_code: {code}, seq_number: {seq}
```

---

## 📊 黑盒日志系统

### 日志路径结构
```
/blackbox/                    # 黑盒子根目录
├── vision/                   # 视觉系统日志
├── state/                    # 状态日志
├── mov/                      # 运动日志
├── dji_perception/           # 感知系统日志
├── navigation/               # 导航日志
├── gimbal/                   # 云台日志
├── camera/                   # 相机日志
└── logger/                   # 记录器日志
    ├── gimbalA/              # 云台A
    ├── gimbalB/              # 云台B
    ├── camera/               # 相机
    ├── cboard/               # 核心板
    ├── cb_m4/                # M4芯片
    ├── service_1860/         # 1860服务
    ├── skyportA/             # SkyPort A
    └── skyportB/             # SkyPort B
```

### 控制器路径
```
/controller/
├── appreciation
├── config/user
├── module_activate
├── p4_ext
├── payload_sdk
├── payload_sdk_video
├── simulator
├── upgrade
├── vision_calibration
└── zenmuse_debug_data
```

---

## ⚠️ 故障诊断关键信息

### 模块组件列表

**电池模块**:
- Battery0, Battery1, Battery2, Battery3
- AG407 Battery, AG410 Battery
- Battery_AFE, Battery_GAUGE
- Backup Battery

**云台模块**:
- Gimbal303, Gimbal5223
- Gimbal 0402-0407
- Gimbal_esc_1/2/3
- Gimbal FPV
- fc_gimbal

**相机模块**:
- Camera4K, Camera4K_Loader
- Camera LENS
- Camera System, Camera Focus, Camera SSD
- E2_Camera

**飞控模块**:
- GPS1
- IMU_FPGA
- Flight Controller (0x0a)

**感知模块**:
- Perception (0x12)
- Weight Sensor
- AirSense CPLD, AirSense MCU

### 常见错误类型

**通信错误**:
- `sendTextMessage failed`
- `Time Out Error`
- `Do Ping V3 Test Failed!`
- `connect failed`

**升级错误**:
- `Enter Upgrade failed`
- `0x07(Enter Upgrade) finished, begin 0x0C(Query Device Status)`
- `DoEnterUpgradeMode2 receive error code 0xFE`

**校准错误**:
- `calibration calculation error[stereoextract]!`
- `calibration calculation error[ptsextract]!`
- `Camera Reading Error`
- `match rect failed`
- `calculation failed`

**配置错误**:
- `SetFlyCtrlCountryCode return error`
- `GetFlyCtrlCountryCode error`
- `GetWifiCountryCode error`
- `set WIFI CountryCode failed`

**设备错误**:
- `device not found`
- `open camera fail`
- `init failed, cam open retcode`

---

## 🔧 视觉校准系统

### 校准模块
- DJIVisionCalibration.dll (v1)
- DJIVisionCalibration2.dll (v2)
- DJIVisionCalibration3.dll (v3)

### 校准配置文件
```
calibration.ini
vision_userconfig.txt
/data/vision/cali/sensor_brt_cali.txt
/data/vision/cali_img/
```

### 校准错误代码
- `error_invalid_calibration_board`
- `set pattern error, screen too small!`
- `unknown error in init_pattern`
- `query state when cali_state is not init_done`

---

## 🌐 网络API接口

### 登录验证
```
https://account.dji.com/user/register.html?appId=DjiAssistant2
https://accounts.dji.com/user
https://active.dji.com/api/v2/assistant/switch
```

### 地理围栏
```
/api/v2/geocoder_service/geoip
/api/v3/geofence/onboard_static_data
/api/v3/geofence/query_update_for_onboard_static_data
```

---

## 📝 开发建议

### 故障诊断软件架构建议

1. **设备连接层**
   - 使用 libusb 实现 USB Bulk 传输
   - 支持 USB 和串口两种连接方式
   - 自动检测设备类型和型号

2. **协议解析层**
   - 实现 v1 协议解析
   - 支持命令发送和响应解析
   - 处理心跳和状态查询

3. **故障检测层**
   - 读取黑盒日志
   - 分析错误代码
   - 模块健康状态检测

4. **诊断报告层**
   - 生成诊断报告
   - 提供维修建议
   - 历史记录查询

### 关键功能实现

```python
# 1. 设备连接
def connect_device():
    # 使用 libusb 连接
    # vendor_id = 0x2ca3
    # product_id = 0x0020
    # interface = 5 (v1协议)
    pass

# 2. 查询设备信息
def query_device_info():
    # 发送命令 0x88
    # 解析返回的设备类型、型号、固件版本
    pass

# 3. 读取黑盒日志
def read_blackbox_logs():
    # 访问 /blackbox/ 目录
    # 解析各模块日志文件
    pass

# 4. 故障诊断
def diagnose_fault():
    # 分析错误代码
    # 检查模块状态
    # 生成诊断报告
    pass
```

---

## 📚 参考资料

- DJI Assistant 2 程序结构分析报告
- DJI 通信协议分析文档
- DJI 破解分析报告
- dji_communicator.py 通信工具

---

*知识库版本: 1.0*
*最后更新: 2026-04-19*
*维护者: Omnia AIOS*
