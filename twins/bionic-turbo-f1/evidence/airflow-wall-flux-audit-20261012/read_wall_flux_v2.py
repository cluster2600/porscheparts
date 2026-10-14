"""Read-only final-density reconstruction, not an assembly-time flux certificate."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry

def wall_scalar(text,count):
    m=re.search(r'\bwalls\s*\{([^{}]*)\}',text,re.S)
    assert m
    a=re.search(r'\bvalue\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',m[1],re.S)
    assert a and int(a[1])==count
    values=np.fromstring(a[2],sep=' ')
    assert len(values)==count and np.isfinite(values).all()
    return values
assert np.array_equal(wall_scalar('walls {value nonuniform List<scalar> 2 (1 2);}',2),[1,2])
try:wall_scalar('walls {value nonuniform List<scalar> 2 (1);}',2)
except AssertionError:pass
else:raise AssertionError('Truncated scalar payload was accepted')
results=[]
for name in ('directed-equilibrium-044','wall-flux-pressure-051'):
    case=Path('work/bionic-airflow-20261012')/name;mesh=case/'constant/polyMesh'
    receipt=json.loads((case/'report.json').read_text())
    assert receipt['native_exit_code']==0 and receipt['native_end']
    assert all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
    points=ascii_list((mesh/'points').read_text(),True);owner=ascii_list((mesh/'owner').read_text()).astype(int)
    faces=list(ascii_faces((mesh/'faces').read_text()));assert len(owner)==len(faces)
    match=re.search(r'walls\s*\{.*?nFaces\s+(\d+);\s*startFace\s+(\d+);',(mesh/'boundary').read_text(),re.S)
    count,start=map(int,match.groups());assert start+count==len(faces)
    m=re.search(r'cellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S)
    zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
    rotating=np.isin(owner[start:],zone)
    frame=(case/'constant/MRFProperties').read_text()
    assert re.search(r'nonRotatingPatches\s*\(walls\)',frame)
    assert re.search(r'axis\s*\(0 0 1\)',frame) and re.search(r'origin\s*\(0 0 0\)',frame)
    omega=float(re.search(r'omega\s+constant\s+([^;]+)',frame)[1])
    q=np.zeros(count)
    for size in sorted(set(map(len,faces[start:]))):
        indices=np.array([i for i,f in enumerate(faces[start:]) if len(f)==size and rotating[i]])
        if not len(indices):continue
        c,s,_=geometry(points[np.array([faces[start+i] for i in indices])])
        q[indices]=np.einsum('ij,ij->i',np.cross([0,0,omega],c),s)
    texts={field:(case/'2e-05'/field).read_text() for field in ('rho','phi')}
    assert re.search(r'dimensions\s*\[1 0 -1 0 0 0 0\]',texts['phi'])
    assert re.search(r'dimensions\s*\[1 -3 0 0 0 0 0\]',texts['rho'])
    rho=wall_scalar(texts['rho'],count);phi=wall_scalar(texts['phi'],count)
    residual=phi+rho*q
    results.append(dict(case=name,receipt_sha256=sha(case/'report.json'),walls=count,rotating_owner_walls=int(rotating.sum()),
        max_abs_relative_phi_kg_s=float(abs(phi).max()),sum_abs_relative_phi_kg_s=float(abs(phi).sum()),
        reconstructed_abs_mass_flux_with_final_density_max_kg_s=float(abs(residual).max()),
        reconstructed_abs_mass_flux_with_final_density_sum_abs_kg_s=float(abs(residual).sum()),
        max_face=int(start+np.argmax(abs(residual))),density_range_kg_m3=[float(rho.min()),float(rho.max())]))
output=dict(source_sha256=sha(Path(__file__)),results=results,scope='Exploratory diagnostic only: assembly-time density is not separately recorded. Not a certified wall flux, air performance or cause attribution.')
with Path(__file__).with_name('wall-flux-readback-v2.json').open('x') as f:json.dump(output,f,indent=2)
print(json.dumps(output))
