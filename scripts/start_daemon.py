#!/usr/bin/env python3
"""Start the Omnia Persona Daemon in the background."""

import logging
import os
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "daemon.pid"
LOG_FILE = OMNIA_HOME / "daemon.log"
RUNNER_FILE = PROJECT_ROOT / ".omnia" / "_daemon_runner.py"

# 日志轮转配置
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_log_rotation():
    """Setup log rotation for daemon.log"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if log file is too large (>10MB), if so rotate it manually
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
        # Rotate existing log files
        for i in range(4, 0, -1):
            old_file = LOG_FILE.with_suffix(f'.log.{i}')
            older_file = LOG_FILE.with_suffix(f'.log.{i+1}')
            if old_file.exists():
                old_file.rename(older_file)
        LOG_FILE.rename(LOG_FILE.with_suffix('.log.1'))
    
    # Create a rotating file handler
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    
    return handler


def main():
    if PID_FILE.exists():
        old_pid = PID_FILE.read_text().strip()
        try:
            pid_int = int(old_pid)
            os.kill(pid_int, 0)
            
            # 额外检查：确认进程确实是 Omnia 守护进程
            # 通过检查 /proc/{pid}/cmdline
            try:
                cmdline_path = Path(f"/proc/{pid_int}/cmdline")
                if cmdline_path.exists():
                    cmdline = cmdline_path.read_text()
                    if "omnia" in cmdline.lower() or "daemon" in cmdline.lower():
                        print(f"Daemon already running (pid={old_pid}).")
                        return
                    else:
                        print(f"⚠️ PID {old_pid} exists but is not Omnia daemon, ignoring stale PID file.")
                else:
                    print(f"⚠️ PID {old_pid} not found in /proc, ignoring stale PID file.")
            except Exception as e:
                print(f"⚠️ Could not verify PID {old_pid}: {e}")
                
        except (OSError, ValueError) as e:
            # 进程不存在，继续启动
            print(f"⚠️ Stale PID file found (pid={old_pid}), removing.")
            PID_FILE.unlink(missing_ok=True)

    # Priority: pytorch_env > omnia venv > system python
    pytorch_python = Path.home() / "pytorch_env" / "bin" / "python3"
    omnia_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"
    
    if pytorch_python.exists():
        python_exe = str(pytorch_python)
        print("✓ Using pytorch_env (semantic vectors enabled)")
    elif omnia_venv_python.exists():
        python_exe = str(omnia_venv_python)
        print("✓ Using omnia venv (chromadb enabled)")
    else:
        python_exe = sys.executable
        print("⚠ Using system Python (limited features)")

    # Ensure runner directory exists
    RUNNER_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write runner script ONLY if it doesn't exist yet
    # (uses __file__ to auto-detect paths at runtime - cross-platform safe)
    if not RUNNER_FILE.exists():
        runner_code = '''#!/usr/bin/env python3
# Omnia Daemon Runner - auto-detect paths at runtime.

import sys
import os
from pathlib import Path

# Auto-detect project root: <this_file>/.omnia/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add src to path
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Force CPU mode for stability
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# Force offline mode for HuggingFace (avoid network requests)
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

print("[BOOTSTRAP] Starting Omnia daemon...")
print(f"[BOOTSTRAP] Python: {sys.executable}")
sys.stdout.flush()

# Step 0: Load last context
try:
    from core.context_manager import load_last_context
    ctx = load_last_context()
    if ctx:
        print()
        print("=" * 60)
        print("上次会话上下文:")
        print("=" * 60)
        print(f"时间: {ctx.timestamp}")
        print(f"主题: {ctx.topic}")
        print(f"摘要: {ctx.summary}")
        if ctx.active_project:
            print(f"项目: {ctx.active_project}")
        if ctx.active_files:
            files_str = ', '.join(ctx.active_files[:3])
            print(f"文件: {files_str}")
        if ctx.next_steps:
            print("下一步:")
            for step in ctx.next_steps[:3]:
                print(f"   - {step}")
        print("=" * 60)
        print()
        sys.stdout.flush()
    else:
        print("[BOOTSTRAP] No previous context found, starting fresh.")
        sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: Could not load context: {e}")
    sys.stdout.flush()

# Step 1: Bootstrap core features
try:
    from core.bootstrap import bootstrap_omnia
    report = bootstrap_omnia(workspace_root=PROJECT_ROOT.parent, lazy=True)
    print(f"[BOOTSTRAP] Core initialized: {report['initialized_modules']}")
    sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: {e}")
    sys.stdout.flush()

# Step 2: Enable semantic vectors
vector_service = None
try:
    from core.shared_vector_service import SharedVectorService
    print("[BOOTSTRAP] Enabling semantic vectors...")
    sys.stdout.flush()
    vector_service = SharedVectorService()
    if vector_service.enable_semantic():
        print("[BOOTSTRAP] Semantic vectors enabled (384-dim embeddings)")
    else:
        print("[BOOTSTRAP] Using hash-based vectors (model not available)")
    sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: Semantic vectors unavailable: {e}")
    sys.stdout.flush()

# Step 2.5: Start Vector IPC Server
if vector_service is not None:
    try:
        from core.vector_ipc import VectorIPCServer
        ipc_server = VectorIPCServer(vector_service)
        ipc_server.start()
        print("[BOOTSTRAP] Vector IPC server started (shared model ready)")
        sys.stdout.flush()
    except Exception as e:
        print(f"[BOOTSTRAP] Warning: Vector IPC server failed: {e}")
        sys.stdout.flush()

# Step 2.6: Initialize VectorStore (ChromaDB)
try:
    from core.neural_graph.vector_store import VectorStore
    from core.config import VECTOR_STORE_DIR
    print("[BOOTSTRAP] Initializing VectorStore (ChromaDB)...")
    sys.stdout.flush()
    vector_store = VectorStore(persist_dir=VECTOR_STORE_DIR)
    print(f"[BOOTSTRAP] VectorStore initialized (collection: {vector_store.collection_name})")
    sys.stdout.flush()
except Exception as e:
    print(f"[BOOTSTRAP] Warning: VectorStore unavailable: {e}")
    sys.stdout.flush()

# Step 3: Start daemon
from core.neuro_center import PersonaDaemon, DaemonConfig

cfg = DaemonConfig(
    workspace_root=PROJECT_ROOT.parent,
    poll_interval_seconds=30,
    heartbeat_interval_minutes=5,
)
d = PersonaDaemon(cfg)
print("[BOOTSTRAP] Starting daemon main loop...")
sys.stdout.flush()
d.start()
'''
        RUNNER_FILE.write_text(runner_code, encoding='utf-8')

    # Setup log rotation
    handler = setup_log_rotation()
    
    # Open log file for subprocess output (independent of handler's stream)
    # This ensures log rotation works correctly
    log_fd = open(LOG_FILE, 'a', encoding='utf-8')
    
    proc = subprocess.Popen(
        [python_exe, "-u", str(RUNNER_FILE)],  # -u for unbuffered
        stdout=log_fd,
        stderr=log_fd,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    
    # Close file descriptor in parent process
    # Child process has inherited a copy, so this won't affect it
    log_fd.close()
    
    PID_FILE.write_text(str(proc.pid))
    print(f"Persona Daemon started (pid={proc.pid}).")
    print(f"Python: {python_exe}")
    print(f"Log: {LOG_FILE}")
    print(f"Log rotation: {MAX_LOG_SIZE // 1024 // 1024} MB max, {BACKUP_COUNT} backups")


if __name__ == "__main__":
    main()
