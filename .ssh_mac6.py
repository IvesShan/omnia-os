#!/usr/bin/env python3
"""Read MORE code from Mac."""
import pexpect, time

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
try:
    i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
    if i in [0, 1]:
        child.sendline('130681')
        child.expect(['\$', '%', '#', 'Password:'], timeout=10)
    
    cmds = [
        "sed -n '1200,1240p' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py",
        "sed -n '1295,1350p' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py",
        "wc -l /Volumes/PortableSSD/omnia-os/scripts/daemon.py",
        "cat /Volumes/PortableSSD/omnia-os/scripts/daemon.py",
        "ps aux | grep python | grep -v grep",
        "ls /Volumes/PortableSSD/omnia-os/scripts/",
    ]
    
    results = {}
    for cmd in cmds:
        child.sendline(cmd)
        time.sleep(1)
        child.expect(['\$', '%', '#'], timeout=30)
        out = child.before
        lines = [l for l in out.split('\n') if l.strip() and '?2004' not in l and not l.startswith('\x1b')]
        print(f"\n{'='*40}")
        print(f"CMD: {cmd[:60]}")
        print('='*40)
        for l in lines:
            print(l)
    
    child.sendline('exit')
    child.close()
except Exception as e:
    print(f"ERR: {e}")
