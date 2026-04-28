#!/usr/bin/env python3
"""SCP files from Mac using pexpect."""
import pexpect, sys

if len(sys.argv) < 2:
    print("Usage: .scp_mac.py <remote_path>")
    sys.exit(1)

remote_path = sys.argv[1]
local_path = sys.argv[2] if len(sys.argv) > 2 else '/tmp/mac_file.txt'

child = pexpect.spawn(f'scp -o StrictHostKeyChecking=no xushiyao@192.168.31.119:"{remote_path}" {local_path}', encoding='utf-8', timeout=30)
i = child.expect(['password:', 'Password:', 'Could not resolve', 'No such'], timeout=15)
if i in [0, 1]:
    child.sendline('130681')
    child.expect(pexpect.EOF, timeout=30)
    print(f"SCP done: {local_path}")
elif i == 2:
    print("Host unreachable")
elif i == 3:
    print("File not found")
child.close()
