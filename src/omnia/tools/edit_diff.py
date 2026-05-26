"""
edit_diff.py — 精确代码编辑工具

提供：edit_file（精确文本替换）、apply_diff（补丁应用）
"""

import os
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional


class EditDiffTools:
    """精确编辑工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "精确编辑文件中的特定文本块。使用 old_text 定位，new_text 替换。必须确保 old_text 在文件中唯一存在，否则编辑会失败。适用于小范围、精确的修改。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件的绝对或相对路径"
                            },
                            "old_text": {
                                "type": "string",
                                "description": "要替换的原始文本（必须在文件中精确匹配）"
                            },
                            "new_text": {
                                "type": "string",
                                "description": "替换后的新文本"
                            }
                        },
                        "required": ["path", "old_text", "new_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_diff",
                    "description": "应用代码 diff（统一格式 / unified diff）。适用于多行修改、新增函数、删除代码块。比 edit_file 更适合大规模修改。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "目标文件路径"
                            },
                            "diff": {
                                "type": "string",
                                "description": "统一格式 diff 文本（--- old/+++ new 格式），或简化版：用 '<<<<<<< SEARCH' 标记搜索块，'=======' 分隔，'>>>>>>> REPLACE' 结束"
                            }
                        },
                        "required": ["path", "diff"]
                    }
                }
            }
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "edit_file":
            return await EditDiffTools._edit_file(
                path=args.get("path", ""),
                old_text=args.get("old_text", ""),
                new_text=args.get("new_text", "")
            )
        elif name == "apply_diff":
            return await EditDiffTools._apply_diff(
                path=args.get("path", ""),
                diff=args.get("diff", "")
            )
        else:
            return {"error": f"Unknown edit tool: {name}"}

    @staticmethod
    async def _edit_file(path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """精确文本替换编辑"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"error": f"文件不存在: {path}"}
            
            content = file_path.read_text(encoding="utf-8")
            
            # 检查 old_text 是否存在
            if old_text not in content:
                return {
                    "error": f"未找到匹配文本",
                    "hint": "old_text 在文件中不存在，请确认文本内容完全匹配（包括空格、换行）",
                    "file_preview": content[:500] + "..." if len(content) > 500 else content
                }
            
            # 检查唯一性
            count = content.count(old_text)
            if count > 1:
                return {
                    "error": f"匹配文本不唯一（找到 {count} 处）",
                    "hint": "请扩大 old_text 范围使其唯一，或使用 apply_diff 工具",
                    "locations": [
                        f"位置 {i+1}: ...{content[max(0, pos-50):pos+len(old_text)+50]}..."
                        for i, pos in enumerate([m.start() for m in re.finditer(re.escape(old_text), content)])[:3]
                    ]
                }
            
            # 执行替换
            new_content = content.replace(old_text, new_text, 1)
            
            # 写入文件
            file_path.write_text(new_content, encoding="utf-8")
            
            # 计算差异统计
            old_lines = old_text.count("\n") + 1
            new_lines = new_text.count("\n") + 1
            
            return {
                "success": True,
                "path": str(file_path),
                "lines_changed": f"-{old_lines}/+{new_lines}",
                "bytes_changed": f"-{len(old_text)}/+{len(new_text)}",
                "preview": new_content[max(0, content.find(old_text) - 100):content.find(old_text) + len(new_text) + 100]
            }
            
        except Exception as e:
            return {"error": f"编辑失败: {str(e)}"}

    @staticmethod
    async def _apply_diff(path: str, diff: str) -> Dict[str, Any]:
        """应用 diff 补丁"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"error": f"文件不存在: {path}"}
            
            content = file_path.read_text(encoding="utf-8")
            original_content = content
            
            # 解析 diff 格式
            # 支持两种格式：
            # 1. 简化版：<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE
            # 2. 统一 diff：--- old +++ new @@ ...
            
            if "<<<<<<< SEARCH" in diff:
                result = EditDiffTools._parse_search_replace(content, diff)
            elif "--- " in diff and "+++ " in diff:
                result = EditDiffTools._parse_unified_diff(content, diff)
            else:
                return {
                    "error": "无法识别 diff 格式",
                    "hint": "请使用 '<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE' 格式，或标准统一 diff 格式"
                }
            
            if "error" in result:
                return result
            
            # 写入修改后的内容
            file_path.write_text(result["content"], encoding="utf-8")
            
            return {
                "success": True,
                "path": str(file_path),
                "hunks_applied": result.get("hunks", 1),
                "lines_changed": result.get("lines_changed", "unknown"),
                "preview": result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"]
            }
            
        except Exception as e:
            return {"error": f"应用 diff 失败: {str(e)}"}

    @staticmethod
    def _parse_search_replace(content: str, diff: str) -> Dict[str, Any]:
        """解析 <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE 格式"""
        hunks = re.split(r'<<<<<<< SEARCH\n', diff)
        hunks = [h for h in hunks if h.strip()]
        
        new_content = content
        total_hunks = 0
        total_lines_changed = 0
        
        for hunk in hunks:
            parts = hunk.split("=======\n")
            if len(parts) != 2:
                return {"error": f"diff 格式错误：缺少 '=======' 分隔符"}
            
            search_text = parts[0]
            replace_parts = parts[1].split(">>>>>>> REPLACE")
            if len(replace_parts) != 1:
                # 可能有多个 hunks
                replace_text = replace_parts[0]
            else:
                replace_text = parts[1]
            
            # 移除尾部可能的 >>>>>>> REPLACE\n...
            replace_text = replace_text.split(">>>>>>> REPLACE")[0]
            
            # 确保搜索文本存在且唯一
            if search_text not in new_content:
                return {
                    "error": f"未找到匹配文本",
                    "search_snippet": search_text[:100] + "..." if len(search_text) > 100 else search_text,
                    "hint": "请确认 SEARCH 块的内容与文件中的内容完全匹配"
                }
            
            count = new_content.count(search_text)
            if count > 1:
                return {
                    "error": f"匹配文本不唯一（找到 {count} 处）",
                    "hint": "请扩大 SEARCH 块范围使其唯一"
                }
            
            new_content = new_content.replace(search_text, replace_text, 1)
            total_hunks += 1
            total_lines_changed += abs(replace_text.count("\n") - search_text.count("\n"))
        
        return {
            "content": new_content,
            "hunks": total_hunks,
            "lines_changed": f"±{total_lines_changed}"
        }

    @staticmethod
    def _parse_unified_diff(content: str, diff: str) -> Dict[str, Any]:
        """解析统一 diff 格式（简化版）"""
        lines = content.split("\n")
        diff_lines = diff.split("\n")
        
        # 找到 @@ 行
        hunks = []
        current_hunk = None
        
        for line in diff_lines:
            if line.startswith("@@"):
                # 解析 @@ -old_start,old_count +new_start,new_count @@
                m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                if m:
                    old_start = int(m.group(1))
                    new_start = int(m.group(2))
                    current_hunk = {
                        "old_start": old_start,
                        "new_start": new_start,
                        "old_lines": [],
                        "new_lines": []
                    }
                    hunks.append(current_hunk)
            elif current_hunk is not None:
                if line.startswith("-"):
                    current_hunk["old_lines"].append(line[1:])
                elif line.startswith("+"):
                    current_hunk["new_lines"].append(line[1:])
                elif line.startswith(" "):
                    current_hunk["old_lines"].append(line[1:])
                    current_hunk["new_lines"].append(line[1:])
        
        # 应用 hunks（从后往前避免行号偏移）
        new_lines = list(lines)
        
        for hunk in reversed(hunks):
            start = hunk["old_start"] - 1  # 转 0-index
            old_count = len(hunk["old_lines"])
            
            # 验证原内容
            actual = new_lines[start:start + old_count]
            expected = hunk["old_lines"]
            
            if actual != expected:
                return {
                    "error": f"diff 验证失败: 第 {hunk['old_start']} 行内容不匹配",
                    "expected": "\n".join(expected[:3]),
                    "actual": "\n".join(actual[:3])
                }
            
            # 替换
            new_lines[start:start + old_count] = hunk["new_lines"]
        
        return {
            "content": "\n".join(new_lines),
            "hunks": len(hunks),
            "lines_changed": f"±{sum(abs(len(h['new_lines']) - len(h['old_lines'])) for h in hunks)}"
        }
