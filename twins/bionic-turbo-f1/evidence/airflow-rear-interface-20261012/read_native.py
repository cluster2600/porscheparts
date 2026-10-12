"""Read all native outputs, then measure polygonal interfaces and final fields."""
import json
from pathlib import Path
import re
import sys
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from audit_frame_interface import face_geometry
from run_case import ascii_faces
from prepare_case import sha


def internal(text,count,components):
    m=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    if m:
        assert m[1]==('vector' if components==3 else 'scalar') and int(m[2])==count
        a=np.fromstring(m[3].translate(str.maketrans('()','  ')),sep=' ')
        assert a.size==count*components
        a=a.reshape(count,components)
    else:
        m=re.search(r'internalField\s+uniform\s+([^;]+);',text);assert m
        a=np.fromstring(m[1].translate(str.maketrans('()','  ')),sep=' ')
        assert a.size==components
        a=np.tile(a,(count,1))
    assert np.isfinite(a).all()
    return a


assert internal('internalField uniform (0 0 0);',4,3).shape==(4,3)
for bad in ('internalField nonuniform List<scalar> 4 (1 2);','internalField uniform nan;'):
    try:internal(bad,4,1)
    except AssertionError:pass
    else:raise AssertionError('Invalid field accepted')
from audit_diagnostic import scalar_patch
from audit_interface_corridor import geometry
case=Path('work/bionic-airflow-20261012/static-mrf-rear-028/variable-radius')
manifest=json.loads((case/'manifest.json').read_text());receipt=json.loads((case/'report.json').read_text())
assert receipt['native_exit_code']==0 and receipt['stationary_equilibrium_reproduced']
assert sha(case/'manifest.json')==receipt['manifest_sha256']
assert all(sha(case/name)==digest for name,digest in receipt['output_sha256'].items())
spec=manifest['rear_witness'];count=spec['expected_cells'];mesh=case/'constant/polyMesh'
owner=ascii_list((mesh/'owner').read_text()).astype(np.int64)
neighbour=ascii_list((mesh/'neighbour').read_text()).astype(np.int64)
points=ascii_list((mesh/'points').read_text(),True);faces=list(ascii_faces((mesh/'faces').read_text()))
assert max(owner.max(),neighbour.max())+1==count
m=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);assert m
zone=np.fromstring(m[2],sep=' ',dtype=np.int64)
assert len(zone)==int(m[1])==spec['expected_rotating_cells'] and len(np.unique(zone))==len(zone)
assert zone.min()>=0 and zone.max()<count
active=np.isin(owner[:len(neighbour)],zone);selected=np.flatnonzero(active^np.isin(neighbour,zone))
assert len(selected)==spec['expected_interface_faces']
values=[]
for i in selected:
    c,s=face_geometry(points[list(faces[i])]);q=float(np.dot(np.cross([0,0,manifest['omega_rad_s']],c),s))
    values.append((abs(q),abs(q)/np.linalg.norm(s)))
boundary=(mesh/'boundary').read_text();m=re.search(r'\bstator\s*\{([^{}]*)\}',boundary);assert m
start=int(re.search(r'startFace\s+(\d+)',m[1])[1]);n=int(re.search(r'nFaces\s+(\d+)',m[1])[1]);assert n==spec['expected_stator_faces']
polygons=[points[list(f)] for f in faces[start:start+n]]
assert all(p.shape==(4,3) and np.all(p[:,2]==-.00375) for p in polygons)
triangles=np.array([t for p in polygons for t in (p[[0,1,2]],p[[0,2,3]])])*1000
minimum=float(geometry.projected_min_radius(triangles).min());maximum=float(np.linalg.norm(triangles[:,:,:2],axis=2).max())
geo=Path('twins/bionic-turbo-f1/evidence/airflow-rear-interface-20261012/geometry-027.json')
assert sha(geo)==spec['geometry_report_sha256'];g=json.loads(geo.read_text())
for v in g['variants'].values():
    assert v['annulus']['annulus_inner_radius_mm']<minimum<maximum<v['annulus']['annulus_outer_radius_mm']
area=sum(np.linalg.norm(face_geometry(p)[1]) for p in polygons)
width=spec['shell_half_width_mm'];N=spec['sectors']
expected=N/2*np.sin(2*np.pi/N)*((32+width)**2-(32-width)**2)*1e-6
assert abs(area-expected)<=expected*1e-12
phi=scalar_patch((case/'2e-05/phi').read_text(),'stator',n)
result=dict(source_sha256=sha(Path(__file__)),receipt_sha256=sha(case/'report.json'),all_native_payloads_read_and_hashed=True,
            cells=count,rotating_cells=len(zone),interface_faces=len(values),gross_geometric_frame_flux_m3_s=sum(x[0] for x in values),
            max_normal_frame_speed_m_s=max(x[1] for x in values),native_stator_faces=n,native_stator_area_m2=float(area),
            stator_radial_extent_mm=[minimum,maximum],stator_exactly_on_source_plane=True,all_stator_facets_covered_by_both_source_annuli=True,
            stator_gross_mass_flux_kg_s=float(np.abs(phi).sum()),stator_net_mass_flux_kg_s=float(phi.sum()),fields={},
            observed=receipt['observed'],equilibrium_passed=True,pressure_linear_iteration_cap_hits=receipt['pressure_linear_iteration_cap_hits'],
            solver_admission_granted_for_full_turbo=False,performance_ranking_authorized=False)
for name,n in (('p',1),('T',1),('U',3)):
    path=case/'2e-05'/name;a=internal(path.read_text(),count,n);values=np.linalg.norm(a,axis=1) if n==3 else a[:,0]
    result['fields'][name]=dict(sha256=sha(path),cells=len(a),min=float(values.min()),max=float(values.max()))
with (Path(__file__).parent/'native-readback.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(result,indent=2))
