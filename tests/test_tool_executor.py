"""
ToolCallExecutor 单元测试

覆盖场景：
1. 解析 OpenAI tool_calls 格式
2. 解析文本中的工具调用
3. 安全检查拦截
4. 单个工具执行
5. 批量执行
6. 结果格式化
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.core.actuator.tool_executor import (
    ToolCallExecutor,
    ExecutionResult,
    BatchExecutionResult,
    get_tool_executor,
    reset_tool_executor,
)
from src.core.actuator.tool_call_protocol import (
    ToolCall,
    ToolCallFormat,
    ToolResult,
    ToolCallParser,
)


@pytest.fixture(autouse=True)
def cleanup():
    reset_tool_executor()
    yield
    reset_tool_executor()


@pytest.fixture
def executor():
    return ToolCallExecutor(enable_safety_check=False)


@pytest.fixture
def safe_executor():
    return ToolCallExecutor(enable_safety_check=True)


# ─────────────────────────────────────────────
# 1. 解析 OpenAI tool_calls
# ─────────────────────────────────────────────

class TestParseOpenAIToolCalls:
    """测试从 OpenAI 格式响应中解析工具调用"""

    def test_parse_single_tool_call(self):
        response = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "/tmp/test.txt"}'
                        }
                    }]
                }
            }]
        }
        calls = ToolCallParser.parse(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "/tmp/test.txt"}
        assert calls[0].format == ToolCallFormat.OPENAI_TOOL_CALLS

    def test_parse_multiple_tool_calls(self):
        response = {
            "choices": [{
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "/tmp/a.txt"}'
                            }
                        },
                        {
                            "id": "call_2",
                            "function": {
                                "name": "list_directory",
                                "arguments": '{"path": "/tmp"}'
                            }
                        }
                    ]
                }
            }]
        }
        calls = ToolCallParser.parse(response)
        assert len(calls) == 2
        assert calls[0].name == "read_file"
        assert calls[1].name == "list_directory"

    def test_parse_no_tool_calls(self):
        response = {
            "choices": [{
                "message": {
                    "content": "这是一个普通回复"
                }
            }]
        }
        calls = ToolCallParser.parse(response)
        assert len(calls) == 0


# ─────────────────────────────────────────────
# 2. 解析文本中的工具调用
# ─────────────────────────────────────────────

class TestParseTextToolCalls:
    """测试从文本中解析工具调用"""

    def test_parse_json_block(self):
        response = {
            "choices": [{
                "message": {
                    "content": '我来读取文件：\n```json\n[{"tool": "read_file", "arguments": {"path": "/tmp/test.txt"}}]\n```'
                }
            }]
        }
        calls = ToolCallParser.parse(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].format == ToolCallFormat.TEXT_JSON_BLOCK

    def test_parse_function_call_format(self):
        response = {
            "choices": [{
                "message": {
                    "content": '让我查看：read_file("/tmp/test.txt")'
                }
            }]
        }
        calls = ToolCallParser.parse(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "/tmp/test.txt"}


# ─────────────────────────────────────────────
# 3. 安全检查
# ─────────────────────────────────────────────

class TestSafetyCheck:
    """测试安全门控"""

    @pytest.mark.asyncio
    async def test_blocked_command(self):
        executor = ToolCallExecutor(enable_safety_check=True)
        result = await executor.execute_single(
            "execute_shell",
            {"command": "rm -rf /"}
        )
        assert result.blocked is True
        assert result.tool_result.success is False
        assert "BLOCKED" in result.tool_result.content

    @pytest.mark.asyncio
    async def test_safe_command(self):
        executor = ToolCallExecutor(enable_safety_check=True)
        with patch("src.core.actuator.tool_executor.dispatch_tool", new_callable=AsyncMock) as mock:
            mock.return_value = {"stdout": "ok", "exit_code": 0}
            result = await executor.execute_single(
                "execute_shell",
                {"command": "ls -la"}
            )
            assert result.blocked is False
            assert result.tool_result.success is True

    @pytest.mark.asyncio
    async def test_safety_disabled(self):
        executor = ToolCallExecutor(enable_safety_check=False)
        with patch("src.core.actuator.tool_executor.dispatch_tool", new_callable=AsyncMock) as mock:
            mock.return_value = {"stdout": "ok", "exit_code": 0}
            result = await executor.execute_single(
                "execute_shell",
                {"command": "rm -rf /"}
            )
            # 安全检查关闭时不应被拦截
            assert result.blocked is False


# ─────────────────────────────────────────────
# 4. 单个工具执行
# ─────────────────────────────────────────────

class TestSingleExecution:
    """测试单个工具执行"""

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor):
        with patch("src.core.actuator.tool_executor.dispatch_tool", new_callable=AsyncMock) as mock:
            mock.return_value = {"content": "file content here"}
            result = await executor.execute_single("read_file", {"path": "/tmp/test.txt"})

            assert result.tool_result.success is True
            assert "file content here" in result.tool_result.content
            assert result.blocked is False

    @pytest.mark.asyncio
    async def test_error_execution(self, executor):
        with patch("src.core.actuator.tool_executor.dispatch_tool", new_callable=AsyncMock) as mock:
            mock.return_value = {"error": "File not found"}
            result = await executor.execute_single("read_file", {"path": "/nonexistent"})

            assert result.tool_result.success is False
            assert "File not found" in result.tool_result.content

    @pytest.mark.asyncio
    async def test_exception_handling(self, executor):
        with patch("src.core.actuator.tool_executor.dispatch_tool", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("Something went wrong")
            result = await executor.execute_single("read_file", {"path": "/tmp/test.txt"})

            assert result.tool_result.success is False
            assert "ERROR" in result.tool_result.content


# ─────────────────────────────────────────────
# 5. 批量执行
# ─────────────────────────────────────────────

class TestBatchExecution:
    """测试批量工具调用执行"""

    @pytest.mark.asyncio
    async def test_batch_from_response(self, executor):
        response = {
            "choices": [{
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "/tmp/a.txt"}'
                            }
                        },
                        {
                            "id": "call_2",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "/tmp/b.txt"}'
                            }
                        }
                    ]
                }
            }]
        }

        with patch("src.core.actuator.tool_executor.dispatch_tool", new_callable=AsyncMock) as mock:
            mock.return_value = {"content": "ok"}
            batch = await executor.execute_from_response(response)

            assert batch.has_results
            assert len(batch.results) == 2
            assert batch.all_success
            assert batch.blocked_count == 0
            assert batch.error_count == 0

    @pytest.mark.asyncio
    async def test_batch_with_errors(self, executor):
        response = {
            "choices": [{
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "/tmp/a.txt"}'
                            }
                        },
                        {
                            "id": "call_2",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "/tmp/b.txt"}'
                            }
                        }
                    ]
                }
            }]
        }

        call_count = 0
        async def mock_dispatch(name, args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"content": "ok"}
            return {"error": "not found"}

        with patch("src.core.actuator.tool_executor.dispatch_tool", side_effect=mock_dispatch):
            batch = await executor.execute_from_response(response)

            assert len(batch.results) == 2
            assert batch.all_success is False
            assert batch.error_count == 1

    @pytest.mark.asyncio
    async def test_empty_response(self, executor):
        response = {"choices": [{"message": {"content": "no tools"}}]}
        batch = await executor.execute_from_response(response)
        assert not batch.has_results
        assert batch.all_success


# ─────────────────────────────────────────────
# 6. 结果格式化
# ─────────────────────────────────────────────

class TestResultFormatting:
    """测试结果格式化"""

    def test_openai_format(self, executor):
        batch = BatchExecutionResult()
        batch.results.append(ExecutionResult(
            tool_call=ToolCall(id="call_1", name="read_file", arguments={}),
            tool_result=ToolResult(
                tool_call_id="call_1",
                name="read_file",
                content="file content",
                success=True,
            ),
        ))

        messages = executor.format_for_model(batch, target_format="openai")
        assert len(messages) == 1
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_1"
        assert messages[0]["content"] == "file content"

    def test_anthropic_format(self, executor):
        batch = BatchExecutionResult()
        batch.results.append(ExecutionResult(
            tool_call=ToolCall(id="call_1", name="read_file", arguments={}),
            tool_result=ToolResult(
                tool_call_id="call_1",
                name="read_file",
                content="file content",
                success=True,
            ),
        ))

        messages = executor.format_for_model(batch, target_format="anthropic")
        assert len(messages) == 1
        assert messages[0]["type"] == "tool_result"
        assert messages[0]["tool_use_id"] == "call_1"


# ─────────────────────────────────────────────
# 7. 全局单例
# ─────────────────────────────────────────────

class TestGlobalExecutor:
    """测试全局执行器"""

    def test_get_executor_singleton(self):
        e1 = get_tool_executor()
        e2 = get_tool_executor()
        assert e1 is e2

    def test_reset_executor(self):
        e1 = get_tool_executor()
        reset_tool_executor()
        e2 = get_tool_executor()
        assert e1 is not e2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
