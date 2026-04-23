"""
Web 服务器简单引擎集成补丁

将简单引擎集成到 chat API，实现 LLM 降级策略。
"""

# 在 web_server.py 中添加以下代码

# 1. 导入简单引擎
from omnia.simple_engine import SimpleEngine, TaskComplexity

# 2. 初始化简单引擎（在文件顶部）
_simple_engine = None

def get_simple_engine():
    """获取简单引擎实例（懒加载）"""
    global _simple_engine
    if _simple_engine is None:
        try:
            _simple_engine = SimpleEngine(workspace_root=WORKSPACE)
        except Exception as e:
            print(f"[WebServer] Warning: Simple engine unavailable: {e}")
    return _simple_engine


# 3. 修改 chat_stream 端点，添加降级逻辑
# 在现有的 @app.route('/api/chat/stream', methods=['POST']) 函数中添加：

"""
原代码:
    # 调用模型
    reply = await call_model(messages, provider, api_key)

修改为:
    # 尝试调用 LLM，失败时降级到简单引擎
    try:
        reply = await call_model(messages, provider, api_key)
    except Exception as e:
        print(f"[WebServer] LLM call failed: {e}, falling back to simple engine")
        
        # 降级到简单引擎
        engine = get_simple_engine()
        if engine:
            result = engine.process(user_message, conversation_history)
            reply = result.reply
            
            # 如果简单引擎也无法处理，返回错误
            if result.needs_llm:
                reply = f"抱歉，当前系统运行在简化模式，无法处理此请求。\n\n错误原因: {str(e)}\n\n建议：\n1. 检查 API Key 配置\n2. 检查网络连接\n3. 稍后重试"
        else:
            reply = f"抱歉，系统当前不可用。\n\n错误: {str(e)}"
"""


# 4. 添加健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    """系统健康检查"""
    from datetime import datetime
    import psutil
    
    # 检查进程状态
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'omnia' in cmdline.lower() or 'web_server' in cmdline.lower():
                processes.append({
                    'pid': proc.info['pid'],
                    'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                })
        except:
            continue
    
    # 检查简单引擎
    engine = get_simple_engine()
    simple_engine_available = engine is not None and engine.is_available()
    
    # 检查记忆系统
    memory_available = False
    try:
        from core.memory_palace.memory_palace import MemoryPalace
        memory = MemoryPalace(WORKSPACE)
        memory_available = True
    except:
        pass
    
    # 构建响应
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'web_server': True,
            'simple_engine': simple_engine_available,
            'memory_system': memory_available,
            'llm': False,  # 需要实际检查
        },
        'processes': processes,
        'system': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
        }
    }
    
    # 判断整体状态
    if not all(health['components'].values()):
        health['status'] = 'degraded'
    
    return jsonify(health)


# 5. 添加简单引擎测试端点
@app.route('/api/simple/test', methods=['POST'])
def test_simple_engine():
    """测试简单引擎"""
    data = request.get_json()
    user_message = data.get('message', '')
    
    engine = get_simple_engine()
    if not engine:
        return jsonify({'error': 'Simple engine not available'}), 503
    
    result = engine.process(user_message)
    
    return jsonify({
        'reply': result.reply,
        'confidence': result.confidence,
        'complexity': result.complexity.value,
        'needs_llm': result.needs_llm,
        'source': result.source,
    })


print("✅ Simple engine integration patch loaded")
