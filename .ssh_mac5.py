#!/usr/bin/env python3
"""Read specific code from Mac."""
import pexpect, time, json, base64

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
try:
    i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
    if i in [0, 1]:
        child.sendline('130681')
        child.expect(['\$', '%', '#', 'Password:'], timeout=10)
    
    cmds = [
        # Read chat handler from web_server.py (lines 1175-1210)
        "sed -n '1175,1210p' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py",
        # Read chat_stream handler (lines 1285-1330)
        "sed -n '1285,1330p' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py",
        # Read daemon.py file
        "cat /Volumes/PortableSSD/omnia-os/scripts/daemon.py",
        # Check if daemon is running
        "ps aux | grep -i python | grep -v grep",
        # List scripts dir
        "ls -la /Volumes/PortableSSD/omnia-os/scripts/",
        # Check .pids
        "cat /Volumes/PortableSSD/omnia-os/.pids/daemon.pid 2>/dev/null; echo '---'; cat /Volumes/PortableSSD/omnia-os/.pids/web.pid 2>/dev/null",
    ]
    
    for cmd in cmds:
        child.sendline(cmd)
        time.sleep(1)
        child.expect(['\$', '%', '#'], timeout=30)
        out = child.before
        # Filter terminal garbage
        clean = []
        for line in out.split('\n'):
            l = line.strip()
            if l and not l.startswith('\x1b') and '?2004' not in l:
                clean.append(l)
        print('\n'.join(clean))
        print("===CMD_END===")
    
    child.sendline('exit')
    child.close()
except Exception as e:
    print(f"ERR: {e}")
