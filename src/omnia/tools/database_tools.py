"""
database_tools.py — 数据库查询工具

提供：query_database（执行 SQL 查询）
支持：SQLite, MySQL, PostgreSQL
适配国内环境
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List


class DatabaseTools:
    """数据库查询工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_database",
                    "description": "执行 SQL 查询并返回结果。支持 SQLite、MySQL、PostgreSQL。仅允许 SELECT 查询（只读）。UPDATE/INSERT/DELETE 需使用 execute_database。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL 查询语句"
                            },
                            "db_type": {
                                "type": "string",
                                "enum": ["sqlite", "mysql", "postgresql"],
                                "description": "数据库类型",
                                "default": "sqlite"
                            },
                            "db_path": {
                                "type": "string",
                                "description": "SQLite 数据库文件路径（db_type=sqlite 时必填）"
                            },
                            "host": {
                                "type": "string",
                                "description": "数据库主机地址（MySQL/PostgreSQL）",
                                "default": "localhost"
                            },
                            "port": {
                                "type": "integer",
                                "description": "数据库端口（MySQL默认3306，PostgreSQL默认5432）"
                            },
                            "database": {
                                "type": "string",
                                "description": "数据库名（MySQL/PostgreSQL）"
                            },
                            "user": {
                                "type": "string",
                                "description": "用户名（MySQL/PostgreSQL）"
                            },
                            "password": {
                                "type": "string",
                                "description": "密码（MySQL/PostgreSQL）"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "最大返回行数，默认 100",
                                "default": 100
                            }
                        },
                        "required": ["sql"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_database",
                    "description": "执行 SQL 写入操作（INSERT/UPDATE/DELETE/CREATE）。需要提供确认标记 confirm=true。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL 语句"
                            },
                            "db_type": {
                                "type": "string",
                                "enum": ["sqlite", "mysql", "postgresql"],
                                "description": "数据库类型",
                                "default": "sqlite"
                            },
                            "db_path": {
                                "type": "string",
                                "description": "SQLite 数据库文件路径"
                            },
                            "host": {
                                "type": "string",
                                "description": "主机地址",
                                "default": "localhost"
                            },
                            "port": {
                                "type": "integer",
                                "description": "端口"
                            },
                            "database": {
                                "type": "string",
                                "description": "数据库名"
                            },
                            "user": {
                                "type": "string",
                                "description": "用户名"
                            },
                            "password": {
                                "type": "string",
                                "description": "密码"
                            },
                            "confirm": {
                                "type": "boolean",
                                "description": "确认执行写入操作，必须为 true"
                            }
                        },
                        "required": ["sql", "confirm"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tables",
                    "description": "列出数据库中的所有表。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "db_type": {
                                "type": "string",
                                "enum": ["sqlite", "mysql", "postgresql"],
                                "description": "数据库类型",
                                "default": "sqlite"
                            },
                            "db_path": {
                                "type": "string",
                                "description": "SQLite 数据库文件路径"
                            },
                            "host": {
                                "type": "string",
                                "description": "主机地址",
                                "default": "localhost"
                            },
                            "port": {
                                "type": "integer",
                                "description": "端口"
                            },
                            "database": {
                                "type": "string",
                                "description": "数据库名"
                            },
                            "user": {
                                "type": "string",
                                "description": "用户名"
                            },
                            "password": {
                                "type": "string",
                                "description": "密码"
                            }
                        },
                        "required": []
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "query_database":
            return await DatabaseTools._query_database(**args)
        elif name == "execute_database":
            return await DatabaseTools._execute_database(**args)
        elif name == "list_tables":
            return await DatabaseTools._list_tables(**args)
        return {"error": f"未知的数据库工具: {name}"}

    @staticmethod
    def _get_sqlite_conn(db_path: str):
        """获取 SQLite 连接"""
        import sqlite3
        p = Path(db_path)
        if not p.exists():
            raise FileNotFoundError(f"SQLite 数据库不存在: {db_path}")
        return sqlite3.connect(str(p))

    @staticmethod
    def _get_mysql_conn(host: str, port: int, database: str, user: str, password: str):
        """获取 MySQL 连接"""
        try:
            import pymysql
        except ImportError:
            raise ImportError("MySQL 需要安装 pymysql: pip install pymysql")
        return pymysql.connect(
            host=host, port=port or 3306,
            database=database, user=user, password=password,
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        )

    @staticmethod
    def _get_pg_conn(host: str, port: int, database: str, user: str, password: str):
        """获取 PostgreSQL 连接"""
        try:
            import psycopg2
        except ImportError:
            raise ImportError("PostgreSQL 需要安装 psycopg2: pip install psycopg2-binary")
        return psycopg2.connect(
            host=host, port=port or 5432,
            dbname=database, user=user, password=password,
        )

    @staticmethod
    def _get_connection(args: Dict[str, Any]):
        """根据 db_type 获取数据库连接"""
        db_type = args.get("db_type", "sqlite")
        if db_type == "sqlite":
            db_path = args.get("db_path", "")
            if not db_path:
                raise ValueError("SQLite 需要提供 db_path")
            return DatabaseTools._get_sqlite_conn(db_path)
        elif db_type == "mysql":
            return DatabaseTools._get_mysql_conn(
                args.get("host", "localhost"), args.get("port", 3306),
                args.get("database", ""), args.get("user", ""), args.get("password", "")
            )
        elif db_type == "postgresql":
            return DatabaseTools._get_pg_conn(
                args.get("host", "localhost"), args.get("port", 5432),
                args.get("database", ""), args.get("user", ""), args.get("password", "")
            )
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    @staticmethod
    async def _query_database(sql: str, limit: int = 100, **kwargs) -> Dict[str, Any]:
        """执行 SELECT 查询"""
        try:
            conn = DatabaseTools._get_connection(kwargs)
            cursor = conn.cursor()
            cursor.execute(sql)

            # 获取列名
            if hasattr(cursor, "description") and cursor.description:
                columns = [desc[0] for desc in cursor.description]
            else:
                columns = []

            rows = cursor.fetchmany(limit)
            conn.close()

            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": len(rows) == limit,
            }
        except Exception as e:
            return {"error": f"查询失败: {str(e)}", "success": False}

    @staticmethod
    async def _execute_database(sql: str, confirm: bool = False, **kwargs) -> Dict[str, Any]:
        """执行写入操作"""
        if not confirm:
            return {"error": "写入操作需要设置 confirm=true", "success": False}

        try:
            conn = DatabaseTools._get_connection(kwargs)
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return {
                "success": True,
                "affected_rows": affected,
            }
        except Exception as e:
            return {"error": f"执行失败: {str(e)}", "success": False}

    @staticmethod
    async def _list_tables(**kwargs) -> Dict[str, Any]:
        """列出所有表"""
        db_type = kwargs.get("db_type", "sqlite")
        if db_type == "sqlite":
            sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        elif db_type == "mysql":
            sql = "SHOW TABLES"
        elif db_type == "postgresql":
            sql = "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        else:
            return {"error": f"不支持的数据库类型: {db_type}"}

        return await DatabaseTools._query_database(sql, **kwargs)
