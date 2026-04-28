#!/usr/bin/env python3
"""Check specific files on Mac."""
import pexpect, time, sys

cmds = [
    "echo '===WEB_CHAT==='",
    "sed -n '55,85p' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py 2>/dev/null",
    "echo '===DAEMON_CLIENT==='",
    "cat /Volumes/PortableSSD/omnia-os/src/omnia/daemon_client.py 2>/dev/null | head -60",
    "echo '===DAEMON_RUNNER==='",
    "cat /Volumes/PortableSSD/omnia-os/scripts/daemon.py 2>/dev/null | tail -30",
    "echo '===WATCHDOG==='",
    "ps aux | grep -E 'python|omnia' | grep -v grep",
    "echo '===DONE==='",
]

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
try:
    i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
    if i in [0, 1]:
        child.sendline('130681')
        child.expect(['\$', '%', '#', 'Password:'], timeout=10)
    
    for cmd in cmds:
        child.sendline(cmd)
        time.sleep(0.5)
        idx = child.expect(['\$', '%', '#'], timeout=30)
        output = child.before
        # Only print meaningful output
        lines = [l for l in output.split('\n') if l.strip() and not l.startswith('\x1b')]
        for l in lines:
            print(l)
    
    child.sendline('exit')
    child.close()
except Exception as e:
    print(f"ERROR: {e}")
