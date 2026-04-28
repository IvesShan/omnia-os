#!/usr/bin/env python3
"""Use ssh with stdin pipe to execute commands on Mac."""
import subprocess, sys

cmd = sys.argv[1]

# Build ssh command that reads password from stdin
ssh_script = f"""#!/bin/bash
expect << 'EXPECTEOF'
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119
expect {{
    "password:" {{ send "130681\\r"; exp_continue }}
    "Password:" {{ send "130681\\r"; exp_continue }}
    "%" {{ send "{cmd}\\r"; exp_continue }}
    "$" {{ send "{cmd}\\r"; exp_continue }}
    "~ %" {{ send "{cmd}\\r"; exp_continue }}
}}
EXPECTEOF
"""

# Simpler: use sshpass approach through a named pipe
# Actually let's just use a single ssh command with batch mode
result = subprocess.run(
    ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
     '-o', 'BatchMode=no',
     'xushiyao@192.168.31.119', cmd],
    input='130681\n',
    capture_output=True,
    text=True,
    timeout=60
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500] if result.stderr else "")
print("RC:", result.returncode)
