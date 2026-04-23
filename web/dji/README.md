# DJI 设备诊断工具

> Omnia OS - DJI 设备诊断与维修辅助系统

## 🎯 功能特性

### 设备管理
- ✅ 自动扫描USB/串口设备
- ✅ 识别DJI全系列设备（无人机、遥控器、眼镜）
- ✅ 实时监控设备状态（温度、电量、错误码）

### 诊断分析
- ✅ 一键诊断设备健康状态
- ✅ 智能故障分析
- ✅ 维修建议生成
- ✅ 诊断报告导出

### 知识库
- ✅ 设备型号数据库（Mini系列、Mavic系列、Air系列等）
- ✅ 错误码查询
- ✅ 故障解决方案

## 🚀 快速开始

### 方式1: 使用启动脚本
```bash
cd /home/shan/omnia-os/web/dji
chmod +x start.sh
./start.sh
```

### 方式2: 手动启动
```bash
# 1. 启动API服务
python3 api.py

# 2. 打开浏览器
# 访问 file:///home/shan/omnia-os/web/dji/index.html
```

## 📁 文件结构

```
web/dji/
├── index.html      # 主界面
├── dji.css         # 样式文件
├── dji.js          # 交互逻辑
├── api.py          # 后端API
├── start.sh        # 启动脚本
└── README.md       # 本文档
```

## 🔌 API 接口

### 获取设备列表
```
GET /api/dji/devices
```

### 获取设备信息
```
GET /api/dji/device/<device_id>
```

### 运行诊断
```
POST /api/dji/diagnose/<device_id>
```

### 查询错误码
```
GET /api/dji/error/<error_code>
```

### 健康检查
```
GET /api/dji/health
```

## 🎨 界面预览

```
┌─────────────────────────────────────────┐
│  DJI 设备诊断工具 v1.0                    │
├──────────┬──────────────────────────────┤
│ 设备列表  │  设备详情                     │
│ ├ Mini 3  │  ┌────────────────────┐     │
│ ├ RC-N1   │  │ 型号: Mini 3       │     │
│ └ Goggles │  │ 固件: v1.2.3       │     │
│           │  │ 序列号: XXXXX      │     │
│ [扫描]    │  └────────────────────┘     │
│           │                              │
│           │  诊断面板                    │
│           │  ├ 温度: 45°C               │
│           │  ├ 电量: 85%                │
│           │  └ 错误: 0                  │
│           │                              │
│           │  [刷新] [诊断] [导出]        │
└──────────┴──────────────────────────────┘
```

## 📊 支持的设备

### 无人机
- Mini SE (WM160)
- Mini 2 (WM161)
- Mini 2 SE (WM1615)
- Mini 3 (WM163)
- Mini 3 Pro (WM1605)
- Mini 4 Pro (WM170)
- Air 2S (WM231)
- Mavic Air 2 (WM232)
- Mavic 3 系列 (WM240/245/246)
- Phantom 4 系列

### 遥控器
- RC-N1 (RC221)
- RC Pro (RC430)
- RC Plus (RC600)

### 眼镜
- Goggles 2 (WA140)
- Goggles 3 (WA152)

## 🔧 技术栈

- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **后端**: Python 3 + Flask
- **通信**: RESTful API
- **风格**: Omnia HUD 设计语言

## 📝 开发计划

### v1.1 (计划中)
- [ ] USB设备自动发现
- [ ] 实时数据流（WebSocket）
- [ ] 固件版本检查
- [ ] 飞行日志分析

### v1.2 (计划中)
- [ ] 配件库存管理
- [ ] 维修工单系统
- [ ] 客户管理集成
- [ ] 数据可视化图表

### v2.0 (未来)
- [ ] 与喵修匠系统对接
- [ ] AI故障预测
- [ ] 远程诊断支持

## 🤝 集成

### 喵修匠系统
本工具设计为**喵修匠**维修平台的诊断模块，可独立使用，也可集成到更大的业务系统中。

### 懂机帝平台
长期目标：成为**懂机帝**无人机垂类平台的核心诊断工具。

## 📄 许可证

MIT License - Omnia OS

## 👥 作者

- **原点** - 项目负责人
- **无限** - AI开发助手

---

**Omnia OS** - 让AI成为你的数字伙伴 🤖✨
