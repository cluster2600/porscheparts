"""Qualify isolated four-rank decomposition/check/reconstruction on the analytic cube."""
import hashlib,json,os,resource,shutil,signal,subprocess,time
from pathlib import Path

p=Path('/home/lolman/935-local-relocation-20261022');source=Path('/home/lolman/935-surface-facet-repair-20261022/cube-input-001');out=p/'parallel-cube-001';out.mkdir(mode=0o700)
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
readback=json.loads((source/'geometry-readback.json').read_text());assert sha(source/'geometry-readback.json')=='46987601c17d2681bbea7893f520df3a161d200236a38066c8f9d1d5ce51a903'
for name,expected in readback['native_mesh_sha256'].items():assert sha(source/'constant/polyMesh'/name)==expected
shutil.copytree(source/'constant',out/'constant');shutil.copytree(source/'system',out/'system')
(out/'system/decomposeParDict').write_text('FoamFile {format ascii;class dictionary;object decomposeParDict;}\nnumberOfSubdomains 4; method scotch;\n')
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
command=list(json.loads(pre.read_text())['command']);command[command.index('--bind')+1]=str(out);assert '--unshare-all' in command and '--share-net' not in command
command[-1]='''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
decomposePar -case /workspace -noFields > /workspace/log.decomposePar 2>&1
mpirun --mca btl self,vader --mca pml ob1 -np 4 checkMesh -case /workspace -parallel -allGeometry -allTopology -meshQuality > /workspace/log.parallelCheck 2>&1
reconstructParMesh -case /workspace -constant > /workspace/log.reconstruct 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1
'''

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))

started=time.monotonic();reason=None
with (out/'runtime.log').open('x') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
logs={name:(out/name).read_text() if (out/name).is_file() else '' for name in ['log.parallelCheck','log.checkMesh.allGeometry']}
record={'source_sha256':sha(__file__),'source_readback_sha256':sha(source/'geometry-readback.json'),'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'four_ranks':True,'network_isolation_unchanged':True,'native_parallel_and_reconstructed_quality_passed':all('Mesh OK.' in text and 'Failed' not in text for text in logs.values()),'source_primitives_unchanged':all(sha(source/'constant/polyMesh'/name)==expected for name,expected in readback['native_mesh_sha256'].items()),'analytic_boundary_readback_pending':True,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
assert record['source_primitives_unchanged'];raise SystemExit(0 if code==0 else 1)
