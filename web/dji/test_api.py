#!/usr/bin/env python3
"""
DJI 诊断工具 - 测试脚本
测试API是否正常工作
"""

import requests
import json
import time

API_BASE = 'http://localhost:5002/api/dji'

def test_api():
    print("🧪 测试 DJI 诊断 API...")
    print()
    
    # 测试1: 健康检查
    print("1️⃣ 测试健康检查...")
    try:
        response = requests.get(f'{API_BASE}/health')
        if response.status_code == 200:
            print("   ✅ API 服务正常")
            print(f"   {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            print("   ❌ API 服务异常")
            return False
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False
    
    print()
    
    # 测试2: 获取设备列表
    print("2️⃣ 测试设备列表...")
    try:
        response = requests.get(f'{API_BASE}/devices')
        data = response.json()
        if data['success']:
            print(f"   ✅ 找到 {data['count']} 个设备")
            print(f"   设备: {', '.join([d['name'] for d in data['devices'][:5]])}...")
        else:
            print("   ❌ 获取设备列表失败")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试3: 获取设备信息
    print("3️⃣ 测试设备信息 (WM163 - Mini 3)...")
    try:
        response = requests.get(f'{API_BASE}/device/wm163')
        data = response.json()
        if data['success']:
            device = data['device']
            print(f"   ✅ 设备: {device['name']}")
            print(f"   型号: {device['model']}")
            print(f"   固件: {device['firmware']}")
        else:
            print("   ❌ 获取设备信息失败")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试4: 运行诊断
    print("4️⃣ 测试设备诊断...")
    try:
        response = requests.post(f'{API_BASE}/diagnose/wm163')
        data = response.json()
        if data['success']:
            diagnosis = data['diagnosis']
            print(f"   ✅ 健康分数: {diagnosis['health_score']}")
            print(f"   检查项: {len(diagnosis['checks'])} 项")
        else:
            print("   ❌ 诊断失败")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试5: 查询错误码
    print("5️⃣ 测试错误码查询...")
    try:
        response = requests.get(f'{API_BASE}/error/0x0001')
        data = response.json()
        if data['success']:
            print(f"   ✅ 错误码: {data['code']}")
            print(f"   描述: {data['description']}")
            print(f"   解决: {data['solution']}")
        else:
            print("   ❌ 查询失败")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    print("✨ 测试完成！")
    return True


if __name__ == '__main__':
    print("⚠️  请先启动 API 服务: python3 api.py")
    print("⏳ 等待 3 秒后开始测试...")
    print()
    time.sleep(3)
    test_api()
