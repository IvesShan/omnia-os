#!/usr/bin/env python3
"""快速检查 Mac 上的 Omnia 状态"""
import pexpect, time, re

child = pexpect.spawn('ssh -tt -o StrictHostKeyChecking=no -o ConnectTimeout=15 xushiyao@192.168.31.119',
                      timeout=30, encoding='utf-8')
child.expect('[Pp]assword:', timeout=10)
child.sendline('130681')
time.sleep(2)
child.sendline('')
time.sleep(1)
try: child.read_nonblocking(4096, timeout=2)
except: pass

cmds = [
    'echo "=== 进程 ===" && ps aux | grep -E "python" | grep -v grep || echo "(无python进程)"',
    'echo "=== Web日志(最后10行) ===" && tail -10 /Users/xushiyao/.omnia/web_server.log 2>/dev/null || echo "日志不存在"',
    'echo "=== Daemon日志(最后10行) ===" && tail -10 /Users/xushiyao/.omnia/daemon.log 2>/dev/null || echo "日志不存在"',
    'echo "=== 端口5001 ===" && lsof -i :5001 2>/dev/null || echo "无进程监听5001"',
    'echo "=== 端口6789 ===" && lsof -i :6789 2>/dev/null || echo "无进程监听6789"',
    'echo "=== ports 目录 ===" && ls -la /Volumes/PortableSSD/omnia-os/ 2>/dev/null | head -20',
    'echo "=== 有requirements.txt? ===" && ls /Volumes/PortableSSD/omnia-os/requirements.txt 2>/dev/null || echo "NOT FOUND"',
    'echo "=== 有requirements? ===" && ls /Volumes/PortableSSD/omnia-os/src/requirements.txt 2>/dev/null || echo "src/ NOT FOUND"',
    'echo "=== pip list ===" && /Volumes/PortableSSD/omnia-os/venv/bin/pip list 2>/dev/null | head -20 || echo "pip不可用"',
    'echo "=== .env内容 ===" && head -5 /Volumes/PortableSSD/omnia-os/.env 2>/dev/null || echo "无.env"',
]

for cmd in cmds:
    print(f"\n$ {cmd[:80]}")
    child.sendline(cmd)
    time.sleep(2)
    try:
        data = child.read_nonblocking(8192, timeout=3)
        for line in data.split('\n'):
            line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).replace('\r','').strip()
            if line and 'export PS1' not in line:
                print(f"  {line[:200]}")
    except: pass

child.sendline('exit')
child.expect(pexpect.EOF, timeout=5)
