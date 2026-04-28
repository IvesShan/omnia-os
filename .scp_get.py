#!/usr/bin/env python3
"""SCP file from Mac to local."""
import pexpect, sys, os

remote = sys.argv[1]
local = sys.argv[2] if len(sys.argv) > 2 else '/tmp/mac_file'

child = pexpect.spawn(f'scp -o StrictHostKeyChecking=no xushiyao@192.168.31.119:"{remote}" "{local}"', timeout=60)
i = child.expect(['password:', 'Password:', 'Could not resolve', 'No such', pexpect.EOF, 'Permission denied'], timeout=20)
if i in [0, 1]:
    child.sendline('130681')
    child.expect(pexpect.EOF, timeout=60)
    print(f"OK: {local} ({os.path.getsize(local)} bytes)")
elif i == 2:
    print("Host unreachable")
elif i == 3:
    print("File not found")
elif i == 4:
    print("Already done (no password needed)")
elif i == 5:
    print("Permission denied")
child.close()
