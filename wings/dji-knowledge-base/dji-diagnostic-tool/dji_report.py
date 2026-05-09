#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI 诊断报告生成器
支持 JSON / HTML / TEXT 格式

作者: 无限 (Omnia)
日期: 2026-04-21
"""

import json
import os
from typing import Dict, Any
from datetime import datetime


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    def generate_json(self, result, output_dir: str = "./reports") -> str:
        """生成 JSON 格式报告"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 将结果转换为字典
        report_data = {
            'timestamp': result.timestamp,
            'device_info': {
                'model': result.device_info.model,
                'serial_number': result.device_info.serial_number,
                'firmware_version': result.device_info.firmware_version,
                'flight_time': result.device_info.flight_time,
                'battery_cycles': result.device_info.battery_cycles,
                'total_distance': result.device_info.total_distance,
            },
            'health_score': result.health_score,
            'faults': result.faults,
            'warnings': result.warnings,
            'assessment': result.assessment,
            'recommendations': result.recommendations
        }
        
        filename = f"dji_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def generate_html(self, result, output_dir: str = "./reports") -> str:
        """生成 HTML 格式报告"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        html_content = self._build_html(result)
        
        filename = f"dji_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def generate_text(self, result, output_dir: str = "./reports") -> str:
        """生成文本格式报告"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        text_content = self._build_text(result)
        
        filename = f"dji_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return filepath
    
    def _build_html(self, result) -> str:
        """构建 HTML 报告"""
        # 健康评分颜色
        score_color = self._get_score_color(result.health_score)
        
        # 生成故障列表 HTML
        faults_html = ""
        for fault in result.faults:
            severity_color = self._get_severity_color(fault['severity'])
            faults_html += f"""
            <div class="fault-item {fault['severity']}">
                <h4>[{fault['code']}] {fault['name']}</h4>
                <p><strong>严重等级:</strong> <span class="severity {fault['severity']}">{fault['severity']}</span></p>
                <p><strong>描述:</strong> {fault['description']}</p>
                <p><strong>影响系统:</strong> {', '.join(fault['affected_systems'])}</p>
                <p><strong>症状:</strong></p>
                <ul>{''.join(f'<li>{s}</li>' for s in fault['symptoms'])}</ul>
                <p><strong>解决方案:</strong></p>
                <ol>{''.join(f'<li>{s}</li>' for s in fault['solutions'])}</ol>
                <p><strong>预估成本:</strong> {fault['estimated_cost']} | <strong>维修时间:</strong> {fault['repair_time']}</p>
            </div>
            """
        
        if not faults_html:
            faults_html = '<div class="no-faults">✅ 未发现故障</div>'
        
        # 生成警告列表 HTML
        warnings_html = ""
        for warning in result.warnings:
            warnings_html += f"""
            <div class="warning-item">
                <h4>[{warning['code']}] {warning['name']}</h4>
                <p>{warning['description']}</p>
            </div>
            """
        
        if not warnings_html:
            warnings_html = '<div class="no-warnings">✅ 未发现警告</div>'
        
        # 生成建议列表 HTML
        recommendations_html = ""
        for i, rec in enumerate(result.recommendations, 1):
            recommendations_html += f'<li>{rec}</li>'
        
        # 评估信息 HTML
        assessment = result.assessment
        assessment_html = f"""
        <div class="assessment-summary">
            <h3>二手评估</h3>
            <table>
                <tr><td>设备等级</td><td><strong>{assessment.get('grade', 'N/A')} ({assessment.get('grade_label', 'N/A')})</strong></td></tr>
                <tr><td>预估价值</td><td><strong class="price">¥{assessment.get('estimated_value', 0):,.0f}</strong></td></tr>
                <tr><td>原价参考</td><td>¥{assessment.get('original_price', 0):,.0f}</td></tr>
                <tr><td>折旧率</td><td>{assessment.get('depreciation_rate', 0)}%</td></tr>
                <tr><td>建议售价</td><td>¥{assessment.get('suggested_price_range', {}).get('low', 0):,.0f} - ¥{assessment.get('suggested_price_range', {}).get('high', 0):,.0f}</td></tr>
            </table>
        </div>
        """
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DJI 无人机诊断报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .info-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }}
        .info-item label {{
            display: block;
            color: #666;
            font-size: 12px;
            margin-bottom: 5px;
        }}
        .info-item value {{
            display: block;
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .health-score {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            margin: 20px 0;
        }}
        .score-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: conic-gradient({score_color} calc({result.health_score} * 3.6deg), #e0e0e0 0);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 15px;
            position: relative;
        }}
        .score-circle::before {{
            content: '';
            width: 90px;
            height: 90px;
            background: white;
            border-radius: 50%;
            position: absolute;
        }}
        .score-value {{
            font-size: 36px;
            font-weight: bold;
            color: {score_color};
            position: relative;
            z-index: 1;
        }}
        .fault-item {{
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin-bottom: 15px;
            background: #fdf2f2;
            border-radius: 0 8px 8px 0;
        }}
        .fault-item.critical {{ border-left-color: #c0392b; background: #fadbd8; }}
        .fault-item.high {{ border-left-color: #e74c3c; background: #fdf2f2; }}
        .fault-item.medium {{ border-left-color: #f39c12; background: #fef5e7; }}
        .fault-item.low {{ border-left-color: #f1c40f; background: #fefcf3; }}
        .warning-item {{
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin-bottom: 10px;
            background: #fef5e7;
            border-radius: 0 8px 8px 0;
        }}
        .severity {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .severity.critical {{ background: #c0392b; color: white; }}
        .severity.high {{ background: #e74c3c; color: white; }}
        .severity.medium {{ background: #f39c12; color: white; }}
        .severity.low {{ background: #f1c40f; color: #333; }}
        .price {{ color: #27ae60; font-size: 24px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        table td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        table td:first-child {{
            width: 30%;
            color: #666;
        }}
        .recommendations {{
            background: #e8f4f8;
            padding: 20px;
            border-radius: 8px;
        }}
        .recommendations li {{
            margin-bottom: 10px;
            margin-left: 20px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #eee;
        }}
        .no-faults, .no-warnings {{
            text-align: center;
            padding: 30px;
            color: #27ae60;
            font-size: 18px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚁 DJI 无人机诊断报告</h1>
            <p>生成时间: {result.timestamp}</p>
        </div>
        
        <div class="content">
            <!-- 设备信息 -->
            <div class="section">
                <h2>📱 设备信息</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <label>设备型号</label>
                        <value>{result.device_info.model}</value>
                    </div>
                    <div class="info-item">
                        <label>序列号</label>
                        <value>{result.device_info.serial_number}</value>
                    </div>
                    <div class="info-item">
                        <label>固件版本</label>
                        <value>{result.device_info.firmware_version}</value>
                    </div>
                    <div class="info-item">
                        <label>飞行时间</label>
                        <value>{result.device_info.flight_time} 分钟</value>
                    </div>
                    <div class="info-item">
                        <label>电池循环</label>
                        <value>{result.device_info.battery_cycles} 次</value>
                    </div>
                    <div class="info-item">
                        <label>总飞行距离</label>
                        <value>{result.device_info.total_distance:.1f} km</value>
                    </div>
                </div>
            </div>
            
            <!-- 健康评分 -->
            <div class="section">
                <h2>💯 健康评分</h2>
                <div class="health-score">
                    <div class="score-circle">
                        <div class="score-value">{result.health_score}</div>
                    </div>
                    <p>综合健康评分 (满分100)</p>
                </div>
            </div>
            
            <!-- 故障列表 -->
            <div class="section">
                <h2>🔴 故障列表 ({len(result.faults)})</h2>
                {faults_html}
            </div>
            
            <!-- 警告列表 -->
            <div class="section">
                <h2>⚠️ 警告列表 ({len(result.warnings)})</h2>
                {warnings_html}
            </div>
            
            <!-- 二手评估 -->
            <div class="section">
                <h2>💰 二手评估</h2>
                {assessment_html}
            </div>
            
            <!-- 维修建议 -->
            <div class="section">
                <h2>💡 维修建议</h2>
                <div class="recommendations">
                    <ol>
                        {recommendations_html}
                    </ol>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>本报告由 DJI Diagnostic Tool 自动生成 | 仅供参考</p>
            <p>© 2026 喵修匠维修平台</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _build_text(self, result) -> str:
        """构建文本报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(" " * 20 + "DJI 无人机诊断报告")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"生成时间: {result.timestamp}")
        lines.append("")
        
        # 设备信息
        lines.append("-" * 70)
        lines.append("【设备信息】")
        lines.append("-" * 70)
        lines.append(f"设备型号: {result.device_info.model}")
        lines.append(f"序列号: {result.device_info.serial_number}")
        lines.append(f"固件版本: {result.device_info.firmware_version}")
        lines.append(f"飞行时间: {result.device_info.flight_time} 分钟")
        lines.append(f"电池循环: {result.device_info.battery_cycles} 次")
        lines.append(f"总飞行距离: {result.device_info.total_distance:.1f} km")
        lines.append("")
        
        # 健康评分
        lines.append("-" * 70)
        lines.append("【健康评分】")
        lines.append("-" * 70)
        lines.append(f"综合评分: {result.health_score}/100")
        lines.append("")
        
        # 故障列表
        lines.append("-" * 70)
        lines.append(f"【故障列表】({len(result.faults)})")
        lines.append("-" * 70)
        if result.faults:
            for fault in result.faults:
                lines.append(f"")
                lines.append(f"[{fault['code']}] {fault['name']}")
                lines.append(f"严重等级: {fault['severity']}")
                lines.append(f"描述: {fault['description']}")
                lines.append(f"影响系统: {', '.join(fault['affected_systems'])}")
                lines.append(f"症状:")
                for symptom in fault['symptoms']:
                    lines.append(f"  - {symptom}")
                lines.append(f"解决方案:")
                for solution in fault['solutions']:
                    lines.append(f"  - {solution}")
                lines.append(f"预估成本: {fault['estimated_cost']} | 维修时间: {fault['repair_time']}")
        else:
            lines.append("✅ 未发现故障")
        lines.append("")
        
        # 警告列表
        lines.append("-" * 70)
        lines.append(f"【警告列表】({len(result.warnings)})")
        lines.append("-" * 70)
        if result.warnings:
            for warning in result.warnings:
                lines.append(f"[{warning['code']}] {warning['name']}: {warning['description']}")
        else:
            lines.append("✅ 未发现警告")
        lines.append("")
        
        # 二手评估
        lines.append("-" * 70)
        lines.append("【二手评估】")
        lines.append("-" * 70)
        assessment = result.assessment
        lines.append(f"设备等级: {assessment.get('grade', 'N/A')} ({assessment.get('grade_label', 'N/A')})")
        lines.append(f"预估价值: ¥{assessment.get('estimated_value', 0):,.0f}")
        lines.append(f"原价参考: ¥{assessment.get('original_price', 0):,.0f}")
        lines.append(f"折旧率: {assessment.get('depreciation_rate', 0)}%")
        lines.append(f"建议售价: ¥{assessment.get('suggested_price_range', {}).get('low', 0):,.0f} - ¥{assessment.get('suggested_price_range', {}).get('high', 0):,.0f}")
        lines.append("")
        
        # 维修建议
        lines.append("-" * 70)
        lines.append("【维修建议】")
        lines.append("-" * 70)
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        lines.append("=" * 70)
        lines.append("本报告由 DJI Diagnostic Tool 自动生成 | 仅供参考")
        lines.append("© 2026 喵修匠维修平台")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _get_score_color(self, score: int) -> str:
        """根据分数获取颜色"""
        if score >= 80:
            return "#27ae60"
        elif score >= 60:
            return "#f39c12"
        elif score >= 40:
            return "#e67e22"
        else:
            return "#e74c3c"
    
    def _get_severity_color(self, severity: str) -> str:
        """根据严重等级获取颜色"""
        colors = {
            'critical': '#c0392b',
            'high': '#e74c3c',
            'medium': '#f39c12',
            'low': '#f1c40f'
        }
        return colors.get(severity, '#95a5a6')
