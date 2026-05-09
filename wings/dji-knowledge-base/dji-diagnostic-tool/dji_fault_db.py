#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 故障码数据库
包含常见故障码、症状、解决方案

作者: 无限 (Omnia)
日期: 2026-04-21
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FaultCode:
    """故障码定义"""
    code: str
    name: str
    description: str
    severity: str  # critical, high, medium, low
    affected_systems: List[str]
    symptoms: List[str]
    solutions: List[str]
    estimated_cost: str  # 维修预估成本
    repair_time: str  # 预估维修时间


class FaultDatabase:
    """故障数据库"""
    
    def __init__(self):
        self.faults = self._init_fault_database()
        
    def _init_fault_database(self) -> Dict[str, FaultCode]:
        """初始化故障数据库"""
        return {
            # === 传感器故障 ===
            "0x0001": FaultCode(
                code="0x0001",
                name="IMU 传感器故障",
                description="惯性测量单元(IMU)数据异常或校准失效",
                severity="critical",
                affected_systems=["飞控", "IMU"],
                symptoms=[
                    "飞行器姿态不稳",
                    "悬停漂移",
                    "起飞后倾斜",
                    "App提示IMU异常"
                ],
                solutions=[
                    "1. 在App中进行IMU校准",
                    "2. 检查IMU模块连接",
                    "3. 更换IMU模块（如校准无效）"
                ],
                estimated_cost="¥200-500",
                repair_time="30-60分钟"
            ),
            "0x0002": FaultCode(
                code="0x0002",
                name="指南针故障",
                description="指南针(磁力计)数据异常",
                severity="high",
                affected_systems=["飞控", "指南针"],
                symptoms=[
                    "App提示指南针异常",
                    "方向指示错误",
                    "起飞前校准失败"
                ],
                solutions=[
                    "1. 远离金属物体和磁场干扰",
                    "2. 进行指南针校准",
                    "3. 检查指南针模块连接",
                    "4. 更换指南针模块"
                ],
                estimated_cost="¥150-300",
                repair_time="20-40分钟"
            ),
            
            # === 电机/电调故障 ===
            "0x0101": FaultCode(
                code="0x0101",
                name="电机堵转",
                description="电机无法转动或转动阻力大",
                severity="critical",
                affected_systems=["动力", "电机"],
                symptoms=[
                    "电机不转",
                    "电机转动异响",
                    "飞行中某侧下沉",
                    "电机过热"
                ],
                solutions=[
                    "1. 检查电机轴承",
                    "2. 清理电机内部灰尘/异物",
                    "3. 检查电调连接",
                    "4. 更换电机"
                ],
                estimated_cost="¥100-300/个",
                repair_time="30-60分钟"
            ),
            "0x0102": FaultCode(
                code="0x0102",
                name="电调(ESC)故障",
                description="电子调速器工作异常",
                severity="high",
                affected_systems=["动力", "电调"],
                symptoms=[
                    "电机转速不一致",
                    "飞行中抖动",
                    "电调发热严重",
                    "电机缺相"
                ],
                solutions=[
                    "1. 检查电调连接线",
                    "2. 重新焊接电调",
                    "3. 更换电调"
                ],
                estimated_cost="¥150-400",
                repair_time="40-90分钟"
            ),
            
            # === 电池故障 ===
            "0x0201": FaultCode(
                code="0x0201",
                name="电池电芯异常",
                description="电池电芯电压不平衡或损坏",
                severity="high",
                affected_systems=["电池"],
                symptoms=[
                    "充电时间异常",
                    "续航时间缩短",
                    "电池鼓包",
                    "App提示电池异常"
                ],
                solutions=[
                    "1. 完全放电后重新充电",
                    "2. 检查电芯电压",
                    "3. 更换损坏电芯",
                    "4. 更换整块电池"
                ],
                estimated_cost="¥200-800",
                repair_time="30-120分钟"
            ),
            "0x0202": FaultCode(
                code="0x0202",
                name="电池温度异常",
                description="电池温度过高或传感器异常",
                severity="medium",
                affected_systems=["电池"],
                symptoms=[
                    "电池发热严重",
                    "App提示温度异常",
                    "充电自动停止"
                ],
                solutions=[
                    "1. 等待电池冷却",
                    "2. 检查电池温度传感器",
                    "3. 更换温度传感器",
                    "4. 更换电池"
                ],
                estimated_cost="¥100-500",
                repair_time="20-60分钟"
            ),
            
            # === GPS故障 ===
            "0x0301": FaultCode(
                code="0x0301",
                name="GPS信号弱",
                description="GPS模块无法定位或信号质量差",
                severity="medium",
                affected_systems=["导航", "GPS"],
                symptoms=[
                    "搜星数量少",
                    "定位漂移",
                    "无法进入GPS模式",
                    "返航功能异常"
                ],
                solutions=[
                    "1. 移至开阔地带",
                    "2. 检查GPS天线连接",
                    "3. 重新安装GPS模块",
                    "4. 更换GPS模块"
                ],
                estimated_cost="¥150-400",
                repair_time="30-60分钟"
            ),
            
            # === 视觉系统故障 ===
            "0x0401": FaultCode(
                code="0x0401",
                name="前视视觉传感器故障",
                description="前视避障摄像头工作异常",
                severity="medium",
                affected_systems=["视觉", "避障"],
                symptoms=[
                    "前视避障失效",
                    "视觉定位不稳定",
                    "App提示视觉异常"
                ],
                solutions=[
                    "1. 清洁摄像头镜头",
                    "2. 进行视觉标定",
                    "3. 检查摄像头连接",
                    "4. 更换视觉模块"
                ],
                estimated_cost="¥300-800",
                repair_time="40-90分钟"
            ),
            "0x0402": FaultCode(
                code="0x0402",
                name="下视视觉传感器故障",
                description="下视定位摄像头工作异常",
                severity="medium",
                affected_systems=["视觉", "定位"],
                symptoms=[
                    "室内定位漂移",
                    "降落不稳",
                    "视觉定位失效"
                ],
                solutions=[
                    "1. 清洁下视摄像头",
                    "2. 进行下视标定",
                    "3. 更换下视视觉模块"
                ],
                estimated_cost="¥200-600",
                repair_time="30-60分钟"
            ),
            
            # === 云台故障 ===
            "0x0501": FaultCode(
                code="0x0501",
                name="云台电机故障",
                description="云台电机过载或损坏",
                severity="high",
                affected_systems=["云台"],
                symptoms=[
                    "云台抖动",
                    "云台无法自检",
                    "云台偏向一侧",
                    "电机过热"
                ],
                solutions=[
                    "1. 检查云台是否有阻碍",
                    "2. 进行云台自动校准",
                    "3. 检查云台电机",
                    "4. 更换云台电机"
                ],
                estimated_cost="¥300-800",
                repair_time="40-90分钟"
            ),
            "0x0502": FaultCode(
                code="0x0502",
                name="云台标定失效",
                description="云台IMU标定数据异常",
                severity="medium",
                affected_systems=["云台"],
                symptoms=[
                    "画面倾斜",
                    "云台不水平",
                    "自检提示异常"
                ],
                solutions=[
                    "1. 进行云台标定",
                    "2. 检查云台IMU",
                    "3. 更换云台主板"
                ],
                estimated_cost="¥200-600",
                repair_time="30-60分钟"
            ),
            
            # === 图传故障 ===
            "0x0601": FaultCode(
                code="0x0601",
                name="图传信号弱",
                description="图传模块信号发射异常",
                severity="medium",
                affected_systems=["图传"],
                symptoms=[
                    "图传距离短",
                    "画面卡顿",
                    "信号丢失"
                ],
                solutions=[
                    "1. 检查天线连接",
                    "2. 检查天线是否损坏",
                    "3. 更换图传模块"
                ],
                estimated_cost="¥400-1200",
                repair_time="60-120分钟"
            ),
            
            # === 遥控器故障 ===
            "0x0701": FaultCode(
                code="0x0701",
                name="遥控器信号异常",
                description="遥控器与飞机通信异常",
                severity="high",
                affected_systems=["遥控", "通信"],
                symptoms=[
                    "连接不稳定",
                    "控制延迟",
                    "信号丢失"
                ],
                solutions=[
                    "1. 重新对频",
                    "2. 检查遥控器天线",
                    "3. 更换遥控器射频模块"
                ],
                estimated_cost="¥300-1000",
                repair_time="40-90分钟"
            ),
            
            # === 存储故障 ===
            "0x0801": FaultCode(
                code="0x0801",
                name="SD卡异常",
                description="SD卡读写错误或无法识别",
                severity="low",
                affected_systems=["存储"],
                symptoms=[
                    "无法录制",
                    "文件损坏",
                    "SD卡不识别"
                ],
                solutions=[
                    "1. 更换SD卡",
                    "2. 格式化SD卡",
                    "3. 检查SD卡槽"
                ],
                estimated_cost="¥50-200",
                repair_time="10-20分钟"
            ),
            
            # === 固件/软件故障 ===
            "0x0901": FaultCode(
                code="0x0901",
                name="固件异常",
                description="固件损坏或版本不匹配",
                severity="high",
                affected_systems=["系统"],
                symptoms=[
                    "无法开机",
                    "功能异常",
                    "频繁重启"
                ],
                solutions=[
                    "1. 尝试恢复出厂设置",
                    "2. 重新刷写固件",
                    "3. 更换主控板"
                ],
                estimated_cost="¥0-500",
                repair_time="30-120分钟"
            ),
        }
    
    def analyze(self, log_data: bytes) -> Tuple[List[Dict], List[Dict]]:
        """
        分析日志数据，返回故障和警告列表
        
        返回:
            (faults, warnings)
        """
        faults = []
        warnings = []
        
        # 在日志中搜索已知故障码
        for code, fault in self.faults.items():
            code_bytes = bytes.fromhex(code.replace("0x", ""))
            
            if code_bytes in log_data:
                fault_dict = {
                    "code": fault.code,
                    "name": fault.name,
                    "description": fault.description,
                    "severity": fault.severity,
                    "affected_systems": fault.affected_systems,
                    "symptoms": fault.symptoms,
                    "solutions": fault.solutions,
                    "estimated_cost": fault.estimated_cost,
                    "repair_time": fault.repair_time
                }
                
                if fault.severity in ["critical", "high"]:
                    faults.append(fault_dict)
                else:
                    warnings.append(fault_dict)
        
        return faults, warnings
    
    def get_fault(self, code: str) -> Optional[FaultCode]:
        """获取指定故障码信息"""
        return self.faults.get(code)
    
    def search_by_symptom(self, symptom: str) -> List[FaultCode]:
        """根据症状搜索故障"""
        results = []
        for fault in self.faults.values():
            if any(symptom in s for s in fault.symptoms):
                results.append(fault)
        return results
    
    def get_statistics(self) -> Dict:
        """获取故障统计信息"""
        stats = {
            "total": len(self.faults),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for fault in self.faults.values():
            if fault.severity in stats:
                stats[fault.severity] += 1
        
        return stats


# 全局故障数据库实例
fault_db = FaultDatabase()
