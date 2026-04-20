#!/usr/bin/env python3
"""Query Memory Palace - Standalone tool for memory queries.

Usage:
    python scripts/query_memory.py "无限" --layer facts
    python scripts/query_memory.py "原点" --layer all
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        return {"query": query, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Query Omnia's Memory Palace")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--layer", default="all", choices=["all", "facts", "relations", "habits", "timeline"], help="Memory layer to search")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    result = query_memory(args.query, args.layer)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            sys.exit(1)
        
        print(f"✅ Found {result['count']} memories for '{result['query']}' (layer: {result['layer']})")
        print()
        
        for r in result["results"]:
            if r["layer"] == "facts":
                print(f"  [{r['category']}] {r['key']}: {r['value'][:80]}...")
            elif r["layer"] == "relations":
                print(f"  {r['source']} --[{r['relation']}]--> {r['target']}")
            elif r["layer"] == "habits":
                print(f"  🔄 {r['habit_name']}: {r['description'][:60]}...")
            elif r["layer"] == "timeline":
                print(f"  📅 [{r['event_type']}] {r['description'][:60]}...")


if __name__ == "__main__":
    main()
