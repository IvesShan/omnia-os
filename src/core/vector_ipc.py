"""Vector IPC Service — Inter-process communication for shared vector embeddings.

from core.logging_config import get_logger

logger = get_logger(__name__)

Architecture:
    ┌─────────────┐         Unix Socket        ┌──────────────┐
    │  Web Server │ ────────────────────────→  │   Daemon     │
    │  (client)   │                           │  (server)    │
    │             │ ←────────────────────────  │  (model)     │
    └─────────────┘      vector results        └──────────────┘

Benefits:
    1. Single model in memory (~90MB saved)
    2. Consistent embeddings across processes
    3. Fast local IPC (Unix Socket)
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

from core.config import OMNIA_HOME


# Default socket path
VECTOR_SOCKET_PATH = OMNIA_HOME / "vector_service.sock"
VECTOR_SOCKET_PATH_STR = str(VECTOR_SOCKET_PATH)


class VectorIPCServer:
    """Unix Socket server that exposes SharedVectorService to other processes.
    
    Usage in daemon:
        from core.vector_ipc import VectorIPCServer
        from core.shared_vector_service import SharedVectorService
        
        svc = SharedVectorService()
        svc.enable_semantic()
        
        server = VectorIPCServer(svc)
        server.start()  # Non-blocking, runs in background thread
    """
    
    def __init__(self, vector_service, socket_path: str = VECTOR_SOCKET_PATH_STR):
        self.vector_service = vector_service
        self.socket_path = socket_path
        self.running = False
        self._server_socket = None
        self._thread = None
    
    def start(self):
        """Start the IPC server in a background thread."""
        if self.running:
            return
        
        # Clean up old socket if exists
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        self.running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        print(f"[VectorIPC] Server started at {self.socket_path}")
    
    def stop(self):
        """Stop the IPC server."""
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception:
                pass
        logger.info("[VectorIPC] Server stopped")
    
    def _run_server(self):
        """Run the server loop."""
        try:
            self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)  # Allow periodic check for self.running
            
            while self.running:
                try:
                    client_socket, _ = self._server_socket.accept()
                    # Handle in thread to avoid blocking
                    threading.Thread(
                        target=self._handle_client,
                        args=(client_socket,),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except (FileNotFoundError, IOError, PermissionError) as e:
                    if self.running:
                        print(f"[VectorIPC] Accept error: {e}")
        
        except (ValueError) as e:
            print(f"[VectorIPC] Server error: {e}")
        finally:
            self.stop()
    
    def _handle_client(self, client_socket):
        """Handle a single client request."""
        try:
            # Read request
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Check for complete JSON
                try:
                    request = json.loads(data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue  # Need more data
            
            # Process request
            response = self._process_request(request)
            
            # Send response
            response_data = json.dumps(response).encode('utf-8')
            client_socket.sendall(response_data)
        
        except (json.JSONDecodeError) as e:
            try:
                error_response = {"error": str(e)}
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
            except (json.JSONDecodeError) as e:
                pass
        finally:
            client_socket.close()
    
    def _process_request(self, request: dict) -> dict:
        """Process a vector request."""
        method = request.get("method")
        
        if method == "status":
            return self.vector_service.get_status()
        
        elif method == "encode":
            text = request.get("text", "")
            vec = self.vector_service.encode(text)
            return {
                "vector": vec.tolist(),
                "dim": len(vec)
            }
        
        elif method == "embed":
            texts = request.get("texts", [])
            vectors = self.vector_service.embed(texts)
            return {
                "vectors": [v.tolist() for v in vectors],
                "count": len(vectors),
                "dim": vectors.shape[1] if len(vectors) > 0 else 0
            }
        
        elif method == "similarity":
            vec1 = np.array(request.get("vec1", []), dtype=np.float32)
            vec2 = np.array(request.get("vec2", []), dtype=np.float32)
            sim = self.vector_service.similarity(vec1, vec2)
            return {"similarity": float(sim)}
        
        else:
            return {"error": f"Unknown method: {method}"}


class VectorIPCClient:
    """Client to access vector service via IPC.
    
    Usage in web server:
        from core.vector_ipc import VectorIPCClient
        
        client = VectorIPCClient()
        
        # Check if daemon is available
        if client.is_available():
            vec = client.encode("hello world")
        else:
            # Fallback to local SharedVectorService
            from core.shared_vector_service import get_vector_service
            svc = get_vector_service()
            vec = svc.encode("hello world")
    """
    
    def __init__(self, socket_path: str = VECTOR_SOCKET_PATH_STR, timeout: float = 5.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self._last_check = 0
        self._available = None
    
    def is_available(self) -> bool:
        """Check if the IPC server is available."""
        # Cache check for 5 seconds
        now = time.time()
        if now - self._last_check < 5.0 and self._available is not None:
            return self._available
        
        self._last_check = now
        
        if not os.path.exists(self.socket_path):
            self._available = False
            return False
        
        # Try to connect
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(self.socket_path)
            sock.close()
            self._available = True
            return True
        except (sqlite3.Error) as e:
            self._available = False
            return False
    
    def _call(self, request: dict) -> dict:
        """Make an IPC call to the server."""
        if not self.is_available():
            raise ConnectionError(f"Vector IPC server not available at {self.socket_path}")
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        try:
            sock.connect(self.socket_path)
            
            # Send request
            data = json.dumps(request).encode('utf-8')
            sock.sendall(data)
            sock.shutdown(socket.SHUT_WR)  # Signal end of request
            
            # Read response
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
            
            response = json.loads(response_data.decode('utf-8'))
            
            if "error" in response:
                raise RuntimeError(response["error"])
            
            return response
        
        finally:
            sock.close()
    
    def get_status(self) -> dict:
        """Get vector service status."""
        return self._call({"method": "status"})
    
    def encode(self, text: str) -> np.ndarray:
        """Encode a single text to vector."""
        response = self._call({"method": "encode", "text": text})
        return np.array(response["vector"], dtype=np.float32)
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts to vectors."""
        response = self._call({"method": "embed", "texts": texts})
        return np.array(response["vectors"], dtype=np.float32)
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        response = self._call({
            "method": "similarity",
            "vec1": vec1.tolist(),
            "vec2": vec2.tolist()
        })
        return response["similarity"]


