# Course Development Batch Templates

Pre-structured request formats optimized for single-agent batch processing. Use these to maximize output per request while minimizing RPM usage.

**Core Principle**: One comprehensive request → Comprehensive output. Avoid multiple round-trips.

## Template 1: Complete Module (Single Request)

**Best for**: Creating a full learning module in one shot

```
Create a complete module for "[MODULE_NAME]":

TARGET AUDIENCE: [beginner/intermediate/advanced]
ESTIMATED DURATION: [X hours]

OUTPUT STRUCTURE:
1. MODULE OVERVIEW
   - Learning objectives (3-5 bullets)
   - Prerequisites
   - Equipment/tools needed

2. CONTENT SECTIONS (create 3-5 sections)
   For each section provide:
   - Title
   - Key concepts (bullet list)
   - Detailed explanation (2-3 paragraphs)
   - Visual aid suggestions

3. PRACTICAL EXERCISES
   - 2 hands-on exercises with step-by-step instructions
   - Expected outcomes
   - Common mistakes to avoid

4. KNOWLEDGE CHECK
   - 3-5 quiz questions (mix MCQ and open-ended)
   - Answers with explanations

5. RESOURCES
   - Required reading/materials
   - Optional deep-dive resources

FORMAT: Structured markdown with clear headings
```

## Template 2: Multiple Lessons Batch (Single Request)

**Best for**: Generating 3-5 related lessons efficiently

```
Create [N] lessons on "[TOPIC]":

LESSON STRUCTURE (apply to each):
- Title
- Duration estimate
- Learning objectives (2-3)
- Core content (300-500 words)
- 1 practical activity
- 2 review questions

SPECIFIC TOPICS:
1. [Topic A]
2. [Topic B]
3. [Topic C]

CONNECTION: How these lessons build on each other
ASSESSMENT: Final project tying all lessons together
```

## Template 3: Content Review & Enhancement (Single Request)

**Best for**: Comprehensive review and improvement in one pass

```
Review and enhance the following course content:

[PASTE CONTENT HERE]

REVIEW CRITERIA:
1. Clarity: Identify confusing sections
2. Completeness: What's missing?
3. Engagement: Suggest interactive elements
4. Accuracy: Technical correctness

ENHANCEMENTS NEEDED:
- Add [specific elements]
- Improve [specific sections]
- Create [additional materials]

OUTPUT FORMAT:
- Annotated version with comments
- Revised version
- List of all changes made
```

## Template 4: Assessment Creation (Single Request)

**Best for**: Complete assessment package at once

```
Create assessments for "[MODULE_NAME]":

QUIZ (10 questions):
- 4 knowledge recall (MCQ)
- 3 application (scenario-based)
- 2 analysis (compare/contrast)
- 1 synthesis (design/create)

PRACTICAL EXAM:
- Task description
- Success criteria
- Time limit
- Materials needed
- Grading rubric

SELF-ASSESSMENT CHECKLIST:
- 5-10 "I can..." statements for students
```

## Template 5: Curriculum Outline (Single Request)

**Best for**: High-level planning with detailed breakdowns

```
Create curriculum for "[COURSE NAME]":

COURSE INFO:
- Target: [audience]
- Total duration: [hours/weeks]
- Delivery: [online/in-person/hybrid]

MODULE BREAKDOWN (5-8 modules):
For each module:
- Title & brief description
- Duration
- Key deliverables
- Prerequisites from previous modules

SKILLS PROGRESSION:
- Week 1-2: Foundation
- Week 3-4: Application
- Week 5-6: Mastery
- Week 7-8: Integration

CAPSTONE PROJECT:
- Description
- Milestones
- Evaluation criteria
```

## Template 6: Multi-Variant Generation (Single Request)

**Best for**: Creating different versions for different audiences

```
Create 3 versions of "[CONTENT]":

VERSION A - BEGINNER:
- Simplified terminology
- More explanations
- Basic examples only

VERSION B - INTERMEDIATE:
- Standard technical depth
- Mix of examples
- Some assumed knowledge

VERSION C - ADVANCED:
- Technical depth
- Complex scenarios
- Minimal hand-holding

COMMON ELEMENTS (all versions):
- Same learning objectives
- Same practical outcomes
- Consistent structure

VARIATIONS:
- Depth of explanation
- Complexity of examples
- Assumed prior knowledge
```

## Usage Guidelines

### Before Sending
1. **Fill all placeholders** (brackets)
2. **Add constraints** (tone, style, specific requirements)
3. **Specify output format** if you have preferences
4. **Estimate token usage**: Large requests are fine, just not multiple requests

### After Receiving
1. **Review holistically** before asking for changes
2. **Batch revisions**: "Change X, Y, and Z" not three separate messages
3. **Use for iteration**: Take output, refine in next request

### When to Break into Multiple Requests

**Rare, but valid cases**:
- Content exceeds model output limit (rare with Kimi)
- Need mid-point validation before continuing
- User wants to review and approve before next phase

**Default**: Trust single comprehensive request to handle it.

## Anti-Patterns to Avoid

### ❌ Sequential Small Requests
```
"Write the intro" → "Now section 1" → "Now section 2"...
```
**Better**: Single request with complete outline

### ❌ Implicit Iteration
```
"Create module" → "Add exercises" → "Add quiz" → "Fix formatting"...
```
**Better**: Single request specifying all required components

### ❌ Over-Specification
Don't micromanage every sentence. Provide structure, let model fill content.

**Bad**: "Write intro. First sentence say X. Second sentence say Y..."
**Good**: "Write 200-word intro covering: importance, overview, what they'll learn"