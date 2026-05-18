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
    generate.add_argument("--out-dir", default=".", help="Output directory for skill file")

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
    """生成技能文档"""
    print(f"=== Generating skill for {args.pattern_id} ===")
    
    # 1. 从检测器获取模式
    pd = PatternDetector(
        memory_dir=str(PROJECT_ROOT.parent / "memory"),
        lookback_days=30,  # 扩大搜索范围
        min_evidence=1
    )
    patterns = pd.detect()
    
    # 2. 查找匹配的模式
    target_pattern = None
    for p in patterns:
        if p.pattern_id == args.pattern_id:
            target_pattern = p
            break
    
    if not target_pattern:
        print(f"❌ 未找到模式: {args.pattern_id}")
        print("可用的模式:")
        for p in patterns:
            print(f"  - {p.pattern_id}: {p.pattern_name}")
        return
    
    # 3. 生成技能文档
    try:
        skill_path = generate_skill(target_pattern)
        print(f"✅ 技能文档已生成: {skill_path}")
        
        # 4. 显示技能内容
        skill_content = Path(skill_path).read_text(encoding="utf-8")
        print("\n" + "="*50)
        print("生成的技能文档:")
        print("="*50)
        print(skill_content)
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        logger.error(f"技能生成失败: {e}")


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
            try:
                skill_path = generate_skill(p)
                print(f"  ✅ 已生成: {skill_path}")
                
                # 验证技能
                if vet_skill(skill_path):
                    print(f"  ✅ 验证通过")
                else:
                    print(f"  ⚠️  验证失败")
            except Exception as e:
                print(f"  ❌ 生成失败: {e}")
        else:
            print(f"⏭️  跳过低置信度模式: {p.pattern_name} ({p.confidence:.2f})")


if __name__ == "__main__":
    main()
