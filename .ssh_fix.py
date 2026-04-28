#!/usr/bin/env python3
"""Robust SSH for Mac - use marker-based output capture."""
import pexpect, sys, time

MARKER = "==OUTPUT_START=="

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=60)
i = child.expect(['password:', 'Password:', 'Permission denied', pexpect.TIMEOUT], timeout=20)
if i in [0, 1]:
    child.sendline('130681')
    time.sleep(2)
    # Wait for prompt
    child.expect(['\$', '%', '#', pexpect.TIMEOUT], timeout=10)

# Run command with marker
cmd = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'echo "no command"'
full_cmd = f'echo "{MARKER}" && {cmd} && echo "{MARKER}"'
child.sendline(full_cmd)
time.sleep(5)

# Read everything
try:
    idx = child.expect(['\$', '%', '#', pexpect.TIMEOUT], timeout=30)
except:
    pass

out = child.before or ""

# Extract between markers
parts = out.split(MARKER)
if len(parts) >= 2:
    result = parts[-2].strip()
    print(result)
else:
    # Print last part
    lines = [l.strip() for l in out.split('\n') if l.strip() and 'bind' not in l and 'OMNIA' not in l and not l.startswith('\x1b')]
    print('\n'.join(lines[-30:]))

child.sendline('exit')
try:
    child.expect(pexpect.EOF, timeout=5)
except:
    pass
child.close()
