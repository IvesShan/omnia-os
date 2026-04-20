#!/usr/bin/env python3
"""
Query Memory Palace - Standalone tool for OpenClaw tool execution.

This script is designed to be called by OpenClaw Gateway as a tool.
It properly sets up the Python path and imports the necessary modules.

Usage:
    python3 scripts/query_memory_tool.py '{"query": "无限", "layer": "facts"}'
"""

import sys
import json
import sqlite3
from pathlib import Path

# Add src to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import config to get MEMORY_PALACE_DB
from core.config import MEMORY_PALACE_DB


def query_memory(query: str, layer: str = "all") -> dict:
    """Query Memory Palace for stored information."""
    try:
        if not MEMORY_PALACE_DB.exists():
            return {"error": "Memory Palace database not found", "db_path": str(MEMORY_PALACE_DB)}
        
        conn = sqlite3.connect(str(MEMORY_PALACE_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        results = []
        search_pattern = f"%{query}%"
        
        # Search in facts table
        if layer in ("all", "facts"):
            cursor.execute(
                "SELECT id, category, key, value, created_at FROM facts WHERE value LIKE ? OR key LIKE ? ORDER BY id DESC LIMIT 10",
                (search_pattern, search_pattern)
            )
            for row in cursor.fetchall():
                results.append({
                    "layer": "facts",
                    "id": row["id"],
                    "category": row["category"],
                    "key": row["key"],
                    "value": row["value"],
                    "created_at": row["created_at"]
                })
        
        # Search in relations table
        if layer in ("all", "relations"):
            cursor.execute(
                "SELECT id, source, relation, target, context, created_at FROM relations WHERE source LIKE ? OR target LIKE ? OR context LIKE ? ORDER BY id DESC LIMIT 10",
                (search_pattern, search_pattern, search_pattern)
            )
            for row in cursor.fetchall():
                results.append({
                    "layer": "relations",
                    "id": row["id"],
                    "source": row["source"],
                    "relation": row["relation"],
                    "target": row["target"],
                    "context": row["context"],
                    "created_at": row["created_at"]
                })
        
        # Search in habits table
        if layer in ("all", "habits"):
            cursor.execute(
                "SELECT id, habit_name, description, frequency, last_triggered, created_at FROM habits WHERE habit_name LIKE ? OR description LIKE ? ORDER BY id DESC LIMIT 10",
                (search_pattern, search_pattern)
            )
            for row in cursor.fetchall():
                results.append({
                    "layer": "habits",
                    "id": row["id"],
                    "habit_name": row["habit_name"],
                    "description": row["description"],
                    "frequency": row["frequency"],
                    "last_triggered": row["last_triggered"],
                    "created_at": row["created_at"]
                })
        
        # Search in timeline table
        if layer in ("all", "timeline"):
            cursor.execute(
                "SELECT id, event_type, description, timestamp, metadata FROM timeline WHERE description LIKE ? OR event_type LIKE ? ORDER BY timestamp DESC LIMIT 20",
                (search_pattern, search_pattern)
            )
            for row in cursor.fetchall():
                results.append({
                    "layer": "timeline",
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "description": row["description"],
                    "timestamp": row["timestamp"],
                    "metadata": row["metadata"]
                })
        
        conn.close()
        
        return {
            "query": query,
            "layer": layer,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: query_memory_tool.py '{\"query\": \"...\", \"layer\": \"...\"}'"}))
        sys.exit(1)
    
    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments"}))
        sys.exit(1)
    
    query = args.get("query", "")
    layer = args.get("layer", "all")
    
    result = query_memory(query, layer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
