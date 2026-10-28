"""Run bounded adaptive tetrahedralisation; a new wall requires independent certification."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np

prepared,out=map(Path,sys.argv[1:]);assert not out.exists() and not out.is_symlink();out.mkdir(mode=0o700)
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
proof=json.loads((prepared/'receipt.json').read_text())
for name in ['fluid.smesh','fluid.mtr','boundary.obj']:assert sha(prepared/name)==proof['output_sha256'][name]
with (prepared/'fluid.smesh').open() as stream:count=int(stream.readline().split()[0])
with (prepared/'fluid.mtr').open() as stream:
    assert list(map(int,stream.readline().split()))==[count,1];sizes=np.loadtxt(stream)
assert sizes.shape==(count,) and np.isfinite(sizes).all() and np.all(sizes>0)
checker=Path('/home/lolman/935-cfd-pilot-20261022/check-si-surface');assert sha(checker)=='69caa50a446cfef290a2735be90076aa4ea17907a2507e611704f68fddcd6ede'
check=subprocess.run([str(checker),str(prepared/'boundary.obj')],capture_output=True,text=True,timeout=120)
(out/'CGAL.stdout').write_text(check.stdout);(out/'CGAL.stderr').write_text(check.stderr)
assert check.returncode==0 and json.loads(check.stdout)['self_intersection_pairs']==0
for name in ['fluid.smesh','fluid.mtr']:shutil.copyfile(prepared/name,out/name)
binary=Path('/home/lolman/935-analysis-volume-20261022/upstream-tetgen-1.5.1/tetgen');assert sha(binary)=='fffee20ba554ea4417591dbbbbc4632d724520b2f06e8a78432cb7f22ef5cfec'
command=[str(binary),'-pq1.4/10mO4/7S500000zCf','fluid.smesh']

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

started=time.monotonic();reason=None
with (out/'tetgen.stdout').open('x') as stdout,(out/'tetgen.stderr').open('x') as stderr:
    process=subprocess.Popen(command,cwd=out,stdout=stdout,stderr=stderr,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=600)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
metric_consumed='Opening fluid.mtr' in (out/'tetgen.stdout').read_text()
record={'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'command':command,'binary_sha256':sha(binary),'source_sha256':sha(__file__),'prepared_receipt_sha256':sha(prepared/'receipt.json'),'input_smesh_sha256':sha(prepared/'fluid.smesh'),'metric_sha256':sha(prepared/'fluid.mtr'),'metric_opened_by_native_mesher':metric_consumed,'inputs_unchanged':all(sha(out/name)==sha(prepared/name) for name in ['fluid.smesh','fluid.mtr']),'memory_limit_GiB':8,'timeout_s':600,'maximum_added_Steiner_points':500000,'boundary_retriangulation_permitted_but_not_admitted':True,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
assert record['inputs_unchanged'];raise SystemExit(0 if code==0 and metric_consumed else 1)
