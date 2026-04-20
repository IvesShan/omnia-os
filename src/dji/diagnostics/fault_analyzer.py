#!/usr/bin/env python3
"""
故障分析器 - 深度分析故障模式
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict


class FaultAnalyzer:
    """故障模式分析器"""
    
    def __init__(self):
        """初始化故障分析器"""
        # 故障模式库
        self.fault_patterns = {
            # 通信故障模式
            "communication_failure": {
                "symptoms": [
                    "sendTextMessage failed",
                    "Time Out Error",
                    "Do Ping V3 Test Failed!",
                    "connect failed"
                ],
                "root_causes": [
                    "USB线缆损坏",
                    "USB接口松动",
                    "驱动程序冲突",
                    "设备固件异常",
                    "USB控制器故障"
                ],
                "diagnostic_steps": [
                    "1. 更换USB线缆测试",
                    "2. 更换USB接口测试",
                    "3. 检查设备管理器中的驱动状态",
                    "4. 重启设备和电脑",
                    "5. 更新或重新安装驱动"
                ],
                "severity": "high"
            },
            
            # 电池故障模式
            "battery_failure": {
                "symptoms": [
                    "电池无法识别",
                    "电量显示异常",
                    "电池温度异常",
                    "充电失败",
                    "电池电压不均"
                ],
                "root_causes": [
                    "电池ID芯片损坏",
                    "电量计校准失效",
                    "温度传感器故障",
                    "充电电路故障",
                    "电芯不一致"
                ],
                "diagnostic_steps": [
                    "1. 读取电池序列号",
                    "2. 检查Battery_GAUGE数据",
                    "3. 读取温度数据",
                    "4. 检查充电电压电流",
                    "5. 读取电芯电压"
                ],
                "severity": "medium"
            },
            
            # 云台故障模式
            "gimbal_failure": {
                "symptoms": [
                    "云台过载",
                    "云台震动",
                    "云台不响应",
                    "云台漂移",
                    "云台异响"
                ],
                "root_causes": [
                    "云台卡住",
                    "配重不平衡",
                    "电机故障",
                    "IMU异常",
                    "连接断开",
                    "固件异常",
                    "电机轴承损坏"
                ],
                "diagnostic_steps": [
                    "1. 检查云台活动是否顺畅",
                    "2. 重新配平云台",
                    "3. 执行云台校准",
                    "4. 检查排线连接",
                    "5. 更新固件"
                ],
                "severity": "medium"
            },
            
            # 相机故障模式
            "camera_failure": {
                "symptoms": [
                    "Camera Reading Error",
                    "open camera fail",
                    "init failed, cam open retcode",
                    "相机无图像",
                    "对焦失败",
                    "存储错误"
                ],
                "root_causes": [
                    "传感器故障",
                    "连接问题",
                    "相机被占用",
                    "驱动错误",
                    "固件损坏",
                    "硬件故障",
                    "对焦模块损坏",
                    "存储介质损坏"
                ],
                "diagnostic_steps": [
                    "1. 检查相机排线连接",
                    "2. 重启设备",
                    "3. 更新驱动",
                    "4. 刷写固件",
                    "5. 检查SD卡状态"
                ],
                "severity": "high"
            },
            
            # 飞控故障模式
            "flight_controller_failure": {
                "symptoms": [
                    "IMU校准失败",
                    "GPS信号弱",
                    "指南针错误",
                    "限飞区锁定",
                    "SetFlyCtrlCountryCode error"
                ],
                "root_causes": [
                    "磁场干扰",
                    "传感器故障",
                    "环境遮挡",
                    "GPS天线故障",
                    "校准失效",
                    "位于禁飞区",
                    "固件限制"
                ],
                "diagnostic_steps": [
                    "1. 远离磁场干扰源",
                    "2. 执行IMU校准",
                    "3. 在开阔区域测试GPS",
                    "4. 检查GPS天线",
                    "5. 执行指南针校准"
                ],
                "severity": "critical"
            }
        }
        
        # 故障历史记录
        self.fault_history: List[Dict[str, Any]] = []
    
    def analyze(
        self,
        symptoms: List[str],
        device_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析故障症状
        
        Args:
            symptoms: 故障症状列表
            device_info: 设备信息
            
        Returns:
            分析结果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "symptoms": symptoms,
            "matched_patterns": [],
            "likely_causes": [],
            "diagnostic_plan": [],
            "severity": "unknown"
        }
        
        # 匹配故障模式
        for pattern_name, pattern in self.fault_patterns.items():
            matched_symptoms = []
            for symptom in symptoms:
                if symptom in pattern["symptoms"]:
                    matched_symptoms.append(symptom)
            
            if matched_symptoms:
                result["matched_patterns"].append({
                    "pattern": pattern_name,
                    "matched_symptoms": matched_symptoms,
                    "root_causes": pattern["root_causes"],
                    "diagnostic_steps": pattern["diagnostic_steps"],
                    "severity": pattern["severity"]
                })
        
        # 确定严重程度
        if result["matched_patterns"]:
            severities = [p["severity"] for p in result["matched_patterns"]]
            if "critical" in severities:
                result["severity"] = "critical"
            elif "high" in severities:
                result["severity"] = "high"
            elif "medium" in severities:
                result["severity"] = "medium"
            else:
                result["severity"] = "low"
        
        # 汇总可能原因
        causes_count = defaultdict(int)
        for pattern in result["matched_patterns"]:
            for cause in pattern["root_causes"]:
                causes_count[cause] += 1
        
        result["likely_causes"] = sorted(
            causes_count.keys(),
            key=lambda x: causes_count[x],
            reverse=True
        )
        
        # 生成诊断计划
        steps_set = set()
        for pattern in result["matched_patterns"]:
            for step in pattern["diagnostic_steps"]:
                steps_set.add(step)
        
        result["diagnostic_plan"] = sorted(list(steps_set))
        
        # 记录到历史
        self.fault_history.append(result)
        
        return result
    
    def get_fault_statistics(self) -> Dict[str, Any]:
        """获取故障统计"""
        if not self.fault_history:
            return {"total": 0}
        
        stats = {
            "total": len(self.fault_history),
            "by_severity": defaultdict(int),
            "by_pattern": defaultdict(int),
            "common_symptoms": defaultdict(int),
            "common_causes": defaultdict(int)
        }
        
        for record in self.fault_history:
            # 按严重程度统计
            stats["by_severity"][record["severity"]] += 1
            
            # 按模式统计
            for pattern in record["matched_patterns"]:
                stats["by_pattern"][pattern["pattern"]] += 1
            
            # 常见症状
            for symptom in record["symptoms"]:
                stats["common_symptoms"][symptom] += 1
            
            # 常见原因
            for cause in record["likely_causes"]:
                stats["common_causes"][cause] += 1
        
        return stats
    
    def suggest_preventive_actions(self) -> List[str]:
        """建议预防措施"""
        stats = self.get_fault_statistics()
        
        suggestions = []
        
        if stats["total"] == 0:
            return ["暂无历史故障数据，建议定期维护"]
        
        # 基于常见故障提供建议
        common_patterns = sorted(
            stats["by_pattern"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        for pattern_name, count in common_patterns:
            if pattern_name == "communication_failure":
                suggestions.append("定期检查USB线缆和接口")
                suggestions.append("保持驱动程序更新")
            elif pattern_name == "battery_failure":
                suggestions.append("定期进行电池深度充放电循环")
                suggestions.append("避免电池过度放电")
            elif pattern_name == "gimbal_failure":
                suggestions.append("定期检查云台配平")
                suggestions.append("避免云台受到撞击")
            elif pattern_name == "camera_failure":
                suggestions.append("定期检查相机排线连接")
                suggestions.append("保持存储介质健康")
            elif pattern_name == "flight_controller_failure":
                suggestions.append("定期校准IMU和指南针")
                suggestions.append("避免在强磁场环境飞行")
        
        return list(dict.fromkeys(suggestions))  # 去重
