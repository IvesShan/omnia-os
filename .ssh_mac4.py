#!/usr/bin/env python3
"""Direct grep on Mac files."""
import pexpect, time

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
try:
    i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
    if i in [0, 1]:
        child.sendline('130681')
        child.expect(['\$', '%', '#', 'Password:'], timeout=10)
    
    cmds = [
        "grep -n 'def chat\\|def send\\|class Persona' /Volumes/PortableSSD/omnia-os/src/omnia/daemon_client.py 2>/dev/null",
        "grep -n 'def chat\\|client\\.' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py 2>/dev/null",
        "grep -n 'def chat\\|def main_loop\\|def run\\|signal' /Volumes/PortableSSD/omnia-os/scripts/daemon.py 2>/dev/null",
        "cat /Volumes/PortableSSD/omnia-os/scripts/daemon.py 2>/dev/null | wc -l",
        "ls /Volumes/PortableSSD/omnia-os/scripts/ 2>/dev/null",
        "cat /Volumes/PortableSSD/omnia-os/.pids/daemon.pid 2>/dev/null",
        "kill -0 $(cat /Volumes/PortableSSD/omnia-os/.pids/daemon.pid 2>/dev/null) 2>&1 && echo 'ALIVE' || echo 'DEAD'",
    ]
    
    for cmd in cmds:
        child.sendline(cmd)
        time.sleep(0.8)
        child.expect(['\$', '%', '#'], timeout=30)
        out = child.before.split('\n')
        for line in out:
            l = line.strip()
            if l and not l.startswith('\x1b') and not l.startswith('echo'):
                # filter out shell echo wrapping
                if '?2004h' not in l and '?2004l' not in l:
                    print(l)
    
    child.sendline('exit')
    child.close()
except Exception as e:
    print(f"ERR: {e}")
