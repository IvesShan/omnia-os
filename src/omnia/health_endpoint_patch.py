"""Health endpoint patch for web_server.py

Add this code after the @app.route("/api/status") endpoint (around line 482)
"""

# Health check endpoint for monitoring
@app.route("/api/health", methods=["GET"])
def health_check():
    """Lightweight health check endpoint for monitoring systems."""
    import psutil
    import os
    
    try:
        # Check daemon status
        daemon_running = _daemon_status()
        
        # Check memory usage
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Check database connections
        memory_ok = True
        try:
            mp = MemoryPalace()
            memory_ok = mp.conn is not None
        except:
            memory_ok = False
        
        # Determine overall health
        status = "healthy" if daemon_running and memory_ok else "degraded"
        
        return jsonify({
            "status": status,
            "daemon": "running" if daemon_running else "stopped",
            "memory_mb": round(memory_mb, 1),
            "database": "connected" if memory_ok else "error",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }), 200 if status == "healthy" else 503
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }), 500
