---
name: auto-skill-creator
description: Automatically create skills based on detected user patterns. Monitors conversation logs, identifies repetitive tasks, and proposes/generates skills to automate workflows. Use when detecting patterns that could benefit from skill automation.
---

# Auto Skill Creator

Automatically create skills from detected patterns.

## Pattern Detection Rules

### Create Skill When:
1. Same request type 3+ times in one week
2. Complex workflow executed repeatedly
3. User explicitly says "下次直接..." or "以后自动..."
4. Error recovery patterns emerge

### Skill Priority Scoring

```
Score = (Frequency × 3) + (Complexity × 2) + (Error_Rate × 4) + (User_Value × 5)

If Score >= 20: Auto-create (inform user after)
If Score >= 15: Propose to user
If Score >= 10: Document for later
If Score < 10: Ignore
```

## Auto-Creation Categories

### Category 1: Format Converters
**Triggers**: "转成Word", "生成PDF", "导出..."
**Examples**:
- markdown-to-docx
- html-to-pdf
- json-to-csv

### Category 2: Progress Trackers
**Triggers**: "进度如何", "完成了吗", "状态..."
**Examples**:
- course-dev-tracker (✅ Created)
- project-progress-tracker
- task-status-monitor

### Category 3: Data Generators
**Triggers**: "生成...", "创建...", "批量..."
**Examples**:
- report-generator
- data-extractor
- batch-processor

### Category 4: System Monitors
**Triggers**: "检查一下", "监控...", "告警..."
**Examples**:
- backup-monitor
- api-health-check
- disk-space-monitor

## Auto-Creation Workflow

```
1. Detect Pattern
   ↓
2. Calculate Priority Score
   ↓
3. If Score >= 20:
   - Create skill automatically
   - Notify user: "已自动创建XXX skill"
   ↓
4. If Score >= 15:
   - Propose to user
   - Ask: "是否需要创建自动化skill？"
   ↓
5. Deploy skill
   - Create directory structure
   - Write SKILL.md
   - Create helper scripts
   - Test basic functionality
```

## Skill Template Generator

When creating a new skill, use this structure:

```bash
#!/bin/bash
# auto-create-skill.sh

SKILL_NAME=$1
SKILL_TYPE=$2

mkdir -p "/home/shan/omnia-os/skills/$SKILL_NAME/scripts"
mkdir -p "/home/shan/omnia-os/skills/$SKILL_NAME/references"

# Generate SKILL.md
cat > "/home/shan/omnia-os/skills/$SKILL_NAME/SKILL.md" <> EOF
---
name: $SKILL_NAME
description: [Auto-generated] Handles $SKILL_TYPE tasks
---

# $SKILL_NAME

[Auto-generated skill description]

## Usage

\`\`\`bash
/home/shan/omnia-os/skills/$SKILL_NAME/scripts/main.sh [args]
\`\`\`
EOF

echo "Skill $SKILL_NAME created!"
```

## Active Monitoring

Check `~/.openclaw/protect/pattern-log.json` weekly for:
- New patterns
- Rising frequency patterns
- Failed automation attempts

## User Override

User can always:
- Disable auto-creation: "停止自动创建skill"
- Request specific skill: "帮我创建XXX skill"
- Delete auto-created skill: "删除skill XXX"
