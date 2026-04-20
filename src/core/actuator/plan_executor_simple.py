# Simplified PlanExecutor for Omnia
# This file shows the key changes needed to make Omnia work like OpenClaw

# The main issue: PLAN_PROMPT was forcing JSON output
# OpenClaw's way: Let the model decide how to use tools naturally

# BEFORE (forcing JSON):
PLAN_PROMPT_OLD = """
You are Omnia's planning engine...
Output ONLY a JSON array inside ```json ... ```
"""

# AFTER (let model use tool_calls API naturally):
PLAN_PROMPT_NEW = """
User wants: {goal}

Available tools:
- read_file(path)
- write_file(path, content)
- execute_shell(command)
- list_directory(path)
- web_search(query)
- query_memory(query, layer)

Use tools when needed.
"""

# Key insight:
# OpenClaw passes `tools` parameter to API
# Model naturally uses `tool_calls` API to respond
# No need to force JSON output in prompt
