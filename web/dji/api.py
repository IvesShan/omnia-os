#!/usr/bin/env python3
"""
DJI 诊断工具 - 后端 API
Omnia OS - 2026
"""

import json
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# DJI 设备知识库
DJI_DEVICES = {
    'wm160': {'name': 'Mini SE', 'type': 'drone', 'release': '2021'},
    'wm161': {'name': 'Mini 2', 'type': 'drone', 'release': '2020'},
    'wm1615': {'name': 'Mini 2 SE', 'type': 'drone', 'release': '2023'},
    'wm163': {'name': 'Mini 3', 'type': 'drone', 'release': '2022'},
    'wm1605': {'name': 'Mini 3 Pro', 'type': 'drone', 'release': '2022'},
    'wm170': {'name': 'Mini 4 Pro', 'type': 'drone', 'release': '2023'},
    'wm231': {'name': 'Air 2S', 'type': 'drone', 'release': '2021'},
    'wm232': {'name': 'Mavic Air 2', 'type': 'drone', 'release': '2020'},
    'wm240': {'name': 'Mavic 3', 'type': 'drone', 'release': '2021'},
    'wm245': {'name': 'Mavic 3 Classic', 'type': 'drone', 'release': '2022'},
    'wm246': {'name': 'Mavic 3 Pro', 'type': 'drone', 'release': '2023'},
    'rc221': {'name': 'RC-N1', 'type': 'remote', 'release': '2020'},
    'rc430': {'name': 'RC Pro', 'type': 'remote', 'release': '2021'},
    'rc600': {'name': 'RC Plus', 'type': 'remote', 'release': '2022'},
    'wa140': {'name': 'Goggles 2', 'type': 'goggles', 'release': '2022'},
    'wa152': {'name': 'Goggles 3', 'type': 'goggles', 'release': '2023'},
}

# 错误码知识库
ERROR_CODES = {
    '0x0001': {'desc': '电机故障', 'solution': '检查电机是否卡住，清洁电机'},
    '0x0002': {'desc': 'IMU校准失败', 'solution': '在平坦地面重新校准IMU'},
    '0x0003': {'desc': '指南针干扰', 'solution': '远离金属物体，重新校准指南针'},
    '0x0004': {'desc': '电池温度异常', 'solution': '让电池恢复室温后再使用'},
    '0x0005': {'desc': '存储卡错误', 'solution': '更换存储卡或格式化'},
}



import subprocess
import re

@app.route('/api/dji/scan', methods=['GET'])
def scan_devices():
    """扫描真实USB设备"""
    try:
        # 使用 lsusb 扫描 USB 设备
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        
        devices = []
        djivendor_id = '2ca3'  # DJI Vendor ID
        
        for line in result.stdout.split('\n'):
            if 'DJI' in line or djivendor_id in line.lower():
                # 解析 lsusb 输出: Bus 001 Device 017: ID 2ca3:0020 DJI Technology Co., Ltd. ...
                match = re.search(r'ID\s+([0-9a-f]+):([0-9a-f]+)\s+(.+)', line, re.I)
                if match:
                    vendor_id = match.group(1)
                    product_id = match.group(2)
                    product_name = match.group(3).strip()
                    
                    # 判断设备类型
                    pid_int = int(product_id, 16)
                    if 0x0020 <= pid_int <= 0x0030:
                        device_type = 'drone'
                    elif 0x0040 <= pid_int <= 0x0050:
                        device_type = 'remote'
                    elif 0x0060 <= pid_int <= 0x0070:
                        device_type = 'goggles'
                    else:
                        device_type = 'unknown'
                    
                    devices.append({
                        'vendor_id': vendor_id,
                        'product_id': product_id,
                        'product': product_name,
                        'manufacturer': 'DJI',
                        'serial_number': 'N/A',
                        'type': device_type
                    })
        
        logger.info(f"扫描完成，发现 {len(devices)} 个 DJI 设备")
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices),
            'timestamp': datetime.now().isoformat()
        })
    except subprocess.TimeoutExpired:
        logger.error("USB 扫描超时")
        return jsonify({'success': False, 'error': '扫描超时'}), 500
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dji/devices', methods=['GET'])
def get_devices():
    """获取设备列表"""
    try:
        # 模拟扫描USB设备
        devices = []
        for device_id, info in DJI_DEVICES.items():
            devices.append({
                'id': device_id,
                'name': info['name'],
                'type': info['type'],
                'model': device_id.upper(),
                'release': info['release'],
                'status': 'available'
            })
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dji/device/<device_id>', methods=['GET'])
def get_device_info(device_id):
    """获取设备详细信息"""
    try:
        if device_id not in DJI_DEVICES:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        
        device = DJI_DEVICES[device_id]
        
        # 模拟设备信息
        info = {
            'id': device_id,
            'name': device['name'],
            'type': device['type'],
            'model': device_id.upper(),
            'release': device['release'],
            'firmware': 'v1.2.3',
            'serial': f'{device_id.upper()}-DEMO-{datetime.now().strftime("%Y%m%d")}',
            'battery': 85,
            'temperature': 42,
            'status': 'connected',
            'last_seen': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'device': info
        })
    except Exception as e:
        logger.error(f"获取设备信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dji/diagnose/<device_id>', methods=['POST'])
def diagnose_device(device_id):
    """运行设备诊断"""
    try:
        if device_id not in DJI_DEVICES:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        
        # 模拟诊断过程
        diagnosis = {
            'device_id': device_id,
            'timestamp': datetime.now().isoformat(),
            'health_score': 85,
            'checks': [
                {
                    'name': 'IMU状态',
                    'status': 'pass',
                    'message': 'IMU工作正常'
                },
                {
                    'name': '电池健康',
                    'status': 'pass',
                    'message': '电池循环次数: 45次'
                },
                {
                    'name': '电机状态',
                    'status': 'pass',
                    'message': '4个电机工作正常'
                },
                {
                    'name': '存储状态',
                    'status': 'warning',
                    'message': '存储卡剩余空间不足20%'
                }
            ],
            'recommendations': [
                '建议更换或清理存储卡',
                '定期检查电机轴承'
            ]
        }
        
        return jsonify({
            'success': True,
            'diagnosis': diagnosis
        })
    except Exception as e:
        logger.error(f"诊断失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dji/error/<error_code>', methods=['GET'])
def get_error_info(error_code):
    """查询错误码信息"""
    try:
        if error_code not in ERROR_CODES:
            return jsonify({
                'success': False,
                'error': '未知错误码',
                'code': error_code
            }), 404
        
        error = ERROR_CODES[error_code]
        
        return jsonify({
            'success': True,
            'code': error_code,
            'description': error['desc'],
            'solution': error['solution']
        })
    except Exception as e:
        logger.error(f"查询错误码失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dji/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'service': 'DJI Diagnostic API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    logger.info("🚀 DJI 诊断 API 启动中...")
    logger.info("📍 地址: http://localhost:5002")
    logger.info("📚 文档: http://localhost:5002/api/dji/health")
    
    app.run(host='0.0.0.0', port=5002, debug=True)
