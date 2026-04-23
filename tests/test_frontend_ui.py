#!/usr/bin/env python3
"""
前端 UI 测试脚本
测试模型切换、状态显示、用户交互等功能
"""

import requests
import json
import time
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:5001"
TEST_RESULTS = []

def log_result(test_name, success, message=""):
    """记录测试结果"""
    result = {
        "test": test_name,
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")

def test_api_status():
    """测试 API 状态端点"""
    try:
        response = requests.get(f"{BASE_URL}/api/model/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_result("API 状态查询", True, f"当前模式: {data.get('mode', 'N/A')}")
            return True
        else:
            log_result("API 状态查询", False, f"状态码: {response.status_code}")
            return False
    except Exception as e:
        log_result("API 状态查询", False, str(e))
        return False

def test_model_switch():
    """测试模型切换功能"""
    modes = ["local_only", "cloud_only"]
    
    for mode in modes:
        try:
            # 切换模式
            response = requests.post(
                f"{BASE_URL}/api/model/mode",
                json={"mode": mode},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # 验证切换是否成功
                    status_response = requests.get(f"{BASE_URL}/api/model/status", timeout=5)
                    current_mode = status_response.json().get("mode")
                    
                    if current_mode == mode:
                        log_result(f"切换到 {mode}", True)
                    else:
                        log_result(f"切换到 {mode}", False, f"当前模式: {current_mode}")
                else:
                    log_result(f"切换到 {mode}", False, data.get("error", "未知错误"))
            else:
                log_result(f"切换到 {mode}", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            log_result(f"切换到 {mode}", False, str(e))
        
        time.sleep(0.5)  # 避免请求过快

def test_chat_function():
    """测试聊天功能"""
    test_messages = [
        "你好",
        "介绍一下你自己",
        "今天天气怎么样？"
    ]
    
    for msg in test_messages:
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": msg},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("response", "")
                
                if reply and len(reply) > 0:
                    log_result(f"聊天测试: '{msg}'", True, f"回复长度: {len(reply)}")
                else:
                    log_result(f"聊天测试: '{msg}'", False, "回复为空")
            else:
                log_result(f"聊天测试: '{msg}'", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            log_result(f"聊天测试: '{msg}'", False, str(e))
        
        time.sleep(1)

def test_health_check():
    """测试健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            log_result("健康检查", True)
            return True
        else:
            log_result("健康检查", False, f"状态码: {response.status_code}")
            return False
    except Exception as e:
        log_result("健康检查", False, str(e))
        return False

def test_model_health():
    """测试模型健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/api/model/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            local_health = data.get("local", {}).get("healthy", False)
            cloud_health = data.get("cloud", {}).get("healthy", False)
            
            log_result(
                "模型健康检查", 
                True, 
                f"本地: {'✓' if local_health else '✗'}, 云端: {'✓' if cloud_health else '✗'}"
            )
            return True
        else:
            log_result("模型健康检查", False, f"状态码: {response.status_code}")
            return False
    except Exception as e:
        log_result("模型健康检查", False, str(e))
        return False

def test_frontend_access():
    """测试前端页面访问"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            # 检查关键 HTML 元素
            html = response.text
            checks = {
                "标题": "Omnia" in html,
                "导航栏": "仪表盘" in html,
                "状态指示器": "status-indicator" in html
            }
            
            all_passed = all(checks.values())
            details = ", ".join([k for k, v in checks.items() if not v])
            
            log_result("前端页面访问", all_passed, f"缺失: {details}" if not all_passed else "所有元素存在")
            return all_passed
        else:
            log_result("前端页面访问", False, f"状态码: {response.status_code}")
            return False
    except Exception as e:
        log_result("前端页面访问", False, str(e))
        return False

def test_static_resources():
    """测试静态资源加载"""
    resources = [
        "/static/css/app.css",
        "/static/js/app.js",
        "/static/js/model-switcher.js"
    ]
    
    for resource in resources:
        try:
            response = requests.get(f"{BASE_URL}{resource}", timeout=5)
            if response.status_code == 200:
                log_result(f"静态资源: {resource}", True)
            else:
                log_result(f"静态资源: {resource}", False, f"状态码: {response.status_code}")
        except Exception as e:
            log_result(f"静态资源: {resource}", False, str(e))

def test_error_handling():
    """测试错误处理"""
    # 测试无效模式
    try:
        response = requests.post(
            f"{BASE_URL}/api/model/mode",
            json={"mode": "invalid_mode"},
            timeout=5
        )
        
        if response.status_code == 400:
            log_result("错误处理: 无效模式", True, "正确返回 400")
        else:
            log_result("错误处理: 无效模式", False, f"状态码: {response.status_code}")
    except Exception as e:
        log_result("错误处理: 无效模式", False, str(e))

def generate_report():
    """生成测试报告"""
    total = len(TEST_RESULTS)
    passed = sum(1 for r in TEST_RESULTS if r["success"])
    failed = total - passed
    
    print("\n" + "="*60)
    print("📊 测试报告")
    print("="*60)
    print(f"总计: {total} 项测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"成功率: {(passed/total*100):.1f}%")
    print("="*60)
    
    if failed > 0:
        print("\n❌ 失败的测试:")
        for result in TEST_RESULTS:
            if not result["success"]:
                print(f"  - {result['test']}: {result['message']}")
    
    # 保存报告到文件
    report_path = "/home/shan//home/shan/omnia-os/omnia-os/tests/test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": f"{(passed/total*100):.1f}%"
            },
            "results": TEST_RESULTS
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: {report_path}")
    
    return failed == 0

def main():
    """主测试流程"""
    print("="*60)
    print("🧪 Omnia 前端 UI 测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标服务: {BASE_URL}")
    print("="*60 + "\n")
    
    # 检查服务是否运行
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        print("❌ 后端服务未运行！请先启动: python3 src/omnia/web_server.py")
        sys.exit(1)
    
    print("📋 开始测试...\n")
    
    # 执行测试
    test_health_check()
    test_frontend_access()
    test_static_resources()
    test_api_status()
    test_model_health()
    test_model_switch()
    test_chat_function()
    test_error_handling()
    
    # 生成报告
    success = generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