class HybridVectorService:
    """Hybrid vector service that uses IPC when available, falls back to local.
    
    This is the recommended interface for all components:
    
        from core.vector_ipc import HybridVectorService
        
        svc = HybridVectorService()
        vec = svc.encode("hello world")  # Uses IPC if daemon running, else local
    
    Benefits:
        - Seamless fallback
        - No configuration needed
        - Optimal memory usage
    """
    
    def __init__(self, socket_path: str = VECTOR_SOCKET_PATH_STR):
        self.ipc_client = VectorIPCClient(socket_path)
        self._local_service = None
        self._use_ipc = None
    
    def _get_service(self):
        """Get the appropriate vector service."""
        # Check IPC availability (cached)
        if self._use_ipc is None:
            self._use_ipc = self.ipc_client.is_available()
            if self._use_ipc:
                logger.info("[HybridVectorService] Using IPC (shared daemon model)")
            else:
                logger.info("[HybridVectorService] Using local (fallback mode)")
        
        if self._use_ipc:
            return self.ipc_client
        else:
            # Fallback to local service
            if self._local_service is None:
                from core.shared_vector_service import get_vector_service
                self._local_service = get_vector_service()
            return self._local_service
    
    def encode(self, text: str) -> np.ndarray:
        """Encode a single text to vector."""
        return self._get_service().encode(text)
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts to vectors."""
        return self._get_service().embed(texts)
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity."""
        return self._get_service().similarity(vec1, vec2)
    
    def get_status(self) -> dict:
        """Get service status."""
        service = self._get_service()
        if hasattr(service, 'get_status'):
            return service.get_status()
        return {"mode": "local", "status": "unknown"}
    
    def is_ipc_mode(self) -> bool:
        """Check if using IPC mode."""
        return self._use_ipc is True


# Global hybrid service instance
_hybrid_service: Optional[HybridVectorService] = None


def get_hybrid_vector_service() -> HybridVectorService:
    """Get or create the global hybrid vector service."""
    global _hybrid_service
    if _hybrid_service is None:
        _hybrid_service = HybridVectorService()
    return _hybrid_service
