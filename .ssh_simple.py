#!/usr/bin/env python3
"""Simple SSH command execution on Mac."""
import pexpect, sys, base64

cmd = sys.argv[1]

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
if i in [0, 1]:
    child.sendline('130681')
    child.expect(['\$', '%', '#', 'Password:'], timeout=10)

# Disable bracketed paste mode
child.sendline('bind "^[[?2004h" "" 2>/dev/null; set +o interactivecomments 2>/dev/null')
child.expect(['\$', '%', '#'], timeout=5)

child.sendline(cmd)
child.expect(['\$', '%', '#'], timeout=30)
out = child.before

# Clean output
for line in out.split('\n'):
    l = line.strip()
    if l and not l.startswith('\x1b') and '?2004' not in l and l != cmd.strip():
        print(l)

child.sendline('exit')
child.close()
