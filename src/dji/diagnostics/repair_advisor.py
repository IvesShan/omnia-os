#!/usr/bin/env python3
"""
维修顾问 - 生成智能维修建议
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class RepairAdvisor:
    """维修建议生成器"""
    
    def __init__(self):
        """初始化维修顾问"""
        # 维修难度等级
        self.difficulty_levels = {
            "easy": {
                "level": 1,
                "description": "用户可自行处理",
                "time_estimate": "5-30分钟",
                "tools_needed": ["基础工具"]
            },
            "medium": {
                "level": 2,
                "description": "需要一定技术能力",
                "time_estimate": "30分钟-2小时",
                "tools_needed": ["专业工具", "测试设备"]
            },
            "hard": {
                "level": 3,
                "description": "建议专业维修",
                "time_estimate": "2-4小时",
                "tools_needed": ["专业设备", "维修经验"]
            },
            "expert": {
                "level": 4,
                "description": "必须返厂维修",
                "time_estimate": "需评估",
                "tools_needed": ["原厂设备", "专业培训"]
            }
        }
        
        # 维修方案库
        self.repair_solutions = {
            # 通信故障维修
            "USB线缆损坏": {
                "difficulty": "easy",
                "steps": [
                    "1. 购买原装或认证USB线缆",
                    "2. 断开旧线缆",
                    "3. 连接新线缆",
                    "4. 测试连接"
                ],
                "cost_estimate": "50-200元",
                "success_rate": 0.95
            },
            "USB接口松动": {
                "difficulty": "medium",
                "steps": [
                    "1. 清洁USB接口",
                    "2. 检查接口焊点",
                    "3. 如需要，更换USB接口",
                    "4. 测试连接稳定性"
                ],
                "cost_estimate": "0-300元",
                "success_rate": 0.85
            },
            "驱动程序冲突": {
                "difficulty": "easy",
                "steps": [
                    "1. 打开设备管理器",
                    "2. 卸载当前驱动",
                    "3. 下载最新驱动",
                    "4. 安装并重启",
                    "5. 测试设备连接"
                ],
                "cost_estimate": "0元",
                "success_rate": 0.90
            },
            
            # 电池故障维修
            "电池ID芯片损坏": {
                "difficulty": "hard",
                "steps": [
                    "1. 购买原装电池",
                    "2. 更换电池",
                    "3. 测试电池识别"
                ],
                "cost_estimate": "300-800元",
                "success_rate": 0.95,
                "warning": "建议使用原装电池，第三方电池可能存在安全风险"
            },
            "电量计校准失效": {
                "difficulty": "easy",
                "steps": [
                    "1. 将电池充满至100%",
                    "2. 使用至自动关机",
                    "3. 再次充满",
                    "4. 重复2-3次循环"
                ],
                "cost_estimate": "0元",
                "success_rate": 0.70
            },
            "电芯不一致": {
                "difficulty": "hard",
                "steps": [
                    "1. 检测各电芯电压",
                    "2. 使用平衡充电器充电",
                    "3. 如电压差异过大，更换电池"
                ],
                "cost_estimate": "0-800元",
                "success_rate": 0.60,
                "warning": "电芯不一致可能导致飞行中掉电，建议更换"
            },
            
            # 云台故障维修
            "云台卡住": {
                "difficulty": "easy",
                "steps": [
                    "1. 检查云台是否有异物",
                    "2. 轻轻转动云台各轴",
                    "3. 检查云台限位",
                    "4. 清洁云台关节"
                ],
                "cost_estimate": "0元",
                "success_rate": 0.80
            },
            "配重不平衡": {
                "difficulty": "easy",
                "steps": [
                    "1. 取下相机",
                    "2. 检查云台平衡",
                    "3. 调整配重块位置",
                    "4. 重新安装相机",
                    "5. 测试云台响应"
                ],
                "cost_estimate": "0元",
                "success_rate": 0.85
            },
            "电机故障": {
                "difficulty": "hard",
                "steps": [
                    "1. 诊断具体故障电机",
                    "2. 购买对应型号电机",
                    "3. 拆卸云台外壳",
                    "4. 更换电机",
                    "5. 重新组装",
                    "6. 执行云台校准"
                ],
                "cost_estimate": "100-500元",
                "success_rate": 0.75,
                "warning": "需要一定维修经验，建议专业维修"
            },
            
            # 相机故障维修
            "传感器故障": {
                "difficulty": "expert",
                "steps": [
                    "1. 联系官方售后",
                    "2. 返厂检测",
                    "3. 根据检测结果维修或更换"
                ],
                "cost_estimate": "500-2000元",
                "success_rate": 0.90,
                "warning": "相机传感器属于精密部件，必须专业维修"
            },
            "相机排线松动": {
                "difficulty": "medium",
                "steps": [
                    "1. 拆卸相机外壳",
                    "2. 检查排线连接",
                    "3. 重新插拔排线",
                    "4. 固定排线",
                    "5. 重新组装",
                    "6. 测试相机功能"
                ],
                "cost_estimate": "0-100元",
                "success_rate": 0.85
            },
            "存储介质损坏": {
                "difficulty": "easy",
                "steps": [
                    "1. 尝试在电脑上格式化SD卡",
                    "2. 如无法格式化，更换SD卡",
                    "3. 建议使用高速卡(Class 10或更高)"
                ],
                "cost_estimate": "50-300元",
                "success_rate": 0.95
            },
            
            # 飞控故障维修
            "IMU校准失效": {
                "difficulty": "easy",
                "steps": [
                    "1. 在DJI GO/Assistant中执行IMU校准",
                    "2. 放置在水平面上",
                    "3. 等待校准完成",
                    "4. 重启设备",
                    "5. 验证校准结果"
                ],
                "cost_estimate": "0元",
                "success_rate": 0.85
            },
            "GPS天线故障": {
                "difficulty": "hard",
                "steps": [
                    "1. 检查GPS天线连接",
                    "2. 测试GPS信号强度",
                    "3. 如需要，更换GPS模块",
                    "4. 重新校准GPS"
                ],
                "cost_estimate": "200-600元",
                "success_rate": 0.80,
                "warning": "GPS模块更换需要专业设备"
            }
        }
    
    def generate_advice(
        self,
        diagnosis: Dict[str, Any],
        fault_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成维修建议
        
        Args:
            diagnosis: 诊断结果
            fault_analysis: 故障分析结果
            
        Returns:
            维修建议
        """
        advice = {
            "timestamp": datetime.now().isoformat(),
            "repair_options": [],
            "recommended_action": None,
            "estimated_cost": "待评估",
            "estimated_time": "待评估",
            "difficulty": "unknown"
        }
        
        # 收集所有可能的原因
        all_causes = []
        
        # 从诊断结果中提取
        for issue in diagnosis.get("issues", []):
            if "causes" in issue:
                all_causes.extend(issue["causes"])
        
        # 从故障分析中提取
        if fault_analysis:
            all_causes.extend(fault_analysis.get("likely_causes", []))
        
        # 去重
        all_causes = list(dict.fromkeys(all_causes))
        
        # 为每个原因查找维修方案
        for cause in all_causes:
            if cause in self.repair_solutions:
                solution = self.repair_solutions[cause]
                difficulty_info = self.difficulty_levels[solution["difficulty"]]
                
                advice["repair_options"].append({
                    "cause": cause,
                    "difficulty": difficulty_info,
                    "steps": solution["steps"],
                    "cost": solution["cost_estimate"],
                    "success_rate": solution["success_rate"],
                    "warning": solution.get("warning")
                })
        
        # 推荐最佳方案
        if advice["repair_options"]:
            # 按成功率和难度排序
            sorted_options = sorted(
                advice["repair_options"],
                key=lambda x: (
                    -x["success_rate"],
                    x["difficulty"]["level"]
                )
            )
            
            best_option = sorted_options[0]
            advice["recommended_action"] = best_option
            advice["estimated_cost"] = best_option["cost"]
            advice["estimated_time"] = best_option["difficulty"]["time_estimate"]
            advice["difficulty"] = best_option["difficulty"]["description"]
        
        return advice
    
    def get_maintenance_schedule(
        self,
        device_type: str,
        flight_hours: int = 0
    ) -> Dict[str, Any]:
        """
        获取维护计划
        
        Args:
            device_type: 设备类型
            flight_hours: 飞行小时数
            
        Returns:
            维护计划
        """
        schedule = {
            "daily": [
                "检查螺旋桨是否有裂纹或变形",
                "检查电池外观是否有鼓包",
                "检查相机镜头是否清洁",
                "检查云台活动是否顺畅"
            ],
            "weekly": [
                "清洁机身和相机",
                "检查固件更新",
                "检查存储卡空间",
                "检查遥控器电池"
            ],
            "monthly": [
                "执行IMU校准",
                "执行云台校准",
                "检查电机运转",
                "检查各连接线缆"
            ],
            "per_50_hours": [
                "更换螺旋桨",
                "检查电机轴承",
                "深度清洁设备",
                "检查电池健康度"
            ],
            "per_100_hours": [
                "全面检测设备",
                "更换磨损部件",
                "校准所有传感器",
                "建议送检"
            ]
        }
        
        # 根据飞行时间调整建议
        recommendations = []
        
        recommendations.extend(schedule["daily"])
        recommendations.extend(schedule["weekly"])
        recommendations.extend(schedule["monthly"])
        
        if flight_hours >= 50:
            recommendations.extend(schedule["per_50_hours"])
        
        if flight_hours >= 100:
            recommendations.extend(schedule["per_100_hours"])
        
        return {
            "device_type": device_type,
            "flight_hours": flight_hours,
            "recommendations": recommendations,
            "next_maintenance": self._calculate_next_maintenance(flight_hours)
        }
    
    def _calculate_next_maintenance(self, flight_hours: int) -> str:
        """计算下次维护时间"""
        if flight_hours >= 100:
            return "建议立即进行全面维护"
        elif flight_hours >= 50:
            return f"建议在{100 - flight_hours}飞行小时后进行全面维护"
        else:
            return f"建议在{50 - flight_hours}飞行小时后进行定期维护"
