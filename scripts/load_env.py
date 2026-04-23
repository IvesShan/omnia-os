"""Load .env file into environment variables."""
import os
from pathlib import Path

def load_env(env_file: Path = None):
    """Load .env file into os.environ."""
    if env_file is None:
        # Find .env in project root
        env_file = Path(__file__).parent.parent / ".env"
    
    if not env_file.exists():
        return
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Only set if not already defined
                if key not in os.environ:
                    os.environ[key] = value

# Auto-load when imported
load_env()
