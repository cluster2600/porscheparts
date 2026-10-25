"""Continue snapping only on the validated four-way decomposition; retain all admission gates."""
import hashlib,json,os,resource,signal,subprocess,time
from pathlib import Path

p=Path('/home/lolman/935-local-relocation-20261022');out=Path('/home/lolman/935-snap-resume-20261025/parallel-snap-001');proof=json.loads((out/'preparation.json').read_text());assert proof['exit']==0 and proof['refinement_metadata_validated'] and proof['all_source_cells_assigned_once'] and proof['castellation_reused']
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert not (out/'execution.json').exists();assert sha(out/'system/meshQualityDict')=='bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d'
for row in proof['processor_level_fields']:assert sha(out/f'processor{row["rank"]}/constant/polyMesh'/f'{row["kind"]}Level')==row['sha256']
text=(out/'system/snappyHexMeshDict').read_text();assert 'castellatedMesh false;' in text and 'snap true;' in text and 'addLayers false;' in text and 'minFaceWeight 0.05;' in text
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
command=list(json.loads(pre.read_text())['command']);command[command.index('--bind')+1]=str(out);assert '--unshare-all' in command and '--share-net' not in command
command[-1]='''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
mpirun --mca btl self,vader --mca pml ob1 -np 4 prlimit --as=3221225472 -- snappyHexMesh -case /workspace -parallel -overwrite > /workspace/log.parallelSnap 2>&1
reconstructParMesh -case /workspace -constant > /workspace/log.reconstruct 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1
'''

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,12*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

started=time.monotonic();reason=None
with (out/'runtime.log').open('x') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=3600)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
quality=(out/'log.checkMesh.allGeometry').read_text() if (out/'log.checkMesh.allGeometry').is_file() else ''
record={'source_sha256':sha(__file__),'preparation_sha256':sha(out/'preparation.json'),'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'four_ranks':True,'worker_address_space_limit_GiB':3,'timeout_s':3600,'network_isolation_unchanged':True,'castellation_reused':True,'layers_executed':False,'quality_dictionary_unchanged':sha(out/'system/meshQualityDict')=='bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d','extended_native_quality_passed':'Mesh OK.' in quality and 'Failed' not in quality,'parent_checkpoint_unchanged':all(sha(p/'hex-native-001'/name)==expected for name,expected in proof['source_mesh_and_system_sha256'].items()),'complete_wall_and_volume_admission_pending':True,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
assert record['parent_checkpoint_unchanged'];raise SystemExit(0 if code==0 else 1)
