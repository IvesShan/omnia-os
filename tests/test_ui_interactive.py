#!/usr/bin/env python3
"""
交互式 UI 测试工具
提供手动测试指南和自动化验证
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5001"

def print_section(title):
    """打印章节标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def manual_test_guide():
    """手动测试指南"""
    print_section("📋 手动测试指南")
    
    print("\n1️⃣  访问前端界面")
    print(f"   打开浏览器: {BASE_URL}")
    print("   预期: 看到 Omnia 管理面板")
    
    print("\n2️⃣  检查状态指示器")
    print("   预期: 右上角显示 '🟢 运行中'")
    
    print("\n3️⃣  测试模型切换")
    print("   操作: 点击 '🖥️ 本地 GPU' 按钮")
    print("   预期: 按钮高亮，显示 '当前模式: 本地 GPU'")
    print("   操作: 点击 '☁️ 云端模型' 按钮")
    print("   预期: 按钮高亮，显示 '当前模式: 云端模型'")
    
    print("\n4️⃣  测试聊天功能")
    print("   操作: 在聊天框输入 '你好'")
    print("   预期: 收到 AI 回复")
    
    print("\n5️⃣  检查响应式布局")
    print("   操作: 调整浏览器窗口大小")
    print("   预期: 布局自适应，卡片正确排列")
    
    print("\n6️⃣  测试刷新保持状态")
    print("   操作: 切换到本地模式，刷新页面")
    print("   预期: 仍然显示本地模式")

