#!/usr/bin/env python3
"""Start the Omnia Persona Daemon in the background."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

# Use OMNIA_HOME from config (same as web_server.py)
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "daemon.pid"
LOG_FILE = OMNIA_HOME / "daemon.log"


def main():
    if PID_FILE.exists():
        old_pid = PID_FILE.read_text().strip()
        try:
            os.kill(int(old_pid), 0)
            print(f"Daemon already running (pid={old_pid}).")
            return
        except (OSError, ValueError):
            pass

    # Use pytorch_env if available (for semantic vectors)
    pytorch_python = Path.home() / "pytorch_env" / "bin" / "python3"
    if pytorch_python.exists():
        python_exe = str(pytorch_python)
        print("✓ Using pytorch_env (semantic vectors enabled)")
    else:
        python_exe = sys.executable
        print("⚠ Using system Python (semantic vectors disabled)")

    # Write runner script with offline mode support and context loading
    runner = PROJECT_ROOT / ".omnia" / "_daemon_runner.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text(
        f"""\
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(r"{PROJECT_ROOT}") / "src"))

# Force CPU mode for stability
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# Force offline mode for HuggingFace (avoid network requests)
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

print("[BOOTSTRAP] Starting Omnia daemon...")
print(f"[BOOTSTRAP] Python: {{sys.executable}}")
sys.stdout.flush()

# Step 0: Load last context (自动加载最后一次上下文)
try:
    from core.context_manager import load_last_context
    ctx = load_last_context()
    if ctx:
        print("")
        print("=" * 60)
        print("📖 上次会话上下文:")
        print("=" * 60)
        print(f"📅 时间: {{ctx.timestamp}}")
        print(f"📌 主题: {{ctx.topic}}")
        print(f"📝 摘要: {{ctx.summary}}")
        if ctx.active_project:
            print(f"🏗️ 项目: {{ctx.active_project}}")
        if ctx.active_files:
            files_str = ', '.join(ctx.active_files[:3])
            print(f"📄 文件: {{files_str}}")
        if ctx.next_steps:
            print("➡️ 下一步:")
            for step in ctx.next_steps[:3]:
                print(f"   - {{step}}")
        print("=" * 60)
        print("")
        sys.stdout.flush()
    else:
        print("[BOOTSTRAP] No previous context found, starting fresh.")
        sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: Could not load context: {{e}}")
    sys.stdout.flush()

# Step 1: Bootstrap core features
try:
    from core.bootstrap import bootstrap_omnia
    report = bootstrap_omnia(workspace_root=Path(r"{PROJECT_ROOT.parent}"), lazy=True)
    print(f"[BOOTSTRAP] Core initialized: {{report['initialized_modules']}}")
    sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: {{e}}")
    sys.stdout.flush()

# Step 2: Enable semantic vectors (loads model, ~30-60 seconds)
try:
    from core.shared_vector_service import SharedVectorService
    print("[BOOTSTRAP] Enabling semantic vectors...")
    sys.stdout.flush()
    svc = SharedVectorService()
    if svc.enable_semantic():
        print("[BOOTSTRAP] ✓ Semantic vectors enabled (384-dim embeddings)")
    else:
        print("[BOOTSTRAP] ⚠ Using hash-based vectors (model not available)")
    sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: Semantic vectors unavailable: {{e}}")
    sys.stdout.flush()

# Step 3: Start daemon
from core.neuro_center import PersonaDaemon, DaemonConfig

cfg = DaemonConfig(
    workspace_root=r"{PROJECT_ROOT.parent}",
    poll_interval_seconds=30,
    heartbeat_interval_minutes=5,
)
d = PersonaDaemon(cfg)
print("[BOOTSTRAP] Starting daemon main loop...")
sys.stdout.flush()
d.start()
""",
        encoding="utf-8",
    )

    # Ensure log directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    log = open(LOG_FILE, "a")
    proc = subprocess.Popen(
        [python_exe, "-u", str(runner)],  # -u for unbuffered
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"Persona Daemon started (pid={proc.pid}).")
    print(f"Python: {python_exe}")
    print(f"Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
