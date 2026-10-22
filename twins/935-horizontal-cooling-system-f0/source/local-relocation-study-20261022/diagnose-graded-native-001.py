"""Diagnose native quality only; geometric/volume admission of the remeshed wall is pending."""
import hashlib,json,os,re,resource,shutil,signal,subprocess,sys,time
from pathlib import Path
meshed,case=map(Path,sys.argv[1:]);assert not case.exists() and not case.is_symlink();proof=json.loads((meshed/'execution.json').read_text());assert proof['exit']==0 and proof['inputs_unchanged'] and proof['metric_opened_by_native_mesher'];case.mkdir(mode=0o700);(case/'system').mkdir()
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
for suffix in ['node','ele','face']:shutil.copyfile(meshed/f'fluid.1.{suffix}',case/f'fluid.1.{suffix}')
old=Path('/home/lolman/935-cfd-pilot-20261022/rotor-003/coarse/system')
for name in ['fvSchemes','fvSolution','meshQualityDict']:shutil.copyfile(old/name,case/'system'/name)
header=lambda n:'FoamFile\n{format ascii;class dictionary;object '+n+';}\n'
(case/'system/controlDict').write_text(header('controlDict')+'application tetgenToFoam;startFrom startTime;startTime 0;stopAt endTime;endTime 1;deltaT 1;writeControl timeStep;writeInterval 1;writePrecision 17;functions {};\n')
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d';runtime=json.loads(pre.read_text());base=list(runtime['command']);base[base.index('--bind')+1]=str(case);assert '--unshare-all' in base and '--share-net' not in base

def limits():
 resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

def execute(script,name):
 command=list(base);command[-1]='source /opt/openfoam13/etc/bashrc >/dev/null 2>&1\nset -euo pipefail\ntest "$WM_PROJECT_VERSION" = 13\n'+script
 with (case/name).open('x') as log:
  p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
  try:code=p.wait(timeout=300)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   raise
 assert code==0,(name,code)

t=time.monotonic();execute('tetgenToFoam -case /workspace /workspace/fluid.1\n','log.tetgenToFoam')
rows=re.findall(r'Mapping tetgen region (\d+) to Foam patch (\d+)',(case/'log.tetgenToFoam').read_text());mapping={int(a):int(b) for a,b in rows};assert set(mapping)=={1,2,3,4} and len(set(mapping.values()))==4
text=header('createPatchDict')+'pointSync false;\npatches (\n'
for marker,name,kind in [(1,'inlet','patch'),(2,'outlet','patch'),(3,'duct','wall'),(4,'rotor','wall')]:text+=f'{{name {name};patchInfo {{type {kind};}}constructFrom patches;patches (patch{mapping[marker]});}}\n'
(case/'system/createPatchDict').write_text(text+');\n')
execute('createPatch -case /workspace -overwrite > /workspace/log.createPatch 2>&1\ncheckMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1\n','runtime.check.log')
check=(case/'log.checkMesh.allGeometry').read_text();passed='Mesh OK.' in check and 'Failed' not in check
report={'status':'diagnostic_native_quality_only_geometry_volume_admission_pending','elapsed_s':time.monotonic()-t,'source_sha256':sha(__file__),'mesher_execution_sha256':sha(meshed/'execution.json'),'geometry_and_volume_admission_complete':False,'qualified_runtime_sha256':sha(pre),'image_index_sha256':runtime['image_index_sha256'],'tetgen_region_to_imported_patch':mapping,'original_quality_dictionary_unchanged':sha(case/'system/meshQualityDict')==sha(old/'meshQualityDict'),'extended_mesh_quality_passed':passed,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False,'result_sha256':{str(p.relative_to(case)):sha(p) for p in sorted(case.rglob('*')) if p.is_file()}}
(case/'execution.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='result_sha256'}),flush=True)
