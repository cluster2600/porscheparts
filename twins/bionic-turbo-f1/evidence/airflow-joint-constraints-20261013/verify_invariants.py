"""Exact dependency analysis of the two symbolic ring variables, no evaluation."""
import hashlib,json
from collections import defaultdict
from pathlib import Path

w=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
system=json.loads((w/'system.json').read_text())
src=Path('work/bionic-buffered-transition-20261013/construction.json')
assert sha(src)==system['source_construction_sha256']
s=json.loads(src.read_text());fixed=set(system['fixed_point_labels'])
variable={r['point'] for r in system['coordinate_bindings']}
assert fixed.isdisjoint(variable) and fixed|variable==set(range(len(s['vertices'])))
depends=[bool(set(block)&variable) for block in s['blocks']]
assert [not x for x in depends]==s['rotating']
assert all(set(face)<=fixed for face in s['mrf_faces'])
reg=defaultdict(list);counts=[]
for cell,b in enumerate(s['blocks']):
    n=4 if s['stages'][cell]=='buffer' else 3
    lo,hi=b[:n],b[4:4+n]
    faces=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)]
    counts.append(len(faces))
    for f in faces:reg[tuple(sorted(f))].append(cell)
static_angles=0;variable_angles=0;fixed_face_variable_neighbour=0;mrf_variable=0
for f,cells in reg.items():
    assert len(cells) in (1,2)
    if len(cells)==1:continue
    dependent=any(depends[c] for c in cells)
    variable_angles+=dependent;static_angles+=not dependent
    fixed_face_variable_neighbour+=bool(set(f)<=fixed and dependent)
    if s['rotating'][cells[0]]!=s['rotating'][cells[1]]:
        assert set(f)<=fixed and dependent
        mrf_variable+=1
static_planes=sum(n*(n-1) for c,n in enumerate(counts) if not depends[c])
assert (sum(not x for x in depends),static_angles,static_planes,mrf_variable)==(1152,1920,23040,384)
out=dict(source_sha256=sha(Path(__file__)),system_sha256=sha(w/'system.json'),fixed_rotor_cells=1152,variable_fixed_region_cells=sum(depends),constant_internal_angles=static_angles,remaining_internal_angles=variable_angles,constant_determinants=1152,remaining_determinants=sum(depends),constant_ordered_plane_pairs=static_planes,remaining_ordered_plane_pairs=sum(n*(n-1) for n in counts)-static_planes,mrf_faces_geometrically_constant_but_angle_dependent=mrf_variable,fixed_face_geometry_with_dependent_neighbour_angle=fixed_face_variable_neighbour,dependency_proof_only=True,values_evaluated=False,candidate_created=False,feasibility_solved=False)
(w/'invariants.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
