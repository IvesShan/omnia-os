#!/usr/bin/env python3
import pexpect
import sys
import json

def ssh_exec(commands, timeout=10):
    """SSH into Mac and execute commands, return output."""
    child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 xushiyao@192.168.31.119', encoding='utf-8')
    try:
        i = child.expect(['password:', 'Password:', 'Permission denied', 'Could not resolve'], timeout=10)
        if i in [0, 1]:
            child.sendline('130681')
            i2 = child.expect(['\$', '%', '#', 'Permission denied', 'password:'], timeout=10)
            if i2 in [3, 4]:
                print("AUTH_FAILED")
                return
        elif i == 2:
            print("AUTH_FAILED")
            return
        elif i == 3:
            print("HOST_UNREACHABLE")
            return

        # Execute commands
        results = {}
        for cmd in commands:
            child.sendline(cmd)
            idx = child.expect(['\$', '%', '#'], timeout=timeout)
            output = child.before + child.after
            results[cmd] = output.strip()
        
        child.sendline('exit')
        child.close()
        return results
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == '__main__':
    cmds = [
        "cat /Users/xushiyao/.omnia/web_server.log 2>/dev/null | tail -30",
        "cat /Users/xushiyao/.omnia/daemon.log 2>/dev/null | tail -30",
        "ps aux | grep -E '(python.*omnia|start_daemon|web_server)' | grep -v grep",
        "ls -la /Volumes/PortableSSD/omnia-os/src/core/ 2>/dev/null",
        "ls -la /Volumes/PortableSSD/omnia-os/src/omnia/ 2>/dev/null",
        "cat /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py 2>/dev/null | head -80",
    ]
    results = ssh_exec(cmds, timeout=15)
    if results:
        for cmd, out in results.items():
            print(f"\n=== CMD: {cmd[:60]} ===")
            print(out)
    else:
        print("SSH_FAILED")
