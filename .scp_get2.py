#!/usr/bin/env python3
"""SCP file from Mac to local - simpler."""
import pexpect, sys, os

remote = sys.argv[1]
local = sys.argv[2]

# Build command without fancy quoting
cmd = f'scp -o StrictHostKeyChecking=no xushiyao@192.168.31.119:{remote} {local}'
child = pexpect.spawn(cmd, timeout=60)
i = child.expect(['password:', 'Password:', pexpect.EOF, 'Could not resolve', 'No such'], timeout=20)
if i in [0, 1]:
    child.sendline('130681')
    child.expect(pexpect.EOF, timeout=60)
if os.path.exists(local):
    print(f"OK: {local} ({os.path.getsize(local)} bytes)")
else:
    print(f"FAILED: file not created")
    print(child.before[-500:] if child.before else "no output")
child.close()
