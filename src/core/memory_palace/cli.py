#!/usr/bin/env python3
"""Memory Palace CLI — The first command-line gateway into Omnia's memory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Allow running as script from repo root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from memory_palace import MemoryPalace
# 使用统一的配置路径
from core.config import MEMORY_PALACE_DB


def _mp() -> MemoryPalace:
    mp = MemoryPalace(MEMORY_PALACE_DB)
    mp.initialize()
    return mp


def cmd_fact_add(args):
    mp = _mp()
    mp.remember_fact(args.category, args.key, args.value, args.source, args.strength)
    print(f"[OK] Fact remembered: [{args.category}] {args.key}")


def cmd_fact_list(args):
    mp = _mp()
    results = mp.recall_facts(category=args.category, key=args.key)
    if not results:
        print("No facts found.")
        return
    for r in results:
        print(f"#{r['id']} [{r['category']}] {r['key']} = {r['value']} (strength {r['strength']:.2f})")


def cmd_relate(args):
    mp = _mp()
    mp.relate(args.subject, args.predicate, args.object, args.context, args.strength)
    print(f"[OK] Relation created: {args.subject} --[{args.predicate}]--> {args.object}")


def cmd_relation_list(args):
    mp = _mp()
    results = mp.recall_relations(args.entity)
    if not results:
        print("No relations found.")
        return
    for r in results:
        print(f"#{r['id']} {r['subject']} --[{r['predicate']}]--> {r['object']} | {r['context']}")


def cmd_habit_add(args):
    mp = _mp()
    mp.observe_habit(args.domain, args.pattern, args.evidence, args.certainty)
    print(f"[OK] Habit observed: [{args.domain}] {args.pattern}")


def cmd_habit_list(args):
    mp = _mp()
    results = mp.recall_habits(domain=args.domain)
    if not results:
        print("No habits found.")
        return
    for r in results:
        print(f"#{r['id']} [{r['domain']}] {r['pattern']} (certainty {r['certainty']:.2f}, last {r['last_observed_at']})")


def cmd_event_add(args):
    mp = _mp()
    tags = args.tags.split(",") if args.tags else []
    eid = mp.record_event(
        event_date=date.fromisoformat(args.date),
        event_type=args.type,
        title=args.title,
        description=args.description,
        tags=tags,
        session_key=args.session,
    )
    print(f"[OK] Event recorded with ID: {eid}")


def cmd_event_search(args):
    mp = _mp()
    results = mp.search_timeline(args.query, limit=args.limit)
    if not results:
        print("No events found.")
        return
    for r in results:
        print(f"#{r['id']} [{r['event_date']}] ({r['event_type']}) {r['title']} | tags: {r['tags']}")


def cmd_search(args):
    mp = _mp()
    results = mp.search(args.query, limit=args.limit)
    if not results:
        print("No results found across any layer.")
        return
    for res in results:
        print(f"[{res.layer.upper():8}] #{res.rowid:3} | {res.snippet}")


def main():
    parser = argparse.ArgumentParser(description="Memory Palace CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fact
    fact = subparsers.add_parser("fact", help="Manage facts")
    fact_sub = fact.add_subparsers(dest="subcommand", required=True)
    fa = fact_sub.add_parser("add", help="Add a fact")
    fa.add_argument("category")
    fa.add_argument("key")
    fa.add_argument("value")
    fa.add_argument("--source", default="cli")
    fa.add_argument("--strength", type=float, default=1.0)
    fl = fact_sub.add_parser("list", help="List facts")
    fl.add_argument("--category", default=None)
    fl.add_argument("--key", default=None)

    # relation
    relation = subparsers.add_parser("relation", help="Manage relations")
    rel_sub = relation.add_subparsers(dest="subcommand", required=True)
    ra = rel_sub.add_parser("add", help="Add a relation")
    ra.add_argument("subject")
    ra.add_argument("predicate")
    ra.add_argument("object")
    ra.add_argument("--context", default="")
    ra.add_argument("--strength", type=float, default=0.5)
    rl = rel_sub.add_parser("list", help="List relations")
    rl.add_argument("--entity", default=None)

    # habit
    habit = subparsers.add_parser("habit", help="Manage habits")
    habit_sub = habit.add_subparsers(dest="subcommand", required=True)
    ha = habit_sub.add_parser("add", help="Add a habit")
    ha.add_argument("domain")
    ha.add_argument("pattern")
    ha.add_argument("--evidence", default="")
    ha.add_argument("--certainty", type=float, default=0.5)
    hl = habit_sub.add_parser("list", help="List habits")
    hl.add_argument("--domain", default=None)

    # event
    event = subparsers.add_parser("event", help="Manage timeline events")
    event_sub = event.add_subparsers(dest="subcommand", required=True)
    ea = event_sub.add_parser("add", help="Add an event")
    ea.add_argument("--date", required=True, help="YYYY-MM-DD")
    ea.add_argument("--type", required=True, help="Event type")
    ea.add_argument("--title", required=True)
    ea.add_argument("--description", default="")
    ea.add_argument("--tags", default="")
    ea.add_argument("--session", default=None)
    es = event_sub.add_parser("search", help="Search events")
    es.add_argument("query")
    es.add_argument("--limit", type=int, default=10)

    # search
    search = subparsers.add_parser("search", help="Search all layers")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()

    # Dispatch
    if args.command == "fact":
        if args.subcommand == "add":
            cmd_fact_add(args)
        elif args.subcommand == "list":
            cmd_fact_list(args)
    elif args.command == "relation":
        if args.subcommand == "add":
            cmd_relate(args)
        elif args.subcommand == "list":
            cmd_relation_list(args)
    elif args.command == "habit":
        if args.subcommand == "add":
            cmd_habit_add(args)
        elif args.subcommand == "list":
            cmd_habit_list(args)
    elif args.command == "event":
        if args.subcommand == "add":
            cmd_event_add(args)
        elif args.subcommand == "search":
            cmd_event_search(args)
    elif args.command == "search":
        cmd_search(args)


if __name__ == "__main__":
    main()
