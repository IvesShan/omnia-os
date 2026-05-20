#!/usr/bin/env python3
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
