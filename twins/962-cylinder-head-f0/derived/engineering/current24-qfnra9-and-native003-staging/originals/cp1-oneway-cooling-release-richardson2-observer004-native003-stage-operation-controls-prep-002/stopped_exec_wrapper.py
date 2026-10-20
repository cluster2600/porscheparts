"""HELD/UNRUN same-PID stopped-before-exec stage wrapper."""
import os,re,signal,sys

PY='/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python'
RESOLVED='/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12'
HELPER='/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-staging-freshness-prep-001/stage_four_inputs.py'

assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1])
assert os.path.realpath(sys.executable)==RESOLVED and sys.version_info[:3]==(3,12,11)
assert sys.flags.isolated==sys.flags.no_site==sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0
assert 'site' not in sys.modules and '_distutils_hack' not in sys.modules
assert os.getpid()==os.getpgrp()==os.getsid(0)
os.kill(os.getpid(),signal.SIGSTOP)
os.execv(PY,[PY,'-B','-I','-S',HELPER,sys.argv[1]])
