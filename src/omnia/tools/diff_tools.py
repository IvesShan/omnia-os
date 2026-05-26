"""
diff_tools.py — 文件对比工具

提供：diff_file（对比两个文件的差异）
"""

import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional


class DiffTools:
    """文件对比工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "diff_file",
                    "description": "对比两个文件或两段文本的差异，返回统一格式的 diff 输出。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_a": {
                                "type": "string",
                                "description": "第一个文件路径（或省略以直接比较 text_a/text_b）"
                            },
                            "file_b": {
                                "type": "string",
                                "description": "第二个文件路径"
                            },
                            "text_a": {
                                "type": "string",
                                "description": "第一段文本内容（与 file_a 二选一）"
                            },
                            "text_b": {
                                "type": "string",
                                "description": "第二段文本内容（与 file_b 二选一）"
                            },
                            "context_lines": {
                                "type": "integer",
                                "description": "差异上下文行数，默认 3",
                                "default": 3
                            },
                            "ignore_whitespace": {
                                "type": "boolean",
                                "description": "是否忽略空白差异，默认 false",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "diff_stat",
                    "description": "获取两个文件的差异统计信息（修改行数、添加行数、删除行数）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_a": {
                                "type": "string",
                                "description": "第一个文件路径"
                            },
                            "file_b": {
                                "type": "string",
                                "description": "第二个文件路径"
                            }
                        },
                        "required": ["file_a", "file_b"]
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "diff_file":
            return await DiffTools._diff_file(**args)
        elif name == "diff_stat":
            return await DiffTools._diff_stat(**args)
        return {"error": f"未知的 diff 工具: {name}"}

    @staticmethod
    async def _diff_file(
        file_a: str = "",
        file_b: str = "",
        text_a: str = "",
        text_b: str = "",
        context_lines: int = 3,
        ignore_whitespace: bool = False,
    ) -> Dict[str, Any]:
        """对比差异"""
        try:
            # 获取内容
            if file_a and file_b:
                p_a = Path(file_a)
                p_b = Path(file_b)
                if not p_a.exists():
                    return {"error": f"文件不存在: {file_a}"}
                if not p_b.exists():
                    return {"error": f"文件不存在: {file_b}"}
                lines_a = p_a.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                lines_b = p_b.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                label_a = file_a
                label_b = file_b
            elif text_a is not None and text_b is not None:
                lines_a = (text_a + "\n").splitlines(keepends=True)
                lines_b = (text_b + "\n").splitlines(keepends=True)
                label_a = "text_a"
                label_b = "text_b"
            else:
                return {"error": "请提供 file_a/file_b 或 text_a/text_b 进行对比"}

            # 忽略空白
            if ignore_whitespace:
                lines_a = [l.strip() + "\n" for l in "".join(lines_a).splitlines()]
                lines_b = [l.strip() + "\n" for l in "".join(lines_b).splitlines()]

            # 生成 unified diff
            diff = list(difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=label_a,
                tofile=label_b,
                n=context_lines,
            ))

            diff_text = "".join(diff)

            if not diff_text:
                return {
                    "identical": True,
                    "message": "两个文件/文本完全相同",
                }

            # 截断过长 diff
            truncated = False
            if len(diff_text) > 30_000:
                diff_text = diff_text[:30_000] + "\n\n[...diff 已截断，差异过大...]"
                truncated = True

            return {
                "identical": False,
                "diff": diff_text,
                "lines_a": len(lines_a),
                "lines_b": len(lines_b),
                "truncated": truncated,
            }
        except Exception as e:
            return {"error": f"对比失败: {str(e)}"}

    @staticmethod
    async def _diff_stat(file_a: str, file_b: str) -> Dict[str, Any]:
        """差异统计"""
        try:
            p_a = Path(file_a)
            p_b = Path(file_b)
            if not p_a.exists():
                return {"error": f"文件不存在: {file_a}"}
            if not p_b.exists():
                return {"error": f"文件不存在: {file_b}"}

            lines_a = p_a.read_text(encoding="utf-8", errors="replace").splitlines()
            lines_b = p_b.read_text(encoding="utf-8", errors="replace").splitlines()

            diff = list(difflib.unified_diff(lines_a, lines_b, lineterm=""))

            added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
            removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

            return {
                "file_a": file_a,
                "file_b": file_b,
                "lines_a": len(lines_a),
                "lines_b": len(lines_b),
                "added": added,
                "removed": removed,
                "changed": added + removed,
                "similarity": round(1 - (added + removed) / max(len(lines_a), len(lines_b), 1), 4),
            }
        except Exception as e:
            return {"error": f"统计失败: {str(e)}"}
