# 🚁 DJI 无人机维修诊断与二手检测工具

基于 DJI Assistant 2 协议逆向分析的无人机诊断工具包。

## 功能

- 🔌 **USB 连接诊断** - 通过 USB 直接连接飞机读取数据
- 🔍 **故障自动检测** - 基于日志分析识别故障码
- 💰 **二手价值评估** - 根据设备状态评估二手价格
- 📊 **生成诊断报告** - 支持 JSON / HTML / TEXT 格式

## 支持的设备

- DJI Mini 系列 (Mini 2, Mini 2 SE, Mini 3, Mini 3 Pro, Mini 4 Pro)
- DJI Air 系列 (Air 2, Air 2S, Air 3)
- DJI Mavic 系列 (Mavic 2, Mavic 3)

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# Linux 用户需要安装 libusb
sudo apt-get install libusb-1.0-0-dev
```

## 使用

```bash
# 运行诊断工具
python main.py
```

### 基本流程

1. 通过 USB 连接 DJI 无人机
2. 确保设备已开机
3. 运行诊断工具
4. 等待自动生成报告

### API 使用

```python
from main import DJIDiagnosticTool

# 创建诊断工具
tool = DJIDiagnosticTool()

# 连接设备
if tool.connect_device():
    # 运行诊断
    result = tool.run_diagnosis()
    
    # 生成报告
    tool.generate_report(result)
    
    # 断开连接
    tool.disconnect()
```

## 故障数据库

包含常见故障码：
- 传感器故障 (IMU, 指南针)
- 电机/电调故障
- 电池故障
- GPS 故障
- 视觉系统故障
- 云台故障
- 图传故障

## 评估标准

二手评估基于以下因子：
- 外观成色 (15%)
- 飞行时间 (20%)
- 电池健康 (20%)
- 功能状态 (25%)
- 固件版本 (10%)
- 配件完整 (10%)

## 文件结构

```
dji-diagnostic-tool/
├── main.py              # 主程序入口
├── dji_communicator.py  # USB 通信模块
├── dji_fault_db.py      # 故障码数据库
├── dji_log_parser.py    # 日志解析器
├── dji_assessment.py    # 二手评估引擎
├── dji_report.py        # 报告生成器
├── requirements.txt     # 依赖
└── README.md           # 说明文档
```

## 注意事项

1. **权限问题** - Linux/Mac 用户可能需要 sudo 权限访问 USB
2. **驱动安装** - Windows 用户需要安装 DJI 驱动
3. **安全警告** - 不要随意发送未知命令

## 法律声明

本工具仅供维修诊断和二手评估使用，请勿用于非法目的。

使用本工具导致的任何问题，作者不承担责任。

## 技术支持

- **作者**: 无限 (Omnia)
- **项目**: 喵修匠维修平台
- **日期**: 2026-04-21
