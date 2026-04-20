#!/usr/bin/env python3
"""OpenClaw Memory Hook - Bridge OpenClaw Gateway to Omnia MemoryPalace

This hook is called by OpenClaw Gateway to record conversations to Omnia's MemoryPalace.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add Omnia to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.memory_palace.memory_palace import MemoryPalace


def record_conversation(user_message: str, assistant_response: str, channel: str = "openclaw"):
    """Record a conversation to MemoryPalace
    
    Args:
        user_message: User's message
        assistant_response: Assistant's response
        channel: Communication channel (default: openclaw)
    """
    try:
        memory = MemoryPalace()
        
        # Log the conversation
        memory.log_conversation(
            user_message=user_message,
            assistant_response=assistant_response,
            channel=channel,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "source": "openclaw_gateway"
            }
        )
        
        print(f"[OpenClaw Hook] Recorded conversation to MemoryPalace")
        return True
        
    except Exception as e:
        print(f"[OpenClaw Hook] Error recording conversation: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # For testing
    if len(sys.argv) >= 3:
        user_msg = sys.argv[1]
        assistant_msg = sys.argv[2]
        channel = sys.argv[3] if len(sys.argv) >= 4 else "openclaw"
        record_conversation(user_msg, assistant_msg, channel)
    else:
        print("Usage: openclaw_memory_hook.py <user_message> <assistant_response> [channel]")
