"""Read-only analytic moments and all neighbour constraints of archived PR229."""
import ast
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
SOURCE = Path('work/bionic-buffered-transition-20261013')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = Path('work/bionic-airflow-delivery-20261013-buffered-transition/file-manifest.json')
for row in json.loads(manifest.read_text())['files']:
    assert sha(Path('work') / row['path']) == row['sha256']
source = SOURCE / 'construction.json'
assert sha(source) == 'ddda1839b41b7dfde9b7303d90f47e35c0ac35726f1db1278117366de71eb9e4'
s = json.loads(source.read_text())
p = np.array(s['vertices'])
helper = Path('twins/bionic-turbo-f1/evidence/airflow-conformal-local-design-20261013/verify_pyramids.py')
assert sha(helper) == '673f80a53bd03dba18820fa060c51e4cea75c660a6e546a8cda6c1e394be6c2a'
tree = ast.parse(helper.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('polygon', 'metrics')], type_ignores=[]), str(helper), 'exec'))


def wedge(vertices, upper):
    """Triangle or convex quad in r,z, extruded between two straight angular ends."""
    q = p[vertices]
    r = np.linalg.norm(q[:, :2], axis=1)
    z = q[:, 2]
    rhi = np.linalg.norm(p[upper, :2], axis=1)
    u, v = q[:, :2] / r[:, None], p[upper, :2] / rhi[:, None]
    assert np.max(abs(rhi-r)) < 1e-16 and np.array_equal(p[upper, 2], z)
    assert np.max(abs(u-u[0])) < 1e-14 and np.max(abs(v-v[0])) < 1e-14
    bis = u[0]+v[0]
    coshalf = np.linalg.norm(bis)/2
    direction = bis/np.linalg.norm(bis)
    sine = float(np.cross(u[0], v[0]))
    assert sine > 0 and coshalf > 0
    volume, moment = 0.0, np.zeros(3)
    for j in range(1, len(vertices)-1):
        ids = [0, j, j+1]
        rr, zz = r[ids], z[ids]
        signed = float(np.linalg.det(np.column_stack((rr[1:]-rr[0], zz[1:]-zz[0]))))/2
        area = abs(signed)
        total = sum(rr)
        second = sum(rr*rr)+rr[0]*rr[1]+rr[0]*rr[2]+rr[1]*rr[2]
        c = np.array([*(direction*coshalf*second/(2*total)), (total*sum(zz)+rr@zz)/(4*total)])
        vol = sine*area*total/3
        assert vol > 0
        volume += vol
        moment += vol*c
    return moment/volume, volume


def homothetic(lo, hi):
    """Exact integral of a triangular section scaled linearly along z."""
    low, high = p[lo], p[hi]
    assert np.ptp(low[:, 2]) == 0 and np.ptp(high[:, 2]) == 0
    z0, z1 = low[0, 2], high[0, 2]
    h = z1-z0
    scale = np.linalg.norm(high[0, :2])/np.linalg.norm(low[0, :2])
    assert h > 0 and scale > 0 and np.max(abs(high[:, :2]-scale*low[:, :2])) < 1e-16
    area = abs(float(np.cross(low[1, :2]-low[0, :2], low[2, :2]-low[0, :2])))/2
    i2 = (1+scale+scale**2)/3
    i3 = (1+scale+scale**2+scale**3)/4
    # Integral t*(1+(scale-1)*t)^2 dt, avoiding division by scale-1.
    j2 = (1+2*scale+3*scale**2)/12
    centre = np.array([*(low[:, :2].mean(axis=0)*i3/i2), z0+h*j2/i2])
    return centre, area*h*i2


registry = defaultdict(list)
polys, centres, volumes, face_geometry = [], [], [], []
errors, verr = [], []
for cell, block in enumerate(s['blocks']):
    stage = s['stages'][cell]
    if stage == 'buffer':
        lo, hi = block[:4], block[4:]
        # Meridian ends of the hex, in matching order at the two theta values.
        c, volume = wedge([block[k] for k in (0, 1, 5, 4)], [block[k] for k in (3, 2, 6, 7)])
    else:
        assert block[2] == block[3] and block[6] == block[7]
        lo, hi = block[:3], block[4:7]
        c, volume = wedge(lo, hi) if stage == 'axial' else homothetic(lo, hi)
    n = len(lo)
    faces = [lo[::-1], hi] + [[lo[j], lo[(j+1)%n], hi[(j+1)%n], hi[j]] for j in range(n)]
    edges = Counter((a,b) for face in faces for a,b in zip(face, face[1:]+face[:1]))
    assert all(count == 1 and edges[b,a] == 1 for (a,b),count in edges.items())
    for face in faces:
        registry[tuple(sorted(face))].append((cell, face))
    scalar_c, scalar_v, ca = metrics([[p[k] for k in face] for face in faces])
    errors.append(float(np.linalg.norm(c-scalar_c)))
    verr.append(abs(volume/scalar_v-1))
    assert volume > 0
    polys.append(faces); centres.append(c); volumes.append(volume); face_geometry.append(ca)
