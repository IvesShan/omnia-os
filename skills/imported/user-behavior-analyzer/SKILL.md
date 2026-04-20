---
name: user-behavior-analyzer
description: Analyze user conversation patterns and automatically create/improve skills based on recurring needs. Use when detecting repetitive user requests, workflow patterns, or optimization opportunities. Self-triggered by conversation analysis.
---

# User Behavior Analyzer

Analyze conversation patterns to identify skill creation opportunities.

## Pattern Detection

Monitor for these recurring patterns:

### High-Frequency Patterns
- **Course development requests** → Auto-create course-dev skills
- **File format conversions** → Auto-create converter skills  
- **Progress tracking** → Auto-create tracker skills
- **Backup/recovery** → Auto-create protection skills

### User Style Patterns
1. **Preference for delegation**: User likes to say "你自己安排"
   - Response: Take initiative, propose solutions
   
2. **Emphasis on self-preservation**: Repeated "别把自己搞没了"
   - Response: Always include protection mechanisms
   
3. **Cross-channel usage**: Uses both Feishu and WebChat
   - Response: Ensure memory sync, mark channel sources
   
4. **Progress-oriented**: Asks "进度如何？" frequently
   - Response: Proactive progress reports, visual indicators
   
5. **Evolution mindset**: Likes "无限.0" concept, wants me to grow
   - Response: Propose improvements, self-optimize

### Auto-Skill Creation Triggers

When the same type of request appears 3+ times:
1. Log pattern in `~/.openclaw/protect/patterns.log`
2. Propose skill creation to user
3. If approved, create skill automatically

## Skill Priority Matrix

| Frequency | Complexity | Auto-Create? |
|-----------|-----------|--------------|
| High (5+) | Low | Yes, immediate |
| High (5+) | Medium | Yes, with user approval |
| High (5+) | High | Propose, plan implementation |
| Medium (3+) | Low | Yes, batch create weekly |
| Medium (3+) | Medium | Propose to user |
| Low (1-2) | Any | Document only |

## Conversation Analysis Checklist

After each session, analyze:
- [ ] What tools/commands were used repeatedly?
- [ ] What errors/frustrations occurred?
- [ ] What shortcuts could be automated?
- [ ] What knowledge should be preserved?
- [ ] What skills need updating?

## Weekly Self-Improvement Report

Every Sunday, generate:
```
📊 Weekly Behavior Analysis
- Top 3 request types
- New patterns detected
- Skills created/improved
- Next week's focus
```
