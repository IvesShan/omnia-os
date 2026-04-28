#!/usr/bin/env python3
"""SSH fix for Mac - proper approach."""
import pexpect, time, sys

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=60)
i = child.expect(['password:', 'Password:', pexpect.TIMEOUT], timeout=15)
if i in [0, 1]:
    child.sendline('130681')
    time.sleep(2)
else:
    print("SSH failed")
    sys.exit(1)

# Wait for prompt
try:
    child.expect(['%', '#', '$'], timeout=10)
except:
    pass

# Now run actual diagnostic & fix commands one at a time
commands = [
    # Check directory structure
    'echo "===DIR_STRUCTURE==="',
    'ls -d /Volumes/PortableSSD/omnia-os/src/omnia/ 2>&1',
    'ls -d /Volumes/PortableSSD/omnia-os/omnia-os/src/omnia/ 2>&1',
    'echo "===TOP_LEVEL_FILES==="',
    'ls /Volumes/PortableSSD/omnia-os/src/omnia/ 2>&1',
    'echo "===NESTED_FILES==="',
    'ls /Volumes/PortableSSD/omnia-os/omnia-os/src/omnia/ 2>&1',
    'echo "===WEB_PROCESS==="',
    'ps aux | grep web_server | grep -v grep',
    # Fix: copy nested files to top level
    'echo "===MERGING_DIRS==="',
    'cp -rn /Volumes/PortableSSD/omnia-os/omnia-os/src/omnia/*.py /Volumes/PortableSSD/omnia-os/src/omnia/ 2>&1',
    'cp -rn /Volumes/PortableSSD/omnia-os/omnia-os/src/core/*.py /Volumes/PortableSSD/omnia-os/src/core/ 2>&1',
    'echo "===AFTER_MERGE_TOP==="',
    'ls /Volumes/PortableSSD/omnia-os/src/omnia/*.py 2>&1',
    'echo "===DONE==="',
]

for cmd in commands:
    child.sendline(cmd)
    time.sleep(1)
    try:
        child.expect(['%', '#', '$'], timeout=15)
    except:
        pass

# Get all output
out = child.before or ""
child.sendline('exit')
try:
    child.expect(pexpect.EOF, timeout=5)
except:
    pass
child.close()

# Filter output
for line in out.split('\n'):
    l = line.strip()
    if l and '?2004' not in l and not l.startswith('\x1b'):
        print(l)
