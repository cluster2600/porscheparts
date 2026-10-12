"""Independently bound every rotor facet inside the proposed faceted zone."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_interface_corridor import read_patches
from prepare_case import sha
base=Path(__file__).resolve().parent;path=base/'geometry-027.json';report=json.loads(path.read_text())
nodes=np.array(report['profile']['nodes_z_radius_mm']);cosine=math.cos(math.pi/report['profile']['sectors']);results={}
for label,case in (('baseline','baseline-conformal-022'),('candidate','candidate-parallel-014')):
    root=Path('work/bionic-airflow-20261012')/case;manifest=root/'case-manifest.json'
    assert sha(manifest)==report['variants'][label]['case_manifest_sha256']
    info=json.loads(manifest.read_text())['surface'];triangles=read_patches(root/'constant/triSurface/domain.stl',info)['rotor']
    lo=triangles[:,:,2].min(axis=1);hi=triangles[:,:,2].max(axis=1);rmax=np.linalg.norm(triangles[:,:,:2],axis=2).max(axis=1)+1e-8
    assert lo.min()>nodes[0,0] and hi.max()<nodes[-1,0]
    covered=np.zeros(len(triangles),dtype=bool);margin=float('inf')
    for a,b in zip(nodes[:-1],nodes[1:]):
        selected=(lo<=b[0]+1e-8)&(hi>=a[0]-1e-8)
        if selected.any():
            separation=min(a[1],b[1])*cosine-float(rmax[selected].max())
            assert separation>0
            margin=min(margin,separation);covered|=selected
    assert covered.all()
    results[label]=dict(surface_sha256=info['sha256'],rotor_triangles=len(triangles),all_facets_bounded_inside=True,
                        minimum_radial_separation_mm=margin,axial_bounds_mm=[float(lo.min()),float(hi.max())],
                        rotor_float64_mm_sha256=hashlib.sha256(triangles.astype('<f8').tobytes()).hexdigest())
result=dict(source_sha256=sha(Path(__file__)),geometry_report_sha256=sha(path),variants=results,
            rotor_arrays_identical=results['baseline']['rotor_float64_mm_sha256']==results['candidate']['rotor_float64_mm_sha256'],
            interpretation='Full-facet conservative enclosure of all current CFD rotor boundary triangles. Does not qualify cell ownership after meshing or physical clearances.',performance_ranking_authorized=False)
with (base/'rotor-enclosure.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
