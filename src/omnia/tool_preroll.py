"""
tool_preroll.py — 前置工具检查钩子（Pre-Response Tool Check Hook）

方案A实现：在消息发给 LLM 之前，强制检查用户消息是否涉及需要工具验证的场景。
如果命中关键词，直接执行 shell 命令并将结果注入提示上下文。

改进：使用统一的 tool_trigger 模块判断触发条件。
"""

import re
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# ─── 关键词 → 工具命令映射 ───
# 每条规则: (关键词正则, [(描述, shell命令), ...])
TRIGGER_RULES = [
    # 1. 进度条/上下文占比
    (r"(进度条|percentage|utilization|上下文.*占比|上下文.*进度|800%)",
     [
         ("前端进度条代码", "grep -n 'percentage\\|utilization' web/app.js 2>/dev/null || echo '未找到 web/app.js'"),
         ("后端token状态", "grep -n 'percentage\\|utilization' src/omnia/web_server.py 2>/dev/null | head -5 || echo '未找到'"),
     ]),

    # 2. 消息上限/聊天卡顿
    (r"(消息上限|消息.*上限|MAX_MESSAGES|消息.*清理|50条|too many|卡顿|聊天.*上限|消息.*过多)",
     [
         ("前端消息上限", "grep -n 'MAX_MESSAGES\\|>=\\s*50\\|children.length\\|removeChild' src/omnia/frontend/app.js 2>/dev/null | head -10 || echo '未找到'"),
         ("Web前端消息上限", "grep -n 'MAX_MESSAGES\\|>=\\s*50\\|children.length\\|removeChild' web/app.js 2>/dev/null | head -10 || echo '未找到'"),
     ]),

    # 3. Three.js/神经图谱暂停
    (r"(Three\\.js|神经图谱|图谱.*暂停|pause|visibility|animate.*暂停|graph-viz|3D.*暂停|图谱.*性能)",
     [
         ("前端Three.js暂停", "grep -n 'visibilityState\\|cancelAnimationFrame\\|isPageVisible' scripts/graph-viz.js 2>/dev/null | head -10 || echo '未找到 scripts/graph-viz.js'"),
         ("Web版暂停", "grep -n 'visibilityState\\|cancelAnimationFrame\\|isPageVisible' web/graph-viz.js 2>/dev/null | head -10 || echo '未找到 web/graph-viz.js'"),
     ]),

    # 4. Git 状态/提交记录
    (r"(git|提交|commit|有没有提交|生效了没|提交记录|git.*log|代码.*提交|改了什么)",
     [
         ("最近Git提交", "git -C " + str(PROJECT_ROOT) + " log --oneline -10 2>/dev/null || echo '不是git仓库'"),
         ("Git状态", "git -C " + str(PROJECT_ROOT) + " status --short 2>/dev/null | head -20 || echo '不是git仓库'"),
     ]),

    # 5. 服务/进程/端口检查
    (r"(服务|运行|启动|端口|5001|8765|进程|daemon|重启.*成功|在线|状态)",
     [
         ("端口5001", "ss -tlnp 2>/dev/null | grep 5001 || echo '端口5001未监听'"),
         ("端口8765", "ss -tlnp 2>/dev/null | grep 8765 || echo '端口8765未监听'"),
     ]),

    # 6. 文件读取/查看代码
    (r"(读文件|查看.*文件|检查.*文件|cat|read.*file|查看代码|看看代码|代码.*什么样)",
     [
         ("项目文件结构", "ls -la --color=never " + str(PROJECT_ROOT) + " 2>/dev/null | head -20 || echo 'ls失败'"),
     ]),

    # 7. 通用"检查/分析"动词（兜底）- 扩展关键词
    (r"(检查|确认|验证|核实|查一下|看看|检查一下|检测|测试|试一下|跑一下|分析|重新分析|完整分析|全面分析|改好了吗|生效了吗|有没有生效|状态怎么样|怎么样了|完成了吗|成功了吗|好了没|有没有问题|深入分析)",
     [
         ("通用检查 - Git状态", "git -C " + str(PROJECT_ROOT) + " status --short 2>/dev/null | head -20 || echo '不是git仓库'"),
         ("通用检查 - 最近提交", "git -C " + str(PROJECT_ROOT) + " log --oneline -5 2>/dev/null || echo '不是git仓库'"),
         ("通用检查 - 端口监听", "ss -tlnp 2>/dev/null | grep -E '5001|8765' || echo '无相关端口'"),
     ]),

    # 8. 工具调用相关问题（新增）
    (r"(工具.*调用|调用.*工具|tool.*call|为什么不.*工具|工具.*问题)",
     [
         ("工具注册检查", "grep -n 'TOOLS_SCHEMA\\|dispatch_tool' " + str(PROJECT_ROOT) + "/src/core/actuator/tool_registry.py 2>/dev/null | head -10 || echo '未找到'"),
         ("Chat Handler 检查", "grep -n 'tool_choice\\|should_require_tool' " + str(PROJECT_ROOT) + "/src/omnia/chat_handler.py 2>/dev/null | head -10 || echo '未找到'"),
     ]),
]


def check_and_run(user_message: str) -> str:
    """
    检查用户消息是否命中关键词触发器。
    如果命中，执行对应的 shell 命令并返回结果文本。
    如果未命中，返回空字符串。
    """
    results = []

    for pattern, commands in TRIGGER_RULES:
        if re.search(pattern, user_message, re.IGNORECASE):
            results.append(f"🔍 [前置工具检查] 命中关键词: '{pattern}'")
            for desc, cmd in commands:
                try:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    output = result.stdout.strip() or result.stderr.strip() or "(无输出)"
                    # 截断防止过长
                    if len(output) > 300:
                        output = output[:300] + "..."
                    results.append(f"  📋 {desc}:")
                    results.append(f"    {output}")
                except subprocess.TimeoutExpired:
                    results.append(f"  ⏱️ {desc}: 超时")
                except Exception as e:
                    results.append(f"  ❌ {desc}: 错误 - {e}")
            break  # 只匹配第一条命中的规则

    if results:
        return "\n".join(results)
    return ""


def should_force_tool_check(user_message: str, last_assistant_message: str = "") -> bool:
    """
    判断是否应该强制执行工具检查。
    
    改进：使用统一的 tool_trigger 模块。
    """
    # 尝试使用新模块
    try:
        from omnia.tool_trigger import analyze_message
        result = analyze_message(user_message, last_assistant_message)
        return result.should_trigger
    except ImportError:
        # 回退到旧逻辑
        pass
    
    # 条件1：关键词触发器
    for pattern, _ in TRIGGER_RULES:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True

    # 条件2：上条助理消息包含承诺检查的表述
    check_promises = r"(让我检查|让我看看|让我查|检查一下|看一下|读一下|让我读|看看效果|验证一下)"
    if re.search(check_promises, last_assistant_message, re.IGNORECASE):
        return True

    # 条件3：用户明确要求工具
    tool_requests = r"(调用工具|用工具|执行工具|工具调用)"
    if re.search(tool_requests, user_message, re.IGNORECASE):
        return True

    return False
