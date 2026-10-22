"""Prepare and qualify the analytic cube before the real rotor dualisation."""
import json,resource,shutil,subprocess,time
from pathlib import Path
from prepare_conforming_surface import sha
from check_cube_dual import check

p=Path('/home/lolman/935-surface-facet-repair-20261022');case=p/'cube-input-001';case.mkdir(mode=0o700);(case/'system').mkdir();old=p/'fluid-native-001/system/meshQualityDict';assert sha(old)=='bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d';shutil.copyfile(old,case/'system/meshQualityDict')
header=lambda name:'FoamFile\n{format ascii;class dictionary;object '+name+';}\n'
(case/'system/controlDict').write_text(header('controlDict')+'application blockMesh;startFrom startTime;startTime 0;stopAt endTime;endTime 1;deltaT 1;writeControl timeStep;writeInterval 1;writePrecision 17;functions {};\n')
(case/'system/blockMeshDict').write_text(header('blockMeshDict')+'''convertToMeters 1;
vertices ((-.5 -.5 -.5)(.5 -.5 -.5)(.5 .5 -.5)(-.5 .5 -.5)(-.5 -.5 .5)(.5 -.5 .5)(.5 .5 .5)(-.5 .5 .5));
blocks (hex (0 1 2 3 4 5 6 7) (6 6 6) simpleGrading (1 1 1));
edges ();
boundary (
inlet {type patch;faces ((4 5 6 7));}
outlet {type patch;faces ((0 3 2 1));}
duct {type wall;faces ((0 4 7 3)(0 1 5 4)(3 7 6 2));}
rotor {type wall;faces ((1 2 6 5));}
);
mergePatchPairs ();
''')
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d';runtime=json.loads(pre.read_text());command=list(runtime['command']);command[command.index('--bind')+1]=str(case);assert '--unshare-all' in command and '--share-net' not in command
command[-1]='''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
test "$WM_PROJECT_VERSION" = 13
blockMesh -case /workspace > /workspace/log.blockMesh 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1
'''
def limits():resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))
started=time.monotonic()
with (case/'runtime.log').open('x') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=60,preexec_fn=limits)
assert result.returncode==0;proof=check(case,p/'export-fluid-plc-005.py');assert proof['native_full_quality_passed']
r={'status':'native_cube_control_prepared','source_sha256':sha(__file__),'runtime_sha256':sha(pre),'image_index_sha256':runtime['image_index_sha256'],'elapsed_s':time.monotonic()-started,'cube_geometry_readback_sha256':sha(case/'geometry-readback.json'),'full_native_quality_passed':True,'original_quality_dictionary_unchanged':sha(case/'system/meshQualityDict')==sha(old),'CFD_accepted':False,'manufacturing_authorized':False};(case/'execution.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