assert len(polys) == 6144 and max(errors) < 1e-15 and max(verr) < 1e-11
assert all(len(pair) in (1,2) for pair in registry.values())
boundary = {key for key,pair in registry.items() if len(pair)==1}
assert boundary == {tuple(sorted(set(face))) for face in s['walls']}
by_pair = defaultdict(list)
face_rows = []
warp = 0.0
for key,pair in registry.items():
    owner, face = pair[0]
    cf, sf = polygon([p[k] for k in face])
    sf = np.array(sf); normal = sf/np.linalg.norm(sf)
    warp = max(warp, float(np.max(abs((p[face]-cf)@normal))))
    if len(pair)==1:
        continue
    neighbour, other = pair[1]
    assert set(zip(face,face[1:]+face[:1])) == {(b,a) for a,b in zip(other,other[1:]+other[:1])}
    delta = centres[neighbour]-centres[owner]
    dn = float(delta@normal)
    dt = float(np.linalg.norm(np.cross(delta,normal)))
    assert dn > 0
    angle = math.degrees(math.atan2(dt,dn))
    family = '/'.join(sorted((s['stages'][owner],s['stages'][neighbour])))
    row = dict(owner=owner, neighbour=neighbour, family=family, normal_m=dn, tangential_m=dt, margin_m=math.tan(math.radians(70))*dn-dt, angle_deg=angle)
    by_pair[family].append(row); face_rows.append(row)
assert len(face_rows) == 13696 and warp < 1e-12
old = {(int(r['owner']),int(r['neighbour'])) for r in csv.DictReader((SOURCE/'angles.csv').open()) if float(r['angle_deg'])>70}
assert {(r['owner'],r['neighbour']) for r in face_rows if r['margin_m']<0} == old

cell_rows = []
for cell, (faces,ca) in enumerate(zip(polys,face_geometry)):
    eligible = [sf for face,(_,sf) in zip(faces,ca) if len(registry[tuple(sorted(face))])==2]
    avg = math.fsum(float(np.linalg.norm(sf)) for sf in eligible)/len(eligible)
    tensor = sum(np.outer(sf,sf) for sf in eligible)/avg**2
    determinant = abs(float(np.linalg.det(tensor)))/8
    score = max(float(np.dot(cj-ci,ai)/np.linalg.norm(cj-ci)/np.linalg.norm(ai)) for i,(ci,ai) in enumerate(ca) for j,(cj,_) in enumerate(ca) if i!=j)
    caps = []
    for name,z in (('lower',s['stations_m'][0]),('upper',s['stations_m'][-1])):
        if any(tuple(sorted(face)) in boundary and np.all(p[face,2]==z) for face in faces):
            caps.append(name)
    cell_rows.append(dict(cell=cell,stage=s['stages'][cell],closure='+'.join(caps) or 'none',internal_faces=len(eligible),determinant=determinant,plane_score=score,volume_m3=volumes[cell]))
assert min(r['determinant'] for r in cell_rows)>=.001 and max(r['plane_score'] for r in cell_rows)<=-1e-6
for name,rows in [('faces.csv',face_rows),('cells.csv',cell_rows)]:
    with (ROOT/name).open('x') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
groups = {}
for stage in sorted(set(s['stages'])):
    for closure in ('none','lower','upper'):
        rows=[r for r in cell_rows if r['stage']==stage and r['closure']==closure]
        if rows: groups[stage+'/'+closure]={'cells':len(rows),'internal_face_counts':dict(Counter(r['internal_faces'] for r in rows)),'minimum_determinant':min(r['determinant'] for r in rows),'maximum_plane_score':max(r['plane_score'] for r in rows)}
result={'source_sha256':sha(Path(__file__)),'construction_sha256':sha(source),'source_manifest_sha256':sha(manifest),'all_source_payloads_verified':True,'cells':len(polys),'internal_faces':len(face_rows),'boundary_faces':len(boundary),'max_centre_difference_m':max(errors),'max_volume_relative_difference':max(verr),'volume_m3':sum(volumes),'max_face_warp_m':warp,'families':{k:{'faces':len(rows),'maximum_angle_deg':max(r['angle_deg'] for r in rows),'minimum_margin_m':min(r['margin_m'] for r in rows),'faces_over_70':sum(r['margin_m']<0 for r in rows)} for k,rows in sorted(by_pair.items())},'cell_groups':groups,'boundary_neighbour_angles_defined':False,'candidate_created':False,'native_executed':False,'accepted':False}
(ROOT/'readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
