"""Export the saved castellated rotor boundary for diagnostic visualization only."""
import hashlib,json,os,resource,shutil,signal,subprocess,time
from pathlib import Path

p=Path('/home/lolman/935-local-relocation-20261022');source=p/'hex-native-001';out=p/'castellation-review-001'
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
proof=json.loads((source/'execution.json').read_text())
assert proof['stop_reason']=='wall_time_limit' and proof['source_template_unchanged']
originals={str(f.relative_to(source)):sha(f) for base in ['constant','system'] for f in sorted((source/base).rglob('*')) if f.is_file()}
out.mkdir(mode=0o700)
for base in ['constant','system']:shutil.copytree(source/base,out/base)
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
command=list(json.loads(pre.read_text())['command']);command[command.index('--bind')+1]=str(out)
assert '--unshare-all' in command and '--share-net' not in command
command[-1]='''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
foamToVTK -case /workspace -constant -noInternal -noPointValues -fields '()' -ascii > /workspace/log.foamToVTK 2>&1
foamToSurface -case /workspace -constant -tri /workspace/boundary.obj > /workspace/log.foamToSurface 2>&1
'''

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

started=time.monotonic();reason=None
with (out/'runtime.log').open('x') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=600)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
r={'source_sha256':sha(__file__),'qualified_runtime_sha256':sha(pre),'parent_execution_sha256':sha(source/'execution.json'),'parent_checkpoint_unchanged':all(sha(source/name)==expected for name,expected in originals.items()),'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'network_isolation_unchanged':True,'diagnostic_visualization_only':True,'native_full_quality_passed':False,'geometry_export_verified':False,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
assert code==0 and r['parent_checkpoint_unchanged']
