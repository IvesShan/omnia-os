#!/usr/bin/env python3
"""SSH into MacBook Pro and fix Omnia issues."""
import pexpect
import sys
import time

def ssh(commands, timeout=30):
    child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 xushiyao@192.168.31.119', encoding='utf-8', timeout=timeout)
    try:
        i = child.expect(['password:', 'Password:', 'Permission denied', 'Could not resolve'], timeout=15)
        if i in [0, 1]:
            child.sendline('130681')
            i2 = child.expect(['\$', '%', '#', 'Permission denied', 'password:'], timeout=10)
            if i2 in [3, 4]:
                print("AUTH_FAILED")
                return None
        elif i >= 2:
            print(f"SSH_FAILED with code {i}")
            return None

        outputs = []
        for cmd in commands:
            child.sendline(cmd)
            time.sleep(0.3)
            idx = child.expect(['\$', '%', '#'], timeout=timeout)
            output = child.before + child.after
            outputs.append(output)
        
        child.sendline('exit')
        child.close()
        return outputs
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == '__main__':
    cmds = [
        "echo '===STATE_START==='",
        "cat /Users/xushiyao/.omnia/web_server.log 2>/dev/null | tail -20",
        "echo '===DAEMON_LOG_START==='",
        "cat /Users/xushiyao/.omnia/daemon.log 2>/dev/null | tail -20",
        "echo '===DAEMON_CODE_START==='",
        "head -30 /Volumes/PortableSSD/omnia-os/scripts/start_daemon.py 2>/dev/null",
        "echo '===WEB_CODE_START==='",
        "grep -n 'send_message\\|def chat\\|def send' /Volumes/PortableSSD/omnia-os/src/omnia/web_server.py 2>/dev/null | head -20",
        "echo '===WS_CODE_START==='",
        "grep -n 'send_message\\|def chat\\|def send' /Volumes/PortableSSD/omnia-os/src/omnia/web_socket.py 2>/dev/null | head -20",
        "echo '===DAEMON_CLIENT==='",
        "grep -n 'def chat\\|def send_message\\|def process' /Volumes/PortableSSD/omnia-os/src/omnia/daemon_client.py 2>/dev/null | head -20",
        "echo '===SYS_PATH_START==='",
        "head -20 /Volumes/PortableSSD/omnia-os/scripts/start_daemon.py 2>/dev/null",
        "echo '===PROCESSES==='",
        "ps aux | grep -E '(python|omnia)' | grep -v grep",
        "echo '===END_STATE==='",
    ]
    results = ssh(cmds, timeout=20)
    if results:
        for r in results:
            print(r)
    else:
        print("SSH_FAILED")
