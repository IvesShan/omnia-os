"""
memory_tools.py — 记忆工具实现

提供：query_memory, save_memory, memory_stats, forget_memory
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class MemoryTools:
    """记忆系统工具集"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_memory",
                    "description": "查询 Omnia 记忆宫殿。搜索已存储的事实、关系、习惯、时间线等记忆。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "要搜索的记忆关键词"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "保存一条新记忆到记忆宫殿。可以是事实、关系或习惯。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "记忆内容文本"
                            },
                            "layer": {
                                "type": "string",
                                "enum": ["facts", "relations", "habits", "timeline"],
                                "description": "记忆层：facts(事实), relations(关系), habits(习惯), timeline(时间线)"
                            }
                        },
                        "required": ["content", "layer"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_stats",
                    "description": "获取记忆宫殿统计信息：各层的记忆数量。",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
        ]

    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行记忆工具调用"""
        
        if name == "query_memory":
            return await self._query_memory(args.get("query", ""))
        elif name == "save_memory":
            return await self._save_memory(
                args.get("content", ""),
                args.get("layer", "facts")
            )
        elif name == "memory_stats":
            return await self._memory_stats()
        else:
            return {"error": f"Unknown memory tool: {name}"}

    async def _query_memory(self, query: str) -> Dict[str, Any]:
        """查询记忆"""
        try:
            from core.memory_palace.memory_palace import MemoryPalace
            from src.omnia.config import settings
            
            mp = MemoryPalace(db_path=str(settings.memory_palace_db))
            mp.initialize()
            
            results = mp.search(query, top_k=5)
            
            return {
                "query": query,
                "results": results,
                "count": len(results)
            }
        except ImportError:
            return {"error": "记忆系统不可用: MemoryPalace 模块未找到", "results": []}
        except Exception as e:
            return {"error": f"查询失败: {str(e)}", "results": []}

    async def _save_memory(self, content: str, layer: str = "facts") -> Dict[str, Any]:
        """保存记忆"""
        valid_layers = ["facts", "relations", "habits", "timeline"]
        if layer not in valid_layers:
            return {"error": f"无效的记忆层: {layer}，可选: {valid_layers}"}
        
        try:
            from core.memory_palace.memory_palace import MemoryPalace
            from src.omnia.config import settings
            
            mp = MemoryPalace(db_path=str(settings.memory_palace_db))
            mp.initialize()
            
            if layer == "facts":
                mp.save_fact(content)
            elif layer == "relations":
                mp.save_relation(content)
            elif layer == "habits":
                mp.save_habit(content)
            elif layer == "timeline":
                mp.save_timeline(content)
            
            return {"ok": True, "layer": layer, "content": content}
        except ImportError:
            return {"error": "记忆系统不可用", "ok": False}
        except Exception as e:
            return {"error": f"保存失败: {str(e)}", "ok": False}

    async def _memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        try:
            import sqlite3
            from src.omnia.config import settings
            
            counts = {}
            if settings.memory_palace_db.exists():
                with sqlite3.connect(str(settings.memory_palace_db)) as conn:
                    cursor = conn.cursor()
                    for table in ["facts", "relations", "habits", "timeline"]:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            counts[table] = cursor.fetchone()[0]
                        except sqlite3.OperationalError:
                            counts[table] = 0
            
            return {"counts": counts, "total": sum(counts.values())}
        except Exception as e:
            return {"error": f"统计失败: {str(e)}"}
