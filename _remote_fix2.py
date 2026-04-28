#!/usr/bin/env python3
"""修复 Mac — 传 requirements.txt + 安装依赖 + 重启"""
import pexpect, time, re, os, base64

HOST = "192.168.31.119"
USER = "xushiyao"
PASS = "130681"
OMNIA = "/Volumes/PortableSSD/omnia-os"

# requirements.txt 的 base64
B64_REQ = "IyBPbW5pYSBDb3JlIERlcGVuZGVuY2llcwojIFB5dGhvbiAzLjgrIHJlcXVpcmVkCgojIExMTSBBUElzCm9wZW5haT49MS4wLjAKYW50aHJvcGljPj0wLjE4LjAKcmVxdWVzdHM+PTIuMzEuMAoKIyBNQ1AgKE1vZGVsIENvbnRleHQgUHJvdG9jb2wpCm1jcD49MC45LjAKCiMgRGF0YSAmIENvbmZpZwpweWRhbnRpYz49Mi4wLjAKcHl0aG9uLWRvdGVudj49MS4wLjAKcHl5YW1sPj02LjAKbnVtcHk+PTEuMjQuMAoKIyBBc3luYyAmIE5ldHdvcmtpbmcKaHR0cHg+PTAuMjUuMAp3ZWJzb2NrZXRzPj0xMi4wCgojIFV0aWxpdGllcwpweXRob24tZGF0ZXV0aWw+PTIuOC4wCnRpa3Rva2VuPj0wLjUuMApjcm9uaXRlcj49Mi4wLjAKCiMgVmVjdG9yIFN0b3JlICYgRW1iZWRkaW5ncyAoZm9yIHNlbWFudGljIHNlYXJjaCkKY2hyb21hZGI+PTEuNS4wCnNlbnRlbmNlLXRyYW5zZm9ybWVycz49Mi4yLjAKCiMgT3B0aW9uYWw6IE1lbW9yeSBTeXN0ZW0KIyBtY3Atc2VydmVyLW1lbW9yeSAgIyDlpoLmnpzpnIDopoHmnKzlnLDorrDlv4bmnI3liqHlmagKCiMgT3B0aW9uYWw6IEZlaXNodSBJbnRlZ3JhdGlvbgojIOmjnuS5piBTREsg6ZyA6KaB5Y2V54us5a6J6KOFCg=="

def ssh_exec(commands, title="操作", cmd_timeout=120):
    print(f"\n{'='*50}\n[{title}]")
    child = pexpect.spawn(f'ssh -tt -o StrictHostKeyChecking=no -o ConnectTimeout=15 {USER}@{HOST}',
                          timeout=600, encoding='utf-8', maxread=8192)
    child.expect('[Pp]assword:', timeout=15)
    child.sendline(PASS)
    time.sleep(2)
    child.sendline('')
    time.sleep(1)
    try: child.read_nonblocking(8192, timeout=2)
    except: pass

    child.sendline('export PS1="\\n==> "')
    time.sleep(0.5)
    try: child.read_nonblocking(8192, timeout=1)
    except: pass
    child.sendline('')
    time.sleep(0.3)
    try: child.read_nonblocking(8192, timeout=1)
    except: pass

    for i, cmd in enumerate(commands):
        label = cmd[:70].replace('\n', ' ')
        print(f"\n  [{i+1}/{len(commands)}] $ {label}")
        child.sendline(cmd)
        t = cmd_timeout if 'pip install' in cmd else 120
        done = False
        while not done:
            idx = child.expect(['\n==>', pexpect.TIMEOUT], timeout=t)
            data = child.before or ''
            for line in data.split('\n'):
                line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                line = line.replace('\x1b[?2004h','').replace('\x1b[?2004l','').replace('\r','').strip()
                if line and '==>' not in line and line != cmd.strip() and 'PS1' not in line:
                    if len(line) < 300:
                        print(f"    {line}")
            if idx == 0:
                done = True
            else:
                print(f"    ⚠️ 等待中...")
                t = 60
    try:
        child.sendline('exit')
        child.expect(pexpect.EOF, timeout=5)
    except: pass
    print(f"✅ [{title}] 完成")

def main():
    print("="*60)
    print("  Omnia 远程修复 v2 — 传 requirements.txt")
    print(f"  {USER}@{HOST}")
    print("="*60)

    # 1. 传文件
    print("\n📄 [1/4] 传输 requirements.txt")
    ssh_exec([
        f'echo {B64_REQ} | base64 -d > {OMNIA}/requirements.txt',
        f'echo "文件大小: $(wc -c < {OMNIA}/requirements.txt) bytes"',
        f'head -5 {OMNIA}/requirements.txt',
    ], title="传输文件")

    # 2. 安装依赖
    print("\n📦 [2/4] 安装 Python 依赖")
    ssh_exec([
        f'{OMNIA}/venv/bin/pip install -r {OMNIA}/requirements.txt',
    ], title="安装依赖", cmd_timeout=300)

    # 3. 验证依赖
    print("\n🔍 [3/4] 验证依赖安装")
    ssh_exec([
        f'{OMNIA}/venv/bin/pip list 2>/dev/null | grep -iE "flask|openai|anthropic|mcp|chroma|httpx|requests|pydantic"',
        f'{OMNIA}/venv/bin/python -c "import flask; print(f\'Flask {flask.__version__} OK\')" 2>&1',
    ], title="验证依赖")

    # 4. 重启服务
    print("\n🚀 [4/4] 重启 Omnia 服务")
    ssh_exec([
        f'cd {OMNIA} && bash omnia-restart.sh',
    ], title="重启服务", cmd_timeout=120)

    # 5. 最终验证
    print("\n✅ [5/5] 最终验证")
    ssh_exec([
        'sleep 4',
        'ps aux | grep -E "python.*web_server|start_daemon" | grep -v grep || echo "(无进程)"',
        'curl -s -o /dev/null -w "WebUI: %{http_code}" http://localhost:5001 2>/dev/null; echo ""',
        'curl -s -o /dev/null -w "Daemon: %{http_code}" http://localhost:6789/health 2>/dev/null; echo ""',
    ], title="验证服务")

    print("\n" + "="*60)
    print("🏁 修复全部完成！")
    print("="*60)

if __name__ == '__main__':
    main()
