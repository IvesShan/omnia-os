#!/usr/bin/env python3
"""Read a file from Mac via SSH using pexpect."""
import pexpect, sys, base64

remote_path = sys.argv[1]

child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
if i in [0, 1]:
    child.sendline('130681')
    child.expect(['\$', '%', '#', 'Password:'], timeout=10)

# Use base64 to avoid terminal issues
child.sendline(f'base64 {remote_path}')
child.expect(['\$', '%', '#'], timeout=30)
out = child.before

# Extract base64 data
lines = out.split('\n')
b64_lines = []
capture = False
for line in lines:
    l = line.strip()
    if l.startswith('base64'):
        capture = True
        continue
    if capture and l and not l.startswith('\x1b') and '?2004' not in l:
        b64_lines.append(l)

b64_data = ''.join(b64_lines)
try:
    content = base64.b64decode(b64_data).decode('utf-8')
    print(content)
except:
    print(f"Failed to decode base64. Got {len(b64_data)} chars")
    print(b64_data[:200])

child.sendline('exit')
child.close()
