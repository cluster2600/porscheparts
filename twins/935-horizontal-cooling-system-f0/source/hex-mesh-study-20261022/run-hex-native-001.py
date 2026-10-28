"""Run bounded native adaptive-hex meshing and the unchanged full quality check."""
import hashlib,json,os,resource,shutil,signal,subprocess,sys,time
from pathlib import Path

source,out=map(Path,sys.argv[1:]);assert not out.exists() and not out.is_symlink()
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
proof=json.loads((source/'receipt.json').read_text());assert proof['quality_dictionary_unchanged']
for name,expected in proof['files_sha256'].items():assert sha(source/name)==expected
out.mkdir(mode=0o700);shutil.copytree(source/'system',out/'system');shutil.copytree(source/'constant',out/'constant')
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
runtime=json.loads(pre.read_text());command=list(runtime['command']);command[command.index('--bind')+1]=str(out);assert '--unshare-all' in command and '--share-net' not in command
command[-1]='''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
blockMesh -case /workspace > /workspace/log.blockMesh 2>&1
snappyHexMesh -case /workspace -overwrite > /workspace/log.snappyHexMesh 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1
'''

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,12*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

started=time.monotonic();reason=None
with (out/'runtime.log').open('x') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=1200)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
quality=(out/'log.checkMesh.allGeometry').read_text() if (out/'log.checkMesh.allGeometry').is_file() else ''
record={'source_sha256':sha(__file__),'template_receipt_sha256':sha(source/'receipt.json'),'qualified_runtime_sha256':sha(pre),'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'memory_limit_GiB':12,'timeout_s':1200,'quality_dictionary_unchanged':sha(out/'system/meshQualityDict')==sha(source/'system/meshQualityDict'),'source_template_unchanged':all(sha(source/name)==expected for name,expected in proof['files_sha256'].items()),'extended_native_quality_passed':'Mesh OK.' in quality and 'Failed' not in quality,'complete_wall_and_volume_admission_pending':True,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
assert record['source_template_unchanged'];raise SystemExit(0 if code==0 else 1)
