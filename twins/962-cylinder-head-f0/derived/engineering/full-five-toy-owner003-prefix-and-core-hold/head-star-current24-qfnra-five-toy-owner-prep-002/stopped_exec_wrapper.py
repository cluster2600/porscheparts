"""HELD source only: same-PID stopped exec; no admission is supplied."""
import os,re,signal,sys

PY='/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10'
ADAPTER='/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/head-star-current24-qfnra-five-toy-owner-prep-002/run_fixed_adapter.py'

def main():
    if not (len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1])):
        raise ValueError('Exact external admission digest required')
    if not (os.path.realpath(sys.executable)==os.path.realpath(PY) and sys.version_info[:3]==(3,10,11)):
        raise ValueError('Selected historical3.10.11 route required')
    if not (sys.flags.isolated==sys.flags.no_site==sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0):
        raise ValueError('Exact -B-I-S required')
    if 'site' in sys.modules or '_distutils_hack' in sys.modules:
        raise ValueError('Site startup is prohibited')
    if not (os.getpid()==os.getpgrp()==os.getsid(0)):
        raise ValueError('New samePID/PGID/SID required before helper execution')
    os.kill(os.getpid(),signal.SIGSTOP)
    os.execv(PY,[PY,'-B','-I','-S',ADAPTER,sys.argv[1]])

if __name__=='__main__':main()
