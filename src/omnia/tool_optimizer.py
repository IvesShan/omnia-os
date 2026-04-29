"""
Omnia 工具循环调用优化模块
实现：Token优化 + 错误恢复 + 并行执行 + 成本预估
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    arguments: dict
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    token_count: int = 0
    
    def to_summary(self, max_length: int = 500) -> str:
        """生成结果摘要"""
        if not self.success:
            return f"[失败] {self.tool_name}: {self.error}"
        
        result_str = json.dumps(self.result, ensure_ascii=False) if isinstance(self.result, dict) else str(self.result)
        
        if len(result_str) <= max_length:
            return result_str
        
        # 智能摘要：保留开头和结尾
        half = max_length // 2 - 20
        return f"{result_str[:half]}...[已省略{len(result_str) - max_length + 40}字符]...{result_str[-half:]}"


@dataclass 
class ExecutionPlan:
    """工具执行计划"""
    steps: List[Dict[str, Any]]
    estimated_tokens: int = 0
    estimated_rounds: int = 0
    can_parallel: bool = False
    
    def get_dependencies(self, step_index: int) -> List[int]:
        """获取某个步骤的依赖"""
        if step_index >= len(self.steps):
            return []
        return self.steps[step_index].get("depends_on", [])


class ToolResultCache:
    """工具结果缓存"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache: Dict[str, ToolResult] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _make_key(self, tool_name: str, arguments: dict) -> str:
        """生成缓存键"""
        args_str = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(f"{tool_name}:{args_str}".encode()).hexdigest()
    
    def get(self, tool_name: str, arguments: dict) -> Optional[ToolResult]:
        """获取缓存结果"""
        key = self._make_key(tool_name, arguments)
        cached = self.cache.get(key)
        
        if not cached:
            return None
        
        # 检查是否过期
        age = (datetime.now() - datetime.fromisoformat(cached.timestamp)).total_seconds()
        if age > self.ttl_seconds:
            del self.cache[key]
            return None
        
        return cached
    
    def set(self, tool_name: str, arguments: dict, result: ToolResult):
        """设置缓存"""
        # LRU 淘汰
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
        
        key = self._make_key(tool_name, arguments)
        self.cache[key] = result
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()


class ContextHistoryManager:
    """上下文历史管理器 - RAG式 + 摘要"""
    
    def __init__(self, max_full_results: int = 3, summary_max_length: int = 500):
        self.max_full_results = max_full_results
        self.summary_max_length = summary_max_length
        self.full_results: List[ToolResult] = []
        self.summaries: List[str] = []
    
    def add_result(self, result: ToolResult):
        """添加工具结果"""
        # 如果超过最大完整结果数，压缩最早的
        if len(self.full_results) >= self.max_full_results:
            oldest = self.full_results.pop(0)
            self.summaries.append(oldest.to_summary(self.summary_max_length))
        
        self.full_results.append(result)
    
    def get_context_for_model(self, include_all: bool = False) -> str:
        """获取用于模型的上下文"""
        parts = []
        
        # 添加摘要
        if self.summaries:
            parts.append("【早期工具结果摘要】")
            for i, summary in enumerate(self.summaries, 1):
                parts.append(f"{i}. {summary}")
        
        # 添加完整结果
        if self.full_results:
            parts.append("\n【近期工具结果】")
            for result in self.full_results:
                status = "✓" if result.success else "✗"
                parts.append(f"{status} {result.tool_name}: {result.to_summary(self.summary_max_length)}")
        
        return "\n".join(parts)
    
    def get_token_estimate(self) -> int:
        """估算当前上下文token数"""
        # 粗略估算：每4个字符约1个token
        total_chars = sum(len(r.to_summary()) for r in self.full_results)
        total_chars += sum(len(s) for s in self.summaries)
        return total_chars // 4


