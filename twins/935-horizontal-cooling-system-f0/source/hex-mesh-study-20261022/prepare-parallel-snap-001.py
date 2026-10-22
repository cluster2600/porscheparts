"""Resume the stopped case from its saved mesh, retaining refinement metadata on four ranks."""
import hashlib,json,os,re,resource,shutil,signal,subprocess,time
from pathlib import Path
import numpy as np
from import_conforming_volume import helper

p=Path('/home/lolman/935-local-relocation-20261022');source=p/'hex-native-001';out=p/'parallel-snap-001'
assert not out.exists() and not out.is_symlink()
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
parent=json.loads((source/'execution.json').read_text());assert parent['stop_reason']=='wall_time_limit' and parent['source_template_unchanged']
control=p/'parallel-cube-001';proof=json.loads((control/'geometry-readback.json').read_text());assert proof['native_full_quality_passed'] and proof['cells']==216 and proof['volume_absolute_error_from_analytic_unit_cube']<1e-12
parser_path=Path('/home/lolman/935-surface-facet-repair-20261022/export-fluid-plc-005.py');assert sha(parser_path)=='f50f4cd315c757d9d2c291640f49bfd1a6107a1de851685f8c407e47c33883cb'
ascii=helper(parser_path,'parallel_resume_ascii')

def labels(path):
    count,body=ascii.foam_list(path,maximum_count=10_000_000);values=np.fromstring(body,sep=' ',dtype=np.int64)
    assert values.shape==(count,) and np.all(values>=0)
    return values

originals={str(f.relative_to(source)):sha(f) for base in ['constant','system'] for f in sorted((source/base).rglob('*')) if f.is_file()}
mesh=source/'constant/polyMesh';cell_levels=labels(mesh/'cellLevel');point_levels=labels(mesh/'pointLevel')
with (mesh/'points').open() as stream:
    for _ in range(200):
        line=stream.readline().strip()
        if re.fullmatch(r'\d+',line):assert int(line)==len(point_levels);break
    else:raise ValueError('Native point count not found')
with (mesh/'owner').open() as stream:header=stream.read(2048)
assert int(re.search(r'nCells:\s*(\d+)',header)[1])==len(cell_levels)
out.mkdir(mode=0o700);shutil.copytree(source/'constant',out/'constant');shutil.copytree(source/'system',out/'system')
snappy=out/'system/snappyHexMeshDict';text=snappy.read_text()
for before,after in [('castellatedMesh true;','castellatedMesh false;'),('addLayers true;','addLayers false;'),('#include "meshQualityDict"','#include "meshQualityDict"\n    minFaceWeight 0.05;')]:
    assert text.count(before)==1;text=text.replace(before,after)
snappy.write_text(text)
(out/'system/decomposeParDict').write_text('FoamFile {format ascii;class dictionary;object decomposeParDict;}\nnumberOfSubdomains 4; method scotch;\n')
pre=Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json');assert sha(pre)=='1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
command=list(json.loads(pre.read_text())['command']);command[command.index('--bind')+1]=str(out);command[-1]='source /opt/openfoam13/etc/bashrc >/dev/null 2>&1\nset -euo pipefail\ncommand -v prlimit\ndecomposePar -case /workspace -noFields > /workspace/log.decomposePar 2>&1\n'
assert '--unshare-all' in command and '--share-net' not in command

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,12*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

started=time.monotonic();reason=None
with (out/'preparation-runtime.log').open('x') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try:code=process.wait(timeout=300)
    except subprocess.TimeoutExpired:
        reason='wall_time_limit';os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        code=process.returncode
record={'source_sha256':sha(__file__),'parent_execution_sha256':sha(source/'execution.json'),'source_mesh_and_system_sha256':originals,'parallel_cube_readback_sha256':sha(control/'geometry-readback.json'),'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'source_mesh_unchanged':all(sha(source/name)==expected for name,expected in originals.items()),'castellation_reused':True,'layers_requested_in_this_stage':False,'snapping_creation_minimum_face_weight':.05,'quality_dictionary_unchanged':sha(out/'system/meshQualityDict')==sha(source/'system/meshQualityDict'),'refinement_metadata_validated':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'preparation.json').write_text(json.dumps(record,indent=2)+'\n');assert code==0
cell_parts=[];results=[]
for rank in range(4):
    folder=out/f'processor{rank}/constant/polyMesh';addresses={kind:labels(folder/(kind+'ProcAddressing')) for kind in ['cell','point']};cell_parts.append(addresses['cell'])
    for kind,global_levels in [('cell',cell_levels),('point',point_levels)]:
        address=addresses[kind];assert len(np.unique(address))==len(address) and address.max()<len(global_levels);expected=global_levels[address];target=folder/(kind+'Level');created=not target.exists()
        if created:
            with (mesh/(kind+'Level')).open() as stream:global_header=re.search(r'FoamFile\s*\{[^{}]*\}',stream.read(2048))[0]
            with target.open('x') as stream:stream.write(global_header+f'\n{len(expected)}\n(\n');np.savetxt(stream,expected,fmt='%d');stream.write(')\n')
        assert np.array_equal(labels(target),expected);results.append({'rank':rank,'kind':kind,'values':len(expected),'created_from_exact_addressing':created,'sha256':sha(target)})
    target=folder/'level0Edge'
    if not target.exists():shutil.copyfile(mesh/'level0Edge',target)
    assert sha(target)==sha(mesh/'level0Edge')
all_cells=np.concatenate(cell_parts);assert np.array_equal(np.sort(all_cells),np.arange(len(cell_levels)))
record.update(refinement_metadata_validated=True,global_cells=len(cell_levels),global_points=len(point_levels),processor_level_fields=results,all_source_cells_assigned_once=True,source_mesh_unchanged=all(sha(source/name)==expected for name,expected in originals.items()))
(out/'preparation.json').write_text(json.dumps(record,indent=2)+'\n');assert record['source_mesh_unchanged'];print(json.dumps({k:v for k,v in record.items() if k!='source_mesh_and_system_sha256'}),flush=True)
