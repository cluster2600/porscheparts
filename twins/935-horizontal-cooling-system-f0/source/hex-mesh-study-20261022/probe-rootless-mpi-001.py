"""Probe local MPI availability without changing the qualified network isolation."""
import hashlib,json,os,resource,signal,subprocess,time
from pathlib import Path

p=Path('/home/lolman/935-local-relocation-20261022');out=p/'mpi-probe-001';out.mkdir(mode=0o700)
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
runtime=json.loads(pre.read_text());command=list(runtime['command']);command[command.index('--bind')+1]=str(out);assert '--unshare-all' in command and '--share-net' not in command
command[-1]='source /opt/openfoam13/etc/bashrc >/dev/null 2>&1\nset -euo pipefail\nmpirun --version\nmpirun --mca btl self,vader --mca pml ob1 -np 2 /bin/true\n'

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))

started=time.monotonic();reason=None
with (out/'runtime.log').open('x') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
r={'source_sha256':sha(__file__),'qualified_runtime_sha256':sha(pre),'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'network_isolation_unchanged':True,'two_local_ranks_started':code==0,'actual_parallel_mesh_control_passed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
