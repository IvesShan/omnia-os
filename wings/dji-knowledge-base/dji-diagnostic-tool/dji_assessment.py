#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 二手无人机评估系统
基于设备状态、飞行数据、故障记录评估二手价值

作者: 无限 (Omnia)
日期: 2026-04-21
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AssessmentResult:
    """评估结果"""
    estimated_value: float  # 预估价值（元）
    original_price: float   # 原价（元）
    depreciation_rate: float  # 折旧率
    grade: str  # 等级: S/A/B/C/D
    confidence: int  # 置信度 0-100
    factors: List[Dict]  # 评估因子
    market_reference: Dict  # 市场参考价


class AssessmentEngine:
    """评估引擎"""
    
    # 设备原价参考（需要根据市场更新）
    ORIGINAL_PRICES = {
        'Mini 4 Pro': 4788,
        'Mini 3 Pro': 4788,
        'Mini 3': 3288,
        'Mini 2 SE': 1999,
        'Mini 2': 2899,
        'Mini SE': 1999,
        'Mavic Mini': 2699,
        'Air 3': 6988,
        'Air 2S': 6499,
        'Air 2': 4999,
        'Mavic 3 Pro': 13888,
        'Mavic 3': 12888,
        'Mavic 2 Pro': 9888,
        'Mavic 2 Zoom': 7888,
    }
    
    # 等级定义
    GRADES = {
        'S': {'min_score': 90, 'label': '准新机', 'price_factor': 0.85},
        'A': {'min_score': 75, 'label': '良好', 'price_factor': 0.70},
        'B': {'min_score': 60, 'label': '一般', 'price_factor': 0.55},
        'C': {'min_score': 45, 'label': '较差', 'price_factor': 0.40},
        'D': {'min_score': 0, 'label': '报废/零件', 'price_factor': 0.20},
    }
    
    def __init__(self):
        pass
    
    def evaluate(self, device_info, health_score: int) -> Dict:
        """
        评估设备价值
        
        参数:
            device_info: 设备信息对象
            health_score: 健康评分 0-100
        
        返回:
            评估结果字典
        """
        # 获取原价
        original_price = self._get_original_price(device_info.model)
        
        # 计算各因子得分
        factors = []
        total_score = 100
        
        # 1. 外观成色 (假设)
        appearance_score = 85  # 需要人工检查或图片识别
        factors.append({
            'name': '外观成色',
            'score': appearance_score,
            'weight': 0.15,
            'description': '机身划痕、云台护罩、螺旋桨状态'
        })
        
        # 2. 飞行时间
        flight_time_score = self._score_flight_time(device_info.flight_time)
        factors.append({
            'name': '飞行时间',
            'score': flight_time_score,
            'weight': 0.20,
            'description': f'累计飞行 {device_info.flight_time} 分钟'
        })
        total_score -= (100 - flight_time_score) * 0.20
        
        # 3. 电池健康
        battery_score = self._score_battery(device_info.battery_cycles)
        factors.append({
            'name': '电池健康',
            'score': battery_score,
            'weight': 0.20,
            'description': f'电池循环 {device_info.battery_cycles} 次'
        })
        total_score -= (100 - battery_score) * 0.20
        
        # 4. 功能状态
        function_score = health_score
        factors.append({
            'name': '功能状态',
            'score': function_score,
            'weight': 0.25,
            'description': '基于日志分析的健康评分'
        })
        total_score -= (100 - function_score) * 0.25
        
        # 5. 固件版本
        firmware_score = 90  # 假设最新
        factors.append({
            'name': '固件/软件',
            'score': firmware_score,
            'weight': 0.10,
            'description': f'当前固件: {device_info.firmware_version}'
        })
        
        # 6. 配件完整性
        accessory_score = 85  # 假设齐全
        factors.append({
            'name': '配件完整',
            'score': accessory_score,
            'weight': 0.10,
            'description': '遥控器、电池、充电器、包装盒'
        })
        
        # 计算最终得分
        final_score = sum(f['score'] * f['weight'] for f in factors)
        
        # 确定等级
        grade = self._determine_grade(final_score)
        
        # 计算预估价值
        estimated_value = original_price * self.GRADES[grade]['price_factor']
        
        # 折旧率
        depreciation_rate = 1 - (estimated_value / original_price)
        
        # 市场参考价
        market_reference = self._get_market_reference(device_info.model, grade)
        
        return {
            'estimated_value': round(estimated_value, 0),
            'original_price': original_price,
            'depreciation_rate': round(depreciation_rate * 100, 1),
            'grade': grade,
            'grade_label': self.GRADES[grade]['label'],
            'final_score': round(final_score, 1),
            'confidence': self._calculate_confidence(factors),
            'factors': factors,
            'market_reference': market_reference,
            'suggested_price_range': {
                'low': round(estimated_value * 0.9, 0),
                'high': round(estimated_value * 1.1, 0)
            }
        }
    
    def _get_original_price(self, model: str) -> float:
        """获取设备原价"""
        for key, price in self.ORIGINAL_PRICES.items():
            if key in model:
                return price
        return 3000  # 默认价格
    
    def _score_flight_time(self, flight_time: int) -> int:
        """
        根据飞行时间评分
        
        评分标准:
        - 0-100分钟: 100分 (准新机)
        - 100-500分钟: 90分
        - 500-1000分钟: 80分
        - 1000-2000分钟: 70分
        - 2000-5000分钟: 60分
        - 5000+分钟: 50分
        """
        if flight_time < 100:
            return 100
        elif flight_time < 500:
            return 90
        elif flight_time < 1000:
            return 80
        elif flight_time < 2000:
            return 70
        elif flight_time < 5000:
            return 60
        else:
            return 50
    
    def _score_battery(self, cycles: int) -> int:
        """
        根据电池循环次数评分
        
        评分标准:
        - 0-50次: 100分
        - 50-100次: 90分
        - 100-200次: 75分
        - 200-300次: 60分
        - 300+次: 40分
        """
        if cycles < 50:
            return 100
        elif cycles < 100:
            return 90
        elif cycles < 200:
            return 75
        elif cycles < 300:
            return 60
        else:
            return 40
    
    def _determine_grade(self, score: float) -> str:
        """根据分数确定等级"""
        for grade in ['S', 'A', 'B', 'C', 'D']:
            if score >= self.GRADES[grade]['min_score']:
                return grade
        return 'D'
    
    def _calculate_confidence(self, factors: List[Dict]) -> int:
        """计算置信度"""
        # 基于数据的完整性计算
        # 如果有实际测量数据，置信度高；如果是估计，置信度低
        confidence = 85  # 基础置信度
        
        # 如果有异常低的分数，降低置信度
        for factor in factors:
            if factor['score'] < 50:
                confidence -= 10
        
        return max(0, min(100, confidence))
    
    def _get_market_reference(self, model: str, grade: str) -> Dict:
        """获取市场参考价"""
        # 这里应该从二手市场API获取实际数据
        # 现在使用模拟数据
        
        original = self._get_original_price(model)
        
        # 模拟市场数据
        market_data = {
            'S': {'low': original * 0.80, 'high': original * 0.90, 'avg': original * 0.85},
            'A': {'low': original * 0.65, 'high': original * 0.75, 'avg': original * 0.70},
            'B': {'low': original * 0.50, 'high': original * 0.60, 'avg': original * 0.55},
            'C': {'low': original * 0.35, 'high': original * 0.45, 'avg': original * 0.40},
            'D': {'low': original * 0.15, 'high': original * 0.25, 'avg': original * 0.20},
        }
        
        data = market_data.get(grade, market_data['B'])
        
        return {
            'platform': '闲鱼/转转参考价',
            'low': round(data['low'], 0),
            'high': round(data['high'], 0),
            'average': round(data['avg'], 0)
        }
    
    def generate_report_text(self, assessment: Dict) -> str:
        """生成评估报告文本"""
        lines = []
        lines.append("=" * 60)
        lines.append("DJI 二手无人机评估报告")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"综合评分: {assessment['final_score']}/100")
        lines.append(f"设备等级: {assessment['grade']} ({assessment['grade_label']})")
        lines.append(f"预估价值: ¥{assessment['estimated_value']:,.0f}")
        lines.append(f"原价参考: ¥{assessment['original_price']:,.0f}")
        lines.append(f"折旧率: {assessment['depreciation_rate']}%")
        lines.append(f"置信度: {assessment['confidence']}%")
        lines.append("")
        lines.append("-" * 60)
        lines.append("评估因子:")
        lines.append("-" * 60)
        
        for factor in assessment['factors']:
            lines.append(f"  {factor['name']}: {factor['score']}分 (权重{factor['weight']*100:.0f}%)")
            lines.append(f"    {factor['description']}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("市场参考:")
        lines.append("-" * 60)
        
        market = assessment['market_reference']
        lines.append(f"  参考平台: {market['platform']}")
        lines.append(f"  价格区间: ¥{market['low']:,.0f} - ¥{market['high']:,.0f}")
        lines.append(f"  平均价格: ¥{market['average']:,.0f}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("建议售价:")
        lines.append("-" * 60)
        
        price_range = assessment['suggested_price_range']
        lines.append(f"  ¥{price_range['low']:,.0f} - ¥{price_range['high']:,.0f}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
