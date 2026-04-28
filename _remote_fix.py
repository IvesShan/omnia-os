#!/usr/bin/env python3
"""
Omnia 远程修复 — MacBook Pro
策略: 设定自定义 PS1 标记，彻底避免 zsh 提示符匹配问题
"""

import pexpect
import sys
import time
import re

HOST = "192.168.31.119"
USER = "xushiyao"
PASS = "130681"
OMNIA_PATH = "/Volumes/PortableSSD/omnia-os"

MARKER = "OMNIA>"

def ssh_exec(commands, title="操作"):
    print(f"\n{'='*60}")
    print(f"[{title}]")
    print(f"{'='*60}")
    
    child = pexpect.spawn(
        f'ssh -tt -o StrictHostKeyChecking=no -o ConnectTimeout=15 {USER}@{HOST}',
        timeout=600,
        encoding='utf-8',
        codec_errors='replace',
        maxread=8192,
    )
    
    # 处理密码
    idx = child.expect(['[Pp]assword:', 'yes/no', pexpect.TIMEOUT, pexpect.EOF], timeout=20)
    print(f"  连接 idx={idx}")
    
    if idx == 0:
        child.sendline(PASS)
        time.sleep(2)
        child.sendline('')
        time.sleep(1)
    elif idx == 1:
        child.sendline('yes')
        child.expect('[Pp]assword:', timeout=10)
        child.sendline(PASS)
        time.sleep(2)
        child.sendline('')
        time.sleep(1)
    else:
        print("❌ 连接失败")
        return False
    
    # 丢弃欢迎信息
    try:
        child.read_nonblocking(8192, timeout=2)
    except:
        pass
    
    # 设置自定义提示符（短、唯一、不会换行截断）
    child.sendline(f'export PS1="{MARKER}"')
    time.sleep(1)
    try:
        child.read_nonblocking(8192, timeout=1)
    except:
        pass
    child.sendline('')  # 触发新提示符
    time.sleep(0.5)
    try:
        child.read_nonblocking(8192, timeout=1)
    except:
        pass
    
    print("✅ SSH 登录成功")
    
    for i, cmd in enumerate(commands):
        label = cmd[:60].replace('\n', ' ')
        print(f"\n  [{i+1}/{len(commands)}] $ {label}")
        
        timeout = 300 if 'pip install' in cmd else 120
        
        child.sendline(cmd)
        
        # 等待 MARKER 出现
        output_lines = []
        done = False
        try:
            while not done:
                idx = child.expect([MARKER, pexpect.TIMEOUT, pexpect.EOF], timeout=timeout)
                data = child.before or ''
                
                for line in data.split('\n'):
                    line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                    line = line.replace('\x1b[?2004h', '').replace('\x1b[?2004l', '')
                    line = line.replace('\r', '').strip()
                    if line and line != cmd.strip() and MARKER not in line:
                        output_lines.append(line)
                
                if idx == 0:
                    done = True
                else:
                    print(f"    ⚠️ 等待中...（{timeout}s）")
                    timeout = 60
        except Exception as e:
            print(f"    ⚠️ 异常: {e}")
        
        # 打印输出
        seen = set()
        for line in output_lines:
            if line and line not in seen and len(line) > 2:
                seen.add(line)
                print(f"    {line[:250]}")
        
        if done:
            print(f"    ✓ 完成")
        else:
            print(f"    ⚠️ 可能未完全执行")
    
    # 退出
    try:
        child.sendline('exit')
        child.expect(pexpect.EOF, timeout=10)
    except:
        pass
    print(f"\n✅ [{title}] 结束")
    return True


def main():
    print("="*60)
    print("  Omnia 远程修复 — MacBook Pro")
    print(f"  {USER}@{HOST}")
    print("="*60)
    
    # 步骤 1: 检查系统
    print("\n🔍 [1/5] 检查系统状态")
    ssh_exec([
        'uname -a',
        'python3 --version',
        f'ls -la {OMNIA_PATH}/venv/bin/python3 2>/dev/null && file {OMNIA_PATH}/venv/bin/python3 || echo "venv 不存在"',
    ], title="系统检查")
    
    # 步骤 2: 重建 venv
    print("\n🔧 [2/5] 重建 macOS 原生虚拟环境")
    ssh_exec([
        f'rm -rf {OMNIA_PATH}/venv',
        f'python3 -m venv {OMNIA_PATH}/venv',
        f'{OMNIA_PATH}/venv/bin/pip install --upgrade pip setuptools wheel',
        f'{OMNIA_PATH}/venv/bin/pip install -r {OMNIA_PATH}/requirements.txt',
    ], title="重建 venv")
    
    # 步骤 3: 创建 .omnia 目录
    print("\n🔧 [3/5] 创建 .omnia 目录")
    ssh_exec([
        'mkdir -p ~/.omnia && ls -la ~/.omnia/',
    ], title="目录结构")
    
    # 步骤 4: 运行重启脚本
    print("\n🚀 [4/5] 运行重启脚本")
    ssh_exec([
        f'cd {OMNIA_PATH} && bash omnia-restart.sh',
    ], title="启动服务")
    
    # 步骤 5: 验证
    print("\n✅ [5/5] 验证服务状态")
    ssh_exec([
        'sleep 2',
        'ps aux | grep -E "(python.*web_server|start_daemon|watchdog)" | grep -v grep || echo "(无进程)"',
        'curl -s -o /dev/null -w "%{http_code}" http://localhost:5001 2>/dev/null; echo " (WebUI)"',
        'curl -s -o /dev/null -w "%{http_code}" http://localhost:6789/health 2>/dev/null; echo " (Daemon)"',
    ], title="验证")
    
    print("\n" + "="*60)
    print("🏁 远程修复完成！")
    print("="*60)


if __name__ == '__main__':
    main()
