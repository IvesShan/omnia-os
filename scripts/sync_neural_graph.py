#!/usr/bin/env python3
"""同步记忆宫殿数据到神经图谱

将 Memory Palace 的 relations 同步到 Neural Graph 的 nodes 和 edges。

用法:
    python scripts/sync_neural_graph.py [--dry-run]
"""

import sys
import sqlite3
import hashlib
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.config import MEMORY_PALACE_DB, NEURAL_GRAPH_DB


def init_neural_graph_db(conn):
    """初始化神经图谱数据库表"""
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS neural_nodes (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            canonical_name TEXT,
            aliases TEXT,
            properties TEXT,
            embedding BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS neural_edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            source_name TEXT,
            target_name TEXT,
            relation_type TEXT NOT NULL,
            weight REAL DEFAULT 0.5,
            evidence TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0,
            FOREIGN KEY (source_id) REFERENCES neural_nodes(id),
            FOREIGN KEY (target_id) REFERENCES neural_nodes(id)
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON neural_nodes(entity_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON neural_nodes(entity_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON neural_edges(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON neural_edges(target_id)")
    
    conn.commit()


def sync_relations_to_neural_graph(dry_run: bool = False):
    """同步 Memory Palace relations 到 Neural Graph"""
    
    print(f"[同步] Memory Palace: {MEMORY_PALACE_DB}")
    print(f"[同步] Neural Graph: {NEURAL_GRAPH_DB}")
    
    if not MEMORY_PALACE_DB.exists():
        print(f"[错误] Memory Palace 数据库不存在: {MEMORY_PALACE_DB}")
        return
    
    # 确保目录存在
    if not dry_run:
        NEURAL_GRAPH_DB.parent.mkdir(parents=True, exist_ok=True)
    
    # 连接数据库
    mp_conn = sqlite3.connect(str(MEMORY_PALACE_DB))
    ng_conn = sqlite3.connect(str(NEURAL_GRAPH_DB))
    
    # 初始化表结构
    if not dry_run:
        print(f"[信息] 初始化神经图谱表结构...")
        init_neural_graph_db(ng_conn)
    
    mp_cursor = mp_conn.cursor()
    ng_cursor = ng_conn.cursor()
    
    # 获取所有 relations
    mp_cursor.execute("SELECT id, subject, predicate, object, context, strength FROM relations")
    relations = mp_cursor.fetchall()
    
    print(f"[信息] 找到 {len(relations)} 条 relations")
    
    # 统计
    stats = {
        "nodes_added": 0,
        "nodes_skipped": 0,
        "edges_added": 0,
        "edges_skipped": 0,
    }
    
    for rel_id, subject, predicate, obj, context, strength in relations:
        # 为 subject 创建节点
        node_id_subj = f"entity_{hashlib.md5(subject.encode()).hexdigest()[:12]}"
        ng_cursor.execute(
            "SELECT id FROM neural_nodes WHERE entity_name = ?",
            (subject,)
        )
        if not ng_cursor.fetchone():
            if not dry_run:
                ng_cursor.execute("""
                    INSERT INTO neural_nodes (id, entity_type, entity_name, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (node_id_subj, _guess_entity_type(subject), subject))
            stats["nodes_added"] += 1
        else:
            stats["nodes_skipped"] += 1
        
        # 为 object 创建节点
        node_id_obj = f"entity_{hashlib.md5(obj.encode()).hexdigest()[:12]}"
        ng_cursor.execute(
            "SELECT id FROM neural_nodes WHERE entity_name = ?",
            (obj,)
        )
        if not ng_cursor.fetchone():
            if not dry_run:
                ng_cursor.execute("""
                    INSERT INTO neural_nodes (id, entity_type, entity_name, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (node_id_obj, _guess_entity_type(obj), obj))
            stats["nodes_added"] += 1
        else:
            stats["nodes_skipped"] += 1
        
        # 创建边
        edge_id = f"edge_{hashlib.md5(f'{subject}_{predicate}_{obj}'.encode()).hexdigest()[:12]}"
        ng_cursor.execute(
            "SELECT id FROM neural_edges WHERE source_name = ? AND target_name = ? AND relation_type = ?",
            (subject, obj, predicate)
        )
        if not ng_cursor.fetchone():
            if not dry_run:
                ng_cursor.execute("""
                    INSERT INTO neural_edges (id, source_id, target_id, source_name, target_name, relation_type, weight, evidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (edge_id, node_id_subj, node_id_obj, subject, obj, predicate, strength or 1.0, context))
            stats["edges_added"] += 1
        else:
            stats["edges_skipped"] += 1
    
    if not dry_run:
        ng_conn.commit()
    
    mp_conn.close()
    ng_conn.close()
    
    print(f"\n[完成] 同步结果:")
    print(f"  - 节点新增: {stats['nodes_added']}")
    print(f"  - 节点跳过: {stats['nodes_skipped']}")
    print(f"  - 边新增: {stats['edges_added']}")
    print(f"  - 边跳过: {stats['edges_skipped']}")
    
    if dry_run:
        print("\n[DRY RUN] 未实际写入数据")


def _guess_entity_type(name: str) -> str:
    """猜测实体类型"""
    name_lower = name.lower()
    
    # 项目名
    projects = ["omnia", "喵修匠", "懂机帝", "opc", "drone", "无人机"]
    if any(p in name_lower for p in projects):
        return "PROJECT"
    
    # 人名
    if name in ["原点", "用户", "无限"]:
        return "PERSON"
    
    # 概念
    concepts = ["概念", "api", "系统", "平台", "课程", "培训", "维修"]
    if any(c in name_lower for c in concepts):
        return "CONCEPT"
    
    # 公司
    companies = ["公司", "企业", "工作室"]
    if any(c in name_lower for c in companies):
        return "ORGANIZATION"
    
    return "ENTITY"


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("[DRY RUN] 模式运行，不会实际写入数据\n")
    
    sync_relations_to_neural_graph(dry_run)
