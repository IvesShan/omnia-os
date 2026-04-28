#!/usr/bin/env python3
"""SSH into Mac - PS1-based prompt matching."""
import pexpect, sys, random

HOST = '192.168.31.119'
USER = 'xushiyao'

def ssh_run(cmd, password='130681', timeout=60):
    m1 = f'Z1_{random.randint(10000,99999)}'
    ps1 = 'OMNIA>'
    
    ssh = pexpect.spawn(
        f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {USER}@{HOST}',
        encoding='utf-8', timeout=timeout
    )
    
    ssh.expect('assword:', timeout=15)
    ssh.sendline(password)
    
    # Sync prompt and set custom PS1
    ssh.sendline(f'echo {m1}; export PS1="{ps1}"')
    ssh.expect(m1, timeout=10)
    
    # Now PS1 is "OMNIA>" for future prompts.
    # Send actual command - the NEXT prompt will be "OMNIA>"
    ssh.sendline(f'{cmd} 2>&1')
    
    ssh.expect(ps1, timeout=timeout)
    
    output = ssh.before
    lines = output.split('\n')
    
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if line == m1: continue
        if cmd.strip() in line: continue
        cleaned.append(line)
    
    result = '\n'.join(cleaned).strip()
    
    # Restore
    ssh.sendline('export PS1="% "')
    ssh.sendline('exit')
    try: ssh.expect(pexpect.EOF, timeout=3)
    except: pass
    ssh.close()
    return result if result else '[empty]'

def scp_file(local, remote, password='130681', timeout=60):
    p = pexpect.spawn(
        f'scp -o StrictHostKeyChecking=no {local} {USER}@{HOST}:{remote}',
        encoding='utf-8', timeout=timeout
    )
    p.expect('assword:', timeout=15)
    p.sendline(password)
    p.expect(pexpect.EOF, timeout=timeout)
    p.close()
    return 'OK'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: ssh_mac.py <cmd>")
        print("   or: ssh_mac.py --scp <local> <remote>")
        sys.exit(1)
    
    if sys.argv[1] == '--scp':
        print(scp_file(sys.argv[2], sys.argv[3]))
    else:
        print(ssh_run(' '.join(sys.argv[1:])))
