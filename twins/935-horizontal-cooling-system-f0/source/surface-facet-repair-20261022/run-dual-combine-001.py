"""Test native dualisation on a fresh copy; keep every original quality threshold."""
import hashlib,json,os,resource,shutil,signal,subprocess,sys,time
from pathlib import Path
source,out=map(Path,sys.argv[1:]);assert not out.exists() and not out.is_symlink();out.mkdir(mode=0o700);shutil.copytree(source/'constant/polyMesh',out/'constant/polyMesh',ignore=shutil.ignore_patterns('sets'));shutil.copytree(source/'system',out/'system')
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
readback=json.loads((source/'geometry-readback.json').read_text());assert all(sha(source/'constant/polyMesh'/name)==expected for name,expected in readback['native_mesh_sha256'].items())
inputs={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()};(out/'preparation.json').write_text(json.dumps({'source_sha256':sha(__file__),'source_execution_sha256':sha(source/'execution.json'),'initial_mesh_and_system_sha256':inputs,'feature_angle_degrees':30,'concave_multi_cells':True,'split_all_faces':False,'coplanar_patch_merge':True,'merge_feature_angle_degrees':.000001,'merge_concavity_angle_degrees':.000001,'CFD_accepted':False},indent=2)+'\n')
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');runtime=json.loads(pre.read_text());assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d';command=list(runtime['command']);command[command.index('--bind')+1]=str(out)
assert '--unshare-all' in command and '--share-net' not in command
command[-1]='''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
polyDualMesh -case /workspace -overwrite -concaveMultiCells 30 > /workspace/log.polyDualMesh 2>&1
combinePatchFaces -case /workspace -meshQuality -concaveAngle 0.000001 0.000001 > /workspace/log.combinePatchFaces 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1
'''
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(10*1024**3,10*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))
t=time.monotonic();reason=None
with (out/'runtime.log').open('x') as log:
 p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
 try:code=p.wait(timeout=600)
 except subprocess.TimeoutExpired:
  reason='wall_time_limit';os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  code=p.returncode
check=(out/'log.checkMesh.allGeometry').read_text() if (out/'log.checkMesh.allGeometry').is_file() else ''
report={'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-t,'source_sha256':sha(__file__),'extended_mesh_quality_passed':'Mesh OK.' in check and 'Failed' not in check,'source_geometry_readback_sha256':sha(source/'geometry-readback.json'),'parent_mesh_and_system_unchanged':all(sha(source/name)==expected for name,expected in inputs.items()),'memory_limit_GiB':10,'timeout_s':600,'quality_dictionary_unchanged':sha(out/'system/meshQualityDict')==sha(source/'system/meshQualityDict'),'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'execution.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

assert report['parent_mesh_and_system_unchanged']
raise SystemExit(0 if code==0 else 1)
