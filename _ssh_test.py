#!/usr/bin/env python3
import pexpect, sys, time

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', timeout=20, encoding='utf-8')
idx = child.expect(['password:', 'yes/no', pexpect.TIMEOUT, pexpect.EOF], timeout=10)
print(f"Expect idx: {idx}")
print(f"Before: {child.before}")
print(f"After: {child.after}")

if idx == 0:
    child.sendline('130681')
    idx = child.expect(['$', '#', 'Permission denied', pexpect.TIMEOUT], timeout=10)
    print(f"After password idx: {idx}")
    print(f"After password: {child.before}")
    print(f"After password after: {child.after}")
    if idx in (0,1):
        child.sendline('uname -a')
        idx = child.expect(['$', '#', pexpect.TIMEOUT], timeout=10)
        print(f"Output: {child.before}")
        child.sendline('exit')
