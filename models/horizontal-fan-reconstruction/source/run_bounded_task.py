#!/usr/bin/env python3
"""Run one task in its own process group with CPU, address-space and wall limits."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time


def run(directory,label,command,threads=2,memory_gib=5,timeout=300):
    if not 1<=threads<=4 or not 0<memory_gib<=6 or not 0<timeout<=900:
        raise ValueError('Task exceeds the existing 4 CPU / 6 GiB / 900s admission ceiling')
    available={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}['MemAvailable']
    if available<(memory_gib+1)*1024**3:raise ValueError('Insufficient free memory reserve')
    if not label.replace('-','').replace('_','').replace('.','').isalnum():raise ValueError('Invalid task label')
    log_path=directory/('log.'+label);receipt_path=directory/('receipt.'+label+'.json')
    if log_path.exists() or receipt_path.exists():raise ValueError('Refusing to overwrite an existing job')
    cpu_ids=sorted(os.sched_getaffinity(0))[:threads]
    os.sched_setaffinity(0,cpu_ids);os.nice(10)
    budget=int(memory_gib*1024**3)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS=str(threads),CCX_NPROC_RESULTS=str(threads),CCX_NPROC_EQUATION_SOLVER=str(threads))
    def limits():resource.setrlimit(resource.RLIMIT_AS,(budget,budget))
    start=time.monotonic();timed_out=False
    with log_path.open('x') as log:
        proc=subprocess.Popen(command,cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
        try:code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            code=124
    receipt={'task':label,'command':command,'exit_status':code,'timed_out':timed_out,
             'wall_seconds':time.monotonic()-start,'peak_child_RSS_KiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
             'cpu_affinity':cpu_ids,'max_address_space_GiB':memory_gib,'timeout_seconds':timeout,'nice':10,
             'mem_available_at_admission_bytes':available,'scope':'Only this task process group; no services or third-party processes modified'}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print(log_path.read_text()[-3500:]);return code


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=Path('.'));p.add_argument('--label',required=True)
    p.add_argument('--threads',type=int,default=2);p.add_argument('--memory-gib',type=float,default=5);p.add_argument('--timeout',type=int,default=300);p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:p.error('Task command required')
    raise SystemExit(run(a.directory,a.label,command,a.threads,a.memory_gib,a.timeout))
