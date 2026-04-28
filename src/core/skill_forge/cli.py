#!/usr/bin/env python3
"""Skill Forge CLI — Detect recurring patterns and auto-generate skills."""
from core.logging_config import get_logger

logger = get_logger(__name__)

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.skill_forge.detector import PatternDetector
from core.skill_forge.generator import generate_skill
from core.skill_forge.vetter import vet_skill


def main():
    parser = argparse.ArgumentParser(description="Skill Forge — Auto-generate skills from patterns")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # detect
    detect = subparsers.add_parser("detect", help="Detect recurring patterns")
    detect.add_argument("--days", type=int, default=14, help="Lookback days")
    detect.add_argument("--min-evidence", type=int, default=2, help="Minimum evidence count")

    # generate
    generate = subparsers.add_parser("generate", help="Generate skill from pattern")
    generate.add_argument("pattern_id", help="Pattern ID to generate from")

    # run (detect + generate + vet)
    run = subparsers.add_parser("run", help="Full pipeline: detect → generate → vet")
    run.add_argument("--days", type=int, default=14)
    run.add_argument("--min-evidence", type=int, default=3)

    args = parser.parse_args()

    if args.command == "detect":
        cmd_detect(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "run":
        cmd_run(args)


def cmd_detect(args):
    logger.info("=== Skill Forge Pattern Detection ===\n")
    pd = PatternDetector(
        memory_dir=str(PROJECT_ROOT.parent / "memory"),
        lookback_days=args.days,
        min_evidence=args.min_evidence
    )
    print(f"扫描最近 {pd.lookback_days} 天的记忆文件...")
    files = pd._list_files()
    print(f"找到 {len(files)} 个文件\n")
    patterns = pd.detect()
    print(f"检测到 {len(patterns)} 个模式:\n")
    for p in patterns:
        print(f"[{p.pattern_id}]")
        print(f"  名称: {p.pattern_name}")
        print(f"  频率: {p.frequency} 次")
        print(f"  置信度: {p.confidence:.2f}")
        print(f"  建议技能: {p.suggested_skill_name}")
        print()
    logger.info("✅ 检测完成!")


def cmd_generate(args):
    print(f"=== Generating skill for {args.pattern_id} ===")
    # Implementation placeholder
    print("TODO: Generate skill markdown")


def cmd_run(args):
    logger.info("=== Skill Forge Full Pipeline ===\n")
    pd = PatternDetector(
        memory_dir=str(PROJECT_ROOT.parent / "memory"),
        lookback_days=args.days,
        min_evidence=args.min_evidence
    )
    patterns = pd.detect()
    print(f"检测到 {len(patterns)} 个模式\n")
    for p in patterns:
        if p.confidence >= 0.7:
            print(f"🛠️  生成技能: {p.suggested_skill_name}")
    logger.info("\n✅ 流水线完成!")


if __name__ == "__main__":
    main()
