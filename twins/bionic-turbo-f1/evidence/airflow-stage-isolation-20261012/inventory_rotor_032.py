import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from rotor_shell_inventory import inventory
from audit_interface_corridor import read_patches
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from prepare_case import sha
case=Path('work/bionic-airflow-20261012/baseline-castellated-032');manifest=json.loads((case/'case-manifest.json').read_text())
receipt=json.loads((case/'run-mesh.json').read_text());assert receipt['case_manifest_sha256']==sha(case/'case-manifest.json')
triangles=read_patches(case/'constant/triSurface/domain.stl',manifest['surface'])['rotor']
points,indices=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
source=inventory(points,indices.reshape(-1,3));del triangles,points,indices
mesh=case/'constant/polyMesh'
for name in ('points','faces','boundary'):assert sha(mesh/name)==receipt['output_sha256']['constant/polyMesh/'+name]
x=re.search(r'\brotor\s*\{([^{}]*)\}',(mesh/'boundary').read_text());assert x
start=int(re.search(r'startFace\s+(\d+)',x[1])[1]);count=int(re.search(r'nFaces\s+(\d+)',x[1])[1])
points=ascii_list((mesh/'points').read_text(),True)*1000
faces=[f for i,f in enumerate(ascii_faces((mesh/'faces').read_text())) if start<=i<start+count];assert len(faces)==count
native=inventory(points,faces)
report=dict(source_sha256=sha(Path(__file__)),inventory_source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/rotor_shell_inventory.py')),surface_sha256=manifest['surface']['sha256'],native_mesh_sha256={n:sha(mesh/n) for n in ('points','faces','boundary')},source_rotor_components=source,native_032_rotor_components=native,coordinates_mm=True,geometry_only=True,performance_ranking_authorized=False)
with Path(__file__).with_name('rotor-inventory-032.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2),flush=True)
