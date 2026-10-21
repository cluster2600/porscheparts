"""HELD/UNRUN fixed same-PID stopped-exec wrapper for native005 freshness."""
import hashlib,os,re,signal,sys
from pathlib import Path

PY='/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python'
RESOLVED='/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12'
A=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-helper-root-execution-001/authorization.json')
HELPER=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-prep-001/capture_freshness.py')

assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1])
assert os.path.realpath(sys.executable)==RESOLVED and sys.version_info[:3]==(3,12,11)
assert sys.flags.isolated==sys.flags.no_site==sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0
assert 'site' not in sys.modules and '_distutils_hack' not in sys.modules
assert signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL
assert os.getpid()==os.getpgrp()==os.getsid(0)
assert A.is_file() and not A.is_symlink() and A.stat().st_size<=33554432
assert hashlib.sha256(A.read_bytes()).hexdigest()==sys.argv[1]
raw=HELPER.read_bytes()
assert len(raw)==17737 and hashlib.sha256(raw).hexdigest()=='e3f1c980ead8f7952eb82a1996db7fc167ca829c294afdccf4b9c83d65fe2dac'
os.kill(os.getpid(),signal.SIGSTOP)
os.execv(PY,[PY,'-B','-I','-S',str(HELPER),sys.argv[1]])

