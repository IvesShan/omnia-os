#!/bin/bash
# Omnia systemd wrapper — starts daemon then holds web server in foreground
set -e

OMNIA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_DIR="$(cd "$OMNIA_DIR/.." && pwd)"

cd "$OMNIA_DIR"

# Load env if present
if [ -f "$OMNIA_DIR/.env" ]; then
  export $(grep -v '^#' "$OMNIA_DIR/.env" | xargs)
fi

# Ensure log directory exists
mkdir -p "$WORKSPACE_DIR/.omnia"

# Start daemon in background if not already running
if ! pgrep -f "persona_daemon.py" > /dev/null 2>&1; then
  python3 "$OMNIA_DIR/scripts/start_daemon.py"
fi

# Hold web server in foreground so systemd tracks us
exec python3 "$OMNIA_DIR/src/omnia/web_server.py"
