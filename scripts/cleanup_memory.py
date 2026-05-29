#!/usr/bin/env python3
"""Memory Palace Cleanup Script - Step A"""

import sqlite3
import os

DB_PATH = '/home/shan/.omnia/memory_palace.db'

def cleanup():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("MEMORY PALACE CLEANUP")
    print("=" * 60)

    # ========== STEP 1: Remove duplicate relations ==========
    print("\n[STEP 1] Removing duplicate relations...")

    cursor.execute("""
        SELECT COUNT(*) FROM relations WHERE status='active'
    """)
    before_count = cursor.fetchone()[0]
    print(f"  Active relations before: {before_count}")

    # Count duplicates
    cursor.execute("""
        SELECT SUM(cnt - 1) FROM (
            SELECT subject, predicate, object, COUNT(*) as cnt
            FROM relations WHERE status='active'
            GROUP BY subject, predicate, object
            HAVING cnt > 1
        )
    """)
    dup_count = cursor.fetchone()[0] or 0
    print(f"  Duplicate rows to remove: {dup_count}")

    # Delete duplicates (keep lowest id)
    cursor.execute("""
        DELETE FROM relations WHERE id NOT IN (
            SELECT MIN(id) FROM relations WHERE status='active'
            GROUP BY subject, predicate, object
        ) AND status='active'
    """)
    deleted = cursor.rowcount
    print(f"  Deleted: {deleted} duplicate rows")

    cursor.execute("SELECT COUNT(*) FROM relations WHERE status='active'")
    after_count = cursor.fetchone()[0]
    print(f"  Active relations after: {after_count}")

    # ========== STEP 2: Clean bad/junk facts ==========
    print("\n[STEP 2] Cleaning junk facts...")

    # Find junk facts
    junk_conditions = [
        "value LIKE '%Sender (untrusted metadata)%'",
        "value LIKE '%```json%'",
        "value LIKE '%让我先禁用 Gateway%'",
        "value LIKE '%要我帮你复制%'",
        "key LIKE '%**%'",
        "category = 'test'",
        "category = 'legacy_core'",
        "category = 'legacy_daily'",
    ]

    junk_ids = []
    for cond in junk_conditions:
        cursor.execute(f"SELECT id, category, key FROM facts WHERE status='active' AND {cond}")
        rows = cursor.fetchall()
        for row in rows:
            if row[0] not in junk_ids:
                junk_ids.append(row[0])

    print(f"  Junk facts found: {len(junk_ids)}")

    # Soft-delete junk facts
    for fid in junk_ids:
        cursor.execute("UPDATE facts SET status='deleted' WHERE id=?", (fid,))

    print(f"  Soft-deleted: {len(junk_ids)} facts")

    # Show remaining good facts
    cursor.execute("SELECT COUNT(*) FROM facts WHERE status='active'")
    remaining = cursor.fetchone()[0]
    print(f"  Remaining active facts: {remaining}")

    # ========== STEP 3: Clean bad relations ==========
    print("\n[STEP 3] Cleaning junk relations...")

    bad_rel_conditions = [
        "predicate = '正在进行'",
        "predicate = '正在做'",
        "predicate = '经营'",  # These are overloaded with bad data
    ]

    bad_ids = []
    for cond in bad_rel_conditions:
        cursor.execute(f"SELECT id FROM relations WHERE status='active' AND {cond}")
        rows = cursor.fetchall()
        for row in rows:
            if row[0] not in bad_ids:
                bad_ids.append(row[0])

    print(f"  Junk relations found: {len(bad_ids)}")

    for rid in bad_ids:
        cursor.execute("UPDATE relations SET status='deleted' WHERE id=?", (rid,))

    cursor.execute("SELECT COUNT(*) FROM relations WHERE status='active'")
    final_rels = cursor.fetchone()[0]
    print(f"  Remaining active relations: {final_rels}")

    # ========== STEP 4: Summary ==========
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)

    cursor.execute("SELECT COUNT(*) FROM facts WHERE status='active'")
    f_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM relations WHERE status='active'")
    r_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM habits")
    h_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM timeline")
    t_count = cursor.fetchone()[0]

    print(f"  Facts:      {f_count}")
    print(f"  Relations:  {r_count}")
    print(f"  Habits:     {h_count}")
    print(f"  Timeline:   {t_count}")

    conn.commit()
    conn.close()
    print("\nDone!")

if __name__ == '__main__':
    cleanup()
