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
results=[]
for trial in ('024','025'):
    cases=[Path('work/bionic-airflow-20261012/static-mrf-profile-'+trial)/name for name in ('inertial','variable-radius')]
    manifests=[json.loads((c/'manifest.json').read_text()) for c in cases]
    differences=[name for name,digest in manifests[0]['file_sha256'].items() if digest!=manifests[1]['file_sha256'][name]]
    assert differences==['constant/MRFProperties'],differences
    for case,manifest in zip(cases,manifests):
        receipt=json.loads((case/'report.json').read_text())
        assert sha(case/'manifest.json')==receipt['manifest_sha256']
        assert all(sha(case/name)==digest for name,digest in receipt['output_sha256'].items())
        count=manifest['profile_witness']['expected_cells'];mesh=case/'constant/polyMesh'
        owner=ascii_list((mesh/'owner').read_text()).astype(np.int64)
        neighbour=ascii_list((mesh/'neighbour').read_text()).astype(np.int64)
        points=ascii_list((mesh/'points').read_text(),True)
        assert max(owner.max(),neighbour.max())+1==count
        m=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);assert m
        zone=np.fromstring(m[2],sep=' ',dtype=np.int64)
        assert len(zone)==int(m[1])==manifest['profile_witness']['expected_rotating_cells']
        assert len(np.unique(zone))==len(zone) and zone.min()>=0 and zone.max()<count
        active=np.isin(owner[:len(neighbour)],zone)
        selected=set(np.flatnonzero(active^np.isin(neighbour,zone)))
        assert len(selected)==manifest['profile_witness']['expected_interface_faces']
        values=[]
        for i,face in enumerate(ascii_faces((mesh/'faces').read_text())):
            if i in selected:
                c,s=face_geometry(points[list(face)])
                q=float(np.dot(np.cross([0,0,10471.975511966],c),s))
                values.append((abs(q),abs(q)/np.linalg.norm(s)))
        assert len(values)==len(selected)
        result=dict(case=str(case),receipt_sha256=sha(case/'report.json'),native_exit_code=receipt['native_exit_code'],
                    all_native_payloads_read_and_hashed=True,cells=count,rotating_cells=len(zone),interface_faces=len(values),
                    paired_input_differences=differences,
                    geometric_test_omega_rad_s=10471.975511966,
                    gross_geometric_frame_flux_m3_s=sum(x[0] for x in values),max_normal_frame_speed_m_s=max(x[1] for x in values),fields={})
        if receipt['native_exit_code']==0:
            for name,n in (('p',1),('T',1),('U',3)):
                p=case/'2e-05'/name;a=internal(p.read_text(),count,n)
                magnitude=np.linalg.norm(a,axis=1) if n==3 else a[:,0]
                result['fields'][name]=dict(sha256=sha(p),cells=len(a),min=float(magnitude.min()),max=float(magnitude.max()))
            result.update(observed=receipt['observed'],equilibrium_passed=receipt['stationary_equilibrium_reproduced'],pressure_linear_iteration_cap_hits=receipt['pressure_linear_iteration_cap_hits'])
        else:
            assert not (case/'log.rhoPimpleFoam').exists()
        results.append(result)
out=Path('twins/bionic-turbo-f1/evidence/airflow-profile-interface-20261012/native-readback.json')
with out.open('x') as f:json.dump(dict(source_sha256=sha(Path(__file__)),cases=results,performance_ranking_authorized=False),f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(results,indent=2))
