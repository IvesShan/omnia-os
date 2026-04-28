#!/usr/bin/env python3
"""
DJI 诊断引擎 - 核心诊断逻辑
整合知识库，提供智能故障诊断
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DiagnosticEngine:
    """DJI 设备诊断引擎"""
    
    def __init__(self, knowledge_base_path: Optional[Path] = None):
        """
        初始化诊断引擎
        
        Args:
            knowledge_base_path: 知识库路径
        """
        self.knowledge_base_path = knowledge_base_path or Path(
            str(Path(__file__).parent.parent.parent / "knowledge_base" / "dji")
        )
        
        # 加载故障代码数据库
        self.fault_database = self._load_fault_database()
        
        # 设备类型映射
        self.device_types = {
            0x00: "未知设备",
            0x03: "相机",
            0x04: "遥控器",
            0x05: "电池",
            0x06: "GPS模块",
            0x07: "IMU模块",
            0x08: "云台",
            0x0a: "飞控",
            0x0b: "电调",
            0x0c: "图传模块",
            0x0d: "视觉模块",
            0x0e: "避障模块",
            0x0f: "指南针",
            0x12: "感知模块",
        }
        
        # 设备型号映射
        self.device_models = {
            "wm160": "DJI Mini SE",
            "wm161": "DJI Mini 2",
            "wm1615": "DJI Mini 2 SE",
            "wm163": "DJI Mini 3",
            "wm1605": "DJI Mini 3 Pro",
            "wm170": "DJI Mini 4 Pro",
            "wm231": "DJI Air 2S",
            "wm232": "DJI Mavic Air 2",
            "wm240": "DJI Mavic 3",
            "wm245": "DJI Mavic 3 Classic",
            "wm246": "DJI Mavic 3 Pro",
            "wm260": "DJI Mavic 2 Pro",
            "wm334": "DJI Phantom 4",
            "hg330": "DJI FPV",
            "hg910": "DJI Avata",
        }
    
    def _load_fault_database(self) -> Dict[str, Any]:
        """加载故障代码数据库"""
        return {
            "communication": {
                "sendTextMessage failed": {
                    "description": "发送文本消息失败",
                    "causes": ["USB连接中断", "驱动问题"],
                    "solutions": ["检查USB连接", "重新安装驱动"]
                },
                "Time Out Error": {
                    "description": "通信超时",
                    "causes": ["设备无响应", "协议错误"],
                    "solutions": ["重启设备", "检查波特率"]
                },
                "USB Connection Lost": {
                    "description": "USB连接丢失",
                    "causes": ["USB线缆损坏", "USB接口松动"],
                    "solutions": ["更换USB线", "重新插拔"]
                },
            },
            "battery": {
                "Battery Overheat": {
                    "description": "电池过热",
                    "causes": ["环境温度过高", "大电流放电"],
                    "solutions": ["停止使用并降温", "检查电池健康"]
                },
                "Low Voltage Warning": {
                    "description": "低电压警告",
                    "causes": ["电池电量不足", "电池老化"],
                    "solutions": ["立即充电", "更换电池"]
                },
            },
            "gimbal": {
                "Gimbal Motor Error": {
                    "description": "云台电机错误",
                    "causes": ["电机过载", "机械卡死"],
                    "solutions": ["检查云台平衡", "清理异物"]
                },
                "Gimbal Overload": {
                    "description": "云台过载",
                    "causes": ["负载过重", "电机故障"],
                    "solutions": ["减轻负载", "联系售后"]
                },
            },
            "gps": {
                "GPS Signal Weak": {
                    "description": "GPS信号弱",
                    "causes": ["室内环境", "金属遮挡"],
                    "solutions": ["移至室外", "远离金属物体"]
                },
                "Compass Error": {
                    "description": "指南针错误",
                    "causes": ["磁场干扰", "指南针校准"],
                    "solutions": ["远离干扰源", "重新校准"]
                },
            }
        }
    
    def diagnose_device(
        self, 
        device_info: Dict[str, Any], 
        status_data: Any = None,
        error_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        诊断设备
        
        Args:
            device_info: 设备信息
            status_data: 状态数据 (bytes 或 dict)
            error_codes: 错误代码列表
            
        Returns:
            诊断结果
        """
        diagnosis = {
            "device_info": self._parse_device_info(device_info),
            "status": "normal",
            "severity": "info",
            "issues": [],
            "faults": [],
            "errors": [],
            "recommendations": []
        }
        
        # 1. 解析状态数据
        if status_data is not None:
            status_info = self._parse_status_data(status_data)
            diagnosis["status"] = status_info["status"]
            diagnosis["issues"].extend(status_info["issues"])
        
        # 2. 分析错误代码
        if error_codes:
            for code in error_codes:
                fault = self._analyze_error_code(code)
                if fault:
                    diagnosis["faults"].append(fault)
                    diagnosis["errors"].append({
                        "code": code,
                        "message": fault.get("description", "未知错误")
                    })
        
        # 3. 设备特定检查
        device_type = device_info.get("device_type")
        if device_type:
            device_checks = self._check_device_specific(device_type, device_info, status_data)
            diagnosis["issues"].extend(device_checks["issues"])
            diagnosis["recommendations"].extend(device_checks["recommendations"])
        
        # 4. 确定严重程度
        if diagnosis["faults"] or any(i.get("severity") == "critical" for i in diagnosis["issues"]):
            diagnosis["severity"] = "critical"
        elif diagnosis["issues"]:
            diagnosis["severity"] = "warning"
        
        # 5. 生成维修建议
        diagnosis["recommendations"].extend(
            self._generate_recommendations(diagnosis)
        )
        
        return diagnosis
    
    def _parse_device_info(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """解析设备信息"""
        device_type = device_info.get("device_type", 0x00)
        model_code = device_info.get("model", "unknown")
        
        return {
            "type": device_type,
            "type_name": self.device_types.get(device_type, "未知设备"),
            "model": model_code,
            "model_name": self.device_models.get(model_code, model_code),
            "serial": device_info.get("serial", "N/A"),
            "firmware": device_info.get("firmware", "N/A")
        }
    
    def _parse_status_data(self, status_data: Any) -> Dict[str, Any]:
        """
        解析状态数据
        支持 bytes 和 dict 两种格式
        """
        result = {
            "status": "normal",
            "issues": []
        }
        
        # 处理 bytes 格式
        if isinstance(status_data, bytes):
            if len(status_data) > 0:
                status_byte = status_data[0]
                
                has_error = (status_byte & 0x04) != 0
                has_warning = (status_byte & 0x02) != 0
                
                if has_error:
                    result["status"] = "error"
                    result["issues"].append({
                        "type": "status_error",
                        "description": "设备存在错误状态",
                        "severity": "critical",
                        "data": f"0x{status_byte:02x}"
                    })
                elif has_warning:
                    result["status"] = "warning"
                    result["issues"].append({
                        "type": "status_warning",
                        "description": "设备存在警告状态",
                        "severity": "warning",
                        "data": f"0x{status_byte:02x}"
                    })
        
        # 处理 dict 格式
        elif isinstance(status_data, dict):
            status_value = status_data.get("status", 0)
            
            # 状态值映射
            status_map = {
                0x00: "normal",
                0x01: "warning",
                0x02: "error"
            }
            result["status"] = status_map.get(status_value, "normal")
            
            # 检查温度
            temp = status_data.get("temperature")
            if temp is not None:
                if temp > 55:
                    result["status"] = "warning"
                    result["issues"].append({
                        "type": "overheat",
                        "description": f"温度过高: {temp}°C",
                        "severity": "warning",
                        "data": {"temperature": temp}
                    })
            
            # 检查电压
            voltage = status_data.get("voltage")
            if voltage is not None:
                if voltage < 11.0:
                    result["status"] = "warning"
                    result["issues"].append({
                        "type": "low_voltage",
                        "description": f"电压偏低: {voltage}V",
                        "severity": "warning",
                        "data": {"voltage": voltage}
                    })
        
        return result
    
    def _analyze_error_code(self, error_code: str) -> Optional[Dict[str, Any]]:
        """分析错误代码"""
        for category, codes in self.fault_database.items():
            if error_code in codes:
                fault_info = codes[error_code]
                return {
                    "code": error_code,
                    "category": category,
                    "description": fault_info["description"],
                    "causes": fault_info["causes"],
                    "solutions": fault_info["solutions"]
                }
        return None
    
    def _check_device_specific(
        self, 
        device_type: int, 
        device_info: Dict[str, Any],
        status_data: Any
    ) -> Dict[str, Any]:
        """设备特定检查"""
        result = {
            "issues": [],
            "recommendations": []
        }
        
        # 电池检查
        if device_type == 0x05:
            if isinstance(status_data, dict):
                flight_time = status_data.get("flight_time", 0)
                if flight_time > 150:
                    result["recommendations"].append(
                        "建议进行电池深度充放电循环以校准电量显示"
                    )
        
        # 云台检查
        elif device_type == 0x08:
            result["recommendations"].append(
                "定期检查云台平衡和电机状态"
            )
        
        # GPS检查
        elif device_type == 0x06:
            result["recommendations"].append(
                "确保在开阔区域使用以获得最佳GPS信号"
            )
        
        return result
    
    def _generate_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """生成维修建议"""
        recommendations = []
        
        # 根据故障生成建议
        for fault in diagnosis.get("faults", []):
            solutions = fault.get("solutions", [])
            recommendations.extend(solutions)
        
        # 根据问题生成建议
        for issue in diagnosis.get("issues", []):
            if issue.get("type") == "overheat":
                recommendations.append("建议停止使用并等待设备降温")
            elif issue.get("type") == "low_voltage":
                recommendations.append("建议立即充电或更换电池")
        
        return list(set(recommendations))  # 去重
    
    def get_device_types(self) -> Dict[int, str]:
        """获取设备类型映射"""
        return self.device_types
    
    def get_device_models(self) -> Dict[str, str]:
        """获取设备型号映射"""
        return self.device_models