def automated_ui_checks():
    """自动化 UI 检查"""
    print_section("🤖 自动化 UI 检查")
    
    checks = []
    
    # 1. 检查前端页面
    print("\n[1/6] 检查前端页面...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            html = response.text
            
            # 检查关键元素
            elements = {
                "标题": "Omnia" in html,
                "导航": "仪表盘" in html and "记忆管理" in html,
                "模型切换容器": "model-switcher" in html,
                "状态指示器": "status-indicator" in html,
                "Tailwind CSS": "tailwindcss" in html
            }
            
            print("   ✅ 页面加载成功")
            for elem, exists in elements.items():
                status = "✓" if exists else "✗"
                print(f"   {status} {elem}")
                checks.append(("页面元素", elem, exists))
        else:
            print(f"   ❌ 状态码: {response.status_code}")
            checks.append(("页面加载", "HTTP", False))
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        checks.append(("页面加载", "连接", False))
    
    # 2. 检查静态资源
    print("\n[2/6] 检查静态资源...")
    resources = {
        "CSS": "/static/css/app.css",
        "App JS": "/static/js/app.js",
        "Model Switcher JS": "/static/js/model-switcher.js"
    }
    
    for name, path in resources.items():
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                print(f"   ✓ {name} ({len(response.text)} bytes)")
                checks.append(("静态资源", name, True))
            else:
                print(f"   ✗ {name} (状态码: {response.status_code})")
                checks.append(("静态资源", name, False))
        except Exception as e:
            print(f"   ✗ {name} ({e})")
            checks.append(("静态资源", name, False))
    
    # 3. 检查 API 端点
    print("\n[3/6] 检查 API 端点...")
    endpoints = {
        "健康检查": "/health",
        "模型状态": "/api/model/status",
        "模型健康": "/api/model/health"
    }
    
    for name, path in endpoints.items():
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                data = response.json() if 'json' in response.headers.get('content-type', '') else {}
                print(f"   ✓ {name}")
                checks.append(("API端点", name, True))
            else:
                print(f"   ✗ {name} (状态码: {response.status_code})")
                checks.append(("API端点", name, False))
        except Exception as e:
            print(f"   ✗ {name} ({e})")
            checks.append(("API端点", name, False))
    
    # 4. 测试模型切换
    print("\n[4/6] 测试模型切换...")
    modes = ["local_only", "cloud_only"]
    
    for mode in modes:
        try:
            response = requests.post(
                f"{BASE_URL}/api/model/mode",
                json={"mode": mode},
                timeout=5
            )
            
            if response.status_code == 200:
                # 验证切换
                status = requests.get(f"{BASE_URL}/api/model/status", timeout=5)
                current = status.json().get("mode")
                
                if current == mode:
                    print(f"   ✓ 切换到 {mode}")
                    checks.append(("模型切换", mode, True))
                else:
                    print(f"   ✗ 切换失败 (当前: {current})")
                    checks.append(("模型切换", mode, False))
            else:
                print(f"   ✗ {mode} (状态码: {response.status_code})")
                checks.append(("模型切换", mode, False))
        except Exception as e:
            print(f"   ✗ {mode} ({e})")
            checks.append(("模型切换", mode, False))
        
        time.sleep(0.3)
    
    # 5. 测试聊天功能
    print("\n[5/6] 测试聊天功能...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "测试消息"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get("response", "")
            
            if reply:
                print(f"   ✓ 聊天功能正常 (回复长度: {len(reply)})")
                checks.append(("聊天功能", "响应", True))
            else:
                print("   ✗ 回复为空")
                checks.append(("聊天功能", "响应", False))
        else:
            print(f"   ✗ 状态码: {response.status_code}")
            checks.append(("聊天功能", "HTTP", False))
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        checks.append(("聊天功能", "连接", False))
    
    # 6. 检查响应时间
    print("\n[6/6] 检查响应时间...")
    test_paths = ["/", "/api/model/status", "/health"]
    
    for path in test_paths:
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            elapsed = (time.time() - start) * 1000
            
            if elapsed < 1000:
                print(f"   ✓ {path}: {elapsed:.0f}ms")
                checks.append(("响应时间", path, True))
            else:
                print(f"   ⚠ {path}: {elapsed:.0f}ms (较慢)")
                checks.append(("响应时间", path, False))
        except Exception as e:
            print(f"   ✗ {path}: {e}")
            checks.append(("响应时间", path, False))
    
    # 生成摘要
    print_section("📊 检查摘要")
    
    total = len(checks)
    passed = sum(1 for c in checks if c[2])
    failed = total - passed
    
    print(f"\n总计: {total} 项检查")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"成功率: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print("\n❌ 失败项目:")
        for category, item, success in checks:
            if not success:
                print(f"   - {category} > {item}")
    
    return checks

def browser_test_checklist():
    """浏览器测试清单"""
    print_section("🌐 浏览器兼容性测试清单")
    
    browsers = [
        ("Chrome/Edge", [
            "✓ 基本功能正常",
            "✓ CSS 样式正确",
            "✓ JavaScript 无错误",
            "✓ 响应式布局正常"
        ]),
        ("Firefox", [
            "✓ 基本功能正常",
            "✓ CSS 样式正确",
            "✓ JavaScript 无错误",
            "✓ 响应式布局正常"
        ]),
        ("Safari", [
            "✓ 基本功能正常",
            "✓ CSS 样式正确",
            "✓ JavaScript 无错误",
            "✓ 响应式布局正常"
        ])
    ]
    
    for browser, items in browsers:
        print(f"\n{browser}:")
        for item in items:
            print(f"  [ ] {item}")
    
    print("\n💡 测试建议:")
    print("   1. 在每个浏览器中完成所有测试项")
    print("   2. 检查浏览器控制台是否有错误")
    print("   3. 测试不同分辨率下的显示效果")
    print("   4. 测试移动端响应式布局")

def performance_test():
    """性能测试"""
    print_section("⚡ 性能测试")
    
    # 并发请求测试
    print("\n[并发请求测试]")
    import concurrent.futures
    
    def make_request(i):
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}/api/model/status", timeout=5)
            elapsed = (time.time() - start) * 1000
            return {"id": i, "status": response.status_code, "time": elapsed}
        except Exception as e:
            return {"id": i, "error": str(e)}
    
    print("   发送 10 个并发请求...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success_count = sum(1 for r in results if "status" in r and r["status"] == 200)
    avg_time = sum(r.get("time", 0) for r in results if "time" in r) / len(results)
    
    print(f"   ✓ 成功: {success_count}/10")
    print(f"   ✓ 平均响应时间: {avg_time:.0f}ms")
    
    # 页面加载测试
    print("\n[页面加载测试]")
    try:
        start = time.time()
        response = requests.get(f"{BASE_URL}/", timeout=5)
        load_time = (time.time() - start) * 1000
        
        print(f"   ✓ 页面大小: {len(response.text)} bytes")
        print(f"   ✓ 加载时间: {load_time:.0f}ms")
        
        if load_time < 500:
            print("   ✓ 性能: 优秀")
        elif load_time < 1000:
            print("   ⚠ 性能: 良好")
        else:
            print("   ✗ 性能: 需要优化")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def main():
    """主菜单"""
    while True:
        print("\n" + "="*60)
        print("  🧪 Omnia 前端 UI 测试工具")
        print("="*60)
        print("\n选择测试类型:")
        print("  1. 📋 查看手动测试指南")
        print("  2. 🤖 运行自动化检查")
        print("  3. 🌐 浏览器兼容性测试清单")
        print("  4. ⚡ 性能测试")
        print("  5. 🏃 运行所有测试")
        print("  0. 退出")
        print("="*60)
        
        choice = input("\n请选择 (0-5): ").strip()
        
        if choice == "1":
            manual_test_guide()
        elif choice == "2":
            automated_ui_checks()
        elif choice == "3":
            browser_test_checklist()
        elif choice == "4":
            performance_test()
        elif choice == "5":
            manual_test_guide()
            automated_ui_checks()
            browser_test_checklist()
            performance_test()
        elif choice == "0":
            print("\n👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试已中断")