class ErrorRecoveryHandler:
    """错误恢复处理器"""
    
    def __init__(self):
        self.recovery_strategies = {
            "file_not_found": self._recover_file_not_found,
            "permission_denied": self._recover_permission_denied,
            "timeout": self._recover_timeout,
            "api_error": self._recover_api_error,
        }
    
    def can_recover(self, error: str) -> bool:
        """判断是否可以恢复"""
        error_lower = error.lower()
        return any(
            key in error_lower 
            for key in ["not found", "no such file", "permission", "timeout", "error"]
        )
    
    def get_recovery_action(self, error: str, tool_name: str, arguments: dict) -> Optional[Dict[str, Any]]:
        """获取恢复动作"""
        error_lower = error.lower()
        
        if "not found" in error_lower or "no such file" in error_lower:
            return self._recover_file_not_found(tool_name, arguments)
        elif "permission" in error_lower:
            return self._recover_permission_denied(tool_name, arguments)
        elif "timeout" in error_lower:
            return self._recover_timeout(tool_name, arguments)
        
        return None
    
    def _recover_file_not_found(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """文件未找到恢复策略"""
        return {
            "action": "search_similar",
            "message": "文件未找到，尝试搜索相似文件...",
            "fallback_tool": "execute_shell",
            "fallback_args": {
                "command": f"find . -name '*{arguments.get('path', '').split('/')[-1]}' 2>/dev/null | head -5"
            }
        }
    
    def _recover_permission_denied(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """权限拒绝恢复策略"""
        return {
            "action": "try_alternative",
            "message": "权限不足，尝试备选方案...",
            "suggestions": [
                "使用 sudo 执行",
                "检查文件权限",
                "尝试其他路径"
            ]
        }
    
    def _recover_timeout(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """超时恢复策略"""
        return {
            "action": "retry_with_smaller_scope",
            "message": "操作超时，尝试缩小范围...",
            "fallback_args": {
                "timeout": 30,
                "limit": 100
            }
        }
    
    def _recover_api_error(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """API错误恢复策略"""
        return {
            "action": "retry_later",
            "message": "API错误，稍后重试...",
            "delay_seconds": 5
        }


class ParallelToolExecutor:
    """并行工具执行器"""
    
    @staticmethod
    def can_execute_in_parallel(tool_calls: List[Dict[str, Any]]) -> Tuple[bool, List[List[int]]]:
        """
        判断工具调用是否可以并行执行
        
        返回: (是否可并行, 执行分组)
        例如: (True, [[0, 2], [1, 3]]) 表示 0和2并行，1和3并行
        """
        if len(tool_calls) <= 1:
            return False, [[0]]
        
        # 分析工具类型和参数
        file_operations = {}  # 涉及的文件
        
        for i, call in enumerate(tool_calls):
            tool_name = call.get("name", call.get("function", {}).get("name", ""))
            args = call.get("arguments", call.get("function", {}).get("arguments", {}))
            
            # 记录文件操作
            if "path" in args:
                file_path = args["path"]
                if file_path not in file_operations:
                    file_operations[file_path] = []
                file_operations[file_path].append((i, tool_name))
        
        # 检查冲突：同一文件的读写操作不能并行
        conflicts = set()
        for file_path, operations in file_operations.items():
            if len(operations) > 1:
                # 同一文件有多个操作，标记为冲突
                for i, _ in operations:
                    conflicts.add(i)
        
        # 构建执行分组
        if not conflicts:
            # 无冲突，全部并行
            return True, [list(range(len(tool_calls)))]
        else:
            # 有冲突，分组执行
            parallel_group = [i for i in range(len(tool_calls)) if i not in conflicts]
            serial_groups = [[i] for i in conflicts]
            
            groups = []
            if parallel_group:
                groups.append(parallel_group)
            groups.extend(serial_groups)
            
            return len(parallel_group) > 1, groups


class ToolExecutionOptimizer:
    """工具执行优化器 - 主入口"""
    
    def __init__(
        self,
        enable_cache: bool = True,
        enable_recovery: bool = True,
        enable_parallel: bool = True,
        max_tokens_per_round: int = 8000,
        max_rounds: int = 10
    ):
        self.cache = ToolResultCache() if enable_cache else None
        self.recovery = ErrorRecoveryHandler() if enable_recovery else None
        self.parallel_executor = ParallelToolExecutor() if enable_parallel else None
        self.context_manager = ContextHistoryManager()
        
        self.max_tokens_per_round = max_tokens_per_round
        self.max_rounds = max_rounds
        
        self.total_tokens_used = 0
        self.rounds_executed = 0
    
    def estimate_cost(self, tool_calls: List[Dict], current_context_tokens: int) -> Dict[str, Any]:
        """预估执行成本"""
        # 估算每个工具调用的token消耗
        estimated_tokens_per_call = 500  # 平均每个工具调用的token
        
        total_estimated = current_context_tokens + len(tool_calls) * estimated_tokens_per_call
        estimated_rounds = min(len(tool_calls), self.max_rounds - self.rounds_executed)
        
        return {
            "estimated_tokens": total_estimated,
            "estimated_rounds": estimated_rounds,
            "current_round": self.rounds_executed + 1,
            "max_rounds": self.max_rounds,
            "should_confirm": total_estimated > self.max_tokens_per_round * 0.8
        }
    
    def should_continue(self) -> bool:
        """判断是否应该继续执行"""
        return (
            self.rounds_executed < self.max_rounds and
            self.total_tokens_used < self.max_tokens_per_round * 2
        )
    
    def process_tool_result(self, result: ToolResult) -> str:
        """处理工具结果，返回用于模型的上下文"""
        # 添加到上下文管理器
        self.context_manager.add_result(result)
        
        # 更新统计
        if result.token_count > 0:
            self.total_tokens_used += result.token_count
        else:
            # 估算token
            result.token_count = len(str(result.result)) // 4
            self.total_tokens_used += result.token_count
        
        return self.context_manager.get_context_for_model()
    
    def get_optimized_context(self) -> str:
        """获取优化后的上下文"""
        return self.context_manager.get_context_for_model()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            "rounds_executed": self.rounds_executed,
            "total_tokens_used": self.total_tokens_used,
            "cache_hits": len(self.cache.cache) if self.cache else 0,
            "full_results_count": len(self.context_manager.full_results),
            "summaries_count": len(self.context_manager.summaries)
        }
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """执行单个工具，支持缓存和错误恢复"""
        from core.actuator.tool_registry import dispatch_tool
        
        # 检查缓存
        if self.cache:
            cached = self.cache.get(tool_name, arguments)
            if cached:
                return ToolResult(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=cached,
                    success=True,
                    error=None
                ).__class__(  # 复制一个带 from_cache 标记的结果
                    tool_name=tool_name,
                    arguments=arguments,
                    result=cached,
                    success=True,
                    error=None
                )
        
        # 执行工具
        try:
            result = dispatch_tool(tool_name, arguments)
            success = True
            error = None
        except Exception as e:
            result = {"error": str(e)}
            success = False
            error = str(e)
            
            # 尝试错误恢复
            if self.recovery:
                recovery_result = self.recovery.get_recovery_action(str(e), tool_name, arguments)
                if recovery_result:
                    result = recovery_result
                    success = True
                    error = None
        
        # 缓存结果
        if self.cache and success:
            self.cache.set(tool_name, arguments, ToolResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=success,
                error=error
            ))
        
        self.rounds_executed += 1
        
        return ToolResult(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            error=error
        )
    
    def execute_tools_parallel(self, tool_calls: List[Dict]) -> List[ToolResult]:
        """并行执行多个工具"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            
            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "unknown")
                try:
                    arguments = json.loads(fn.get("arguments", "{}"))
                except Exception:
                    arguments = {}
                
                future = executor.submit(self.execute_tool, tool_name, arguments)
                futures[future] = tc
            
            for future in as_completed(futures):
                tc = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    fn = tc.get("function", {})
                    result = ToolResult(
                        tool_name=fn.get("name", "unknown"),
                        arguments={},
                        result={"error": str(e)},
                        success=False,
                        error=str(e)
                    )
                results.append(result)
        
        return results
