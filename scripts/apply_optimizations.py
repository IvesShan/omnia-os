#!/usr/bin/env python3
"""
Omnia 优化补丁应用器
安全地应用后续优化，支持回滚
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
WEB_SERVER_PATH = PROJECT_ROOT / "src" / "omnia" / "web_server.py"
BACKUP_DIR = PROJECT_ROOT / ".omnia" / "backups"


def create_backup():
    """创建备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"web_server_{timestamp}.py"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(WEB_SERVER_PATH, backup_path)
    print(f"✅ 备份已创建: {backup_path}")
    return backup_path


def apply_simple_engine_integration():
    """集成简单引擎到 web_server.py"""
    
    # 读取当前文件
    content = WEB_SERVER_PATH.read_text(encoding='utf-8')
    
    # 1. 添加导入语句
    import_insertion = """from omnia.wake import assemble_wake_prompt

# Simple Engine Integration
from omnia.simple_engine import SimpleEngine, TaskComplexity
_simple_engine = None

def get_simple_engine():
    global _simple_engine
    if _simple_engine is None:
        _simple_engine = SimpleEngine()
    return _simple_engine
"""
    
    if "from omnia.simple_engine import" not in content:
        content = content.replace(
            "from omnia.wake import assemble_wake_prompt",
            import_insertion
        )
        print("✅ 已添加简单引擎导入")
    
    # 2. 在 chat() 函数中添加降级逻辑
    # 找到 chat() 函数中 "if not message:" 之后的位置
    degradation_code = '''
        # === 简单引擎降级逻辑 ===
        try:
            engine = get_simple_engine()
            simple_response = engine.process(message)
            
            # 如果是简单任务且置信度高，直接返回
            if not simple_response.needs_llm and simple_response.confidence > 0.7:
                return jsonify({
                    "response": simple_response.reply,
                    "source": "simple_engine",
                    "confidence": simple_response.confidence,
                    "complexity": simple_response.complexity.value
                })
        except Exception as e:
            print(f"[SimpleEngine] Error: {e}")
        # === 降级逻辑结束 ===
'''
    
    if "简单引擎降级逻辑" not in content:
        # 在 "if not message:" 之后插入
        content = content.replace(
            'if not message:\n            return jsonify({"error": "消息不能为空"}), 400',
            f'if not message:\n            return jsonify({{"error": "消息不能为空"}}), 400{degradation_code}'
        )
        print("✅ 已添加降级逻辑")
    
    # 3. 添加健康检查端点
    health_endpoint = '''

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """系统健康检查端点"""
        import psutil
        import os
        
        # 检查进程状态
        daemon_pid_path = OMNIA_HOME / "daemon.pid"
        daemon_running = False
        if daemon_pid_path.exists():
            try:
                pid = int(daemon_pid_path.read_text().strip())
                daemon_running = psutil.pid_exists(pid)
            except:
                pass
        
        # 检查内存使用
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # 检查简单引擎
        engine_status = "available"
        try:
            engine = get_simple_engine()
            engine.process("test")
        except Exception as e:
            engine_status = f"error: {str(e)}"
        
        return jsonify({
            "status": "healthy" if daemon_running else "degraded",
            "daemon_running": daemon_running,
            "web_server_memory_mb": round(memory_mb, 2),
            "simple_engine": engine_status,
            "timestamp": datetime.now().isoformat()
        })
'''
    
    if "/api/health" not in content:
        # 找到最后一个路由定义的位置
        last_route_pos = content.rfind('@app.route("')
        if last_route_pos > 0:
            # 找到这个函数的结束位置
            next_def_pos = content.find('\n    @app.route', last_route_pos + 1)
            if next_def_pos == -1:
                next_def_pos = content.find('\n    def ', last_route_pos + 1)
            
            if next_def_pos > 0:
                content = content[:next_def_pos] + health_endpoint + content[next_def_pos:]
                print("✅ 已添加健康检查端点")
    
    # 写回文件
    WEB_SERVER_PATH.write_text(content, encoding='utf-8')
    print(f"✅ 已更新: {WEB_SERVER_PATH}")
    return True


def main():
    print("=" * 60)
    print("Omnia 后续优化应用器")
    print("=" * 60)
    
    # 创建备份
    backup_path = create_backup()
    
    try:
        # 应用优化
        apply_simple_engine_integration()
        
        print("\n" + "=" * 60)
        print("✅ 所有优化已成功应用")
        print(f"📦 备份位置: {backup_path}")
        print("🔄 如需回滚，运行: python scripts/rollback_optimizations.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 应用失败: {e}")
        print(f"🔄 正在从备份恢复...")
        shutil.copy(backup_path, WEB_SERVER_PATH)
        print("✅ 已恢复备份")
        raise


if __name__ == "__main__":
    main()
