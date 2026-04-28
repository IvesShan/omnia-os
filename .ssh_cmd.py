#!/usr/bin/env python3
"""Execute command on Mac, save output to file, then SCP it."""
import pexpect, sys, os, time

cmd = sys.argv[1]
outfile = '/tmp/mac_output.txt'

# SSH and save output to file
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=30)
i = child.expect(['password:', 'Password:', 'Permission denied'], timeout=15)
if i in [0, 1]:
    child.sendline('130681')
    time.sleep(1)

# Save output to a file to avoid terminal issues
child.sendline(f'{cmd} > {outfile} 2>&1')
time.sleep(3)

child.sendline(f'cat {outfile}')
time.sleep(3)
child.expect(['\$', '%', '#', pexpect.TIMEOUT], timeout=10)
out = child.before or ""

child.sendline('exit')
child.close()

# Print clean output
for line in out.split('\n'):
    l = line.strip()
    if l and not l.startswith('\x1b') and '?2004' not in l and 'cat' not in l and l != cmd.strip():
        print(l)
