#!/usr/bin/env python3
"""将 ToolCallExecutor 集成到 stream_chat.py"""

filepath = 'src/omnia/stream_chat.py'

with open(filepath, 'r') as f:
    content = f.read()

# === Change 1: 添加 import ===
old = 'from omnia.tool_optimizer import ToolExecutionOptimizer, ParallelToolExecutor\nfrom src.core.actuator.tool_registry import TOOLS_SCHEMA'
new = 'from omnia.tool_optimizer import ToolExecutionOptimizer, ParallelToolExecutor\nfrom src.core.tools.tool_executor import ToolCallExecutor\nfrom src.core.actuator.tool_registry import TOOLS_SCHEMA'
if old in content:
    content = content.replace(old, new, 1)
    print("✅ 1/3: import added")
else:
    print("❌ 1/3: import pattern not found"); exit(1)

# === Change 2: 添加 _tool_executor 初始化 + get_tool_executor 函数 ===
old2 = '_optimizer = None\n_executor = ThreadPoolExecutor(max_workers=4)  # 并行执行线程池'
new2 = '_optimizer = None\n_tool_executor = None  # 统一工具执行器\n_executor = ThreadPoolExecutor(max_workers=4)  # 并行执行线程池'
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("✅ 2a/3: _tool_executor init added")
else:
    print("❌ 2a/3: init pattern not found"); exit(1)

old3 = '    return _optimizer\n\n\ndef stream_chat('
new3 = '    return _optimizer\n\n\ndef get_tool_executor():\n    """获取统一工具执行器实例（含安全检查 + MCP 支持）"""\n    global _tool_executor\n    if _tool_executor is None:\n        _tool_executor = ToolCallExecutor()\n    return _tool_executor\n\n\ndef stream_chat('
if old3 in content:
    content = content.replace(old3, new3, 1)
    print("✅ 2b/3: get_tool_executor function added")
else:
    print("❌ 2b/3: function pattern not found"); exit(1)

# === Change 3: 替换工具执行部分 ===
lines = content.split('\n')
start = None
end = None
for i, line in enumerate(lines):
    if '# 使用优化器执行工具（支持并行 + 缓存）' in line:
        start = i
    if '# 记录中间步骤' in line and start is not None:
        end = i
        break

if start is None or end is None:
    print(f"❌ 3/3: section not found (start={start}, end={end})"); exit(1)

print(f"Found tool execution section: lines {start+1}-{end+1}")

new_code = """        # 使用统一工具执行器（支持安全检查 + MCP 工具）
        tool_exec = get_tool_executor()

        # 预处理工具调用：解析 arguments JSON 字符串
        processed_tool_calls = []
        for tc in tool_calls:
            fn = tc.get("function") or {}
            tool_name = fn.get("name", "")
            args_str = fn.get("arguments", "{}")
            try:
                args = json.loads(args_str) if args_str else {}
            except Exception:
                args = {}
            processed_tool_calls.append({
                "name": tool_name,
                "arguments": args
            })

        # 分析是否可并行执行
        can_parallel, groups = ParallelToolExecutor.can_execute_in_parallel(processed_tool_calls)

        if can_parallel and len(tool_calls) > 1:
            # 并行执行（带安全检查 + MCP 支持）
            yield f"data: {json.dumps({'type': 'status', 'message': f'⚡ 并行执行 {len(tool_calls)} 个工具...'})}\\n\\n"

            def _exec_tool(processed):
                return tool_exec.execute_single(processed['name'], processed['arguments'])

            results = list(_executor.map(_exec_tool, processed_tool_calls))

            for tc, processed, exec_result in zip(tool_calls, processed_tool_calls, results):
                tool_name = processed['name']
                args = processed['arguments']
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'arguments': args})}\\n\\n"

                result_content = exec_result.output if exec_result.success else (exec_result.error or "执行失败")
                result_summary = result_content[:100]
                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'content': result_content[:200]})}\\n\\n"

                tool_call_id = tc.get("id", "")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result_content
                })
                execution_history.append({
                    'name': tool_name, 'args': args,
                    'result_summary': result_summary,
                    'success': exec_result.success, 'iteration': iteration
                })
        else:
            # 逐个执行（带安全检查 + MCP 支持）
            for tc, processed in zip(tool_calls, processed_tool_calls):
                tool_name = processed['name']
                args = processed['arguments']
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在执行工具: {tool_name}...'})}\\n\\n"
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'arguments': args})}\\n\\n"

                exec_result = tool_exec.execute_single(tool_name, args)

                result_content = exec_result.output if exec_result.success else (exec_result.error or "执行失败")
                result_summary = result_content[:100]
                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'content': result_content[:200]})}\\n\\n"

                tool_call_id = tc.get("id", "")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result_content
                })
                execution_history.append({
                    'name': tool_name, 'args': args,
                    'result_summary': result_summary,
                    'success': exec_result.success, 'iteration': iteration
                })
"""

new_lines = lines[:start] + [new_code] + lines[end:]
content = '\n'.join(new_lines)
print("✅ 3/3: tool execution section replaced")

with open(filepath, 'w') as f:
    f.write(content)

print("\n🎉 All done! stream_chat.py updated.")
