"""Freeze four literal plane-clip inputs; stdlib only, never call CGAL."""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CUBE = ROOT/'twins/962-cylinder-head-f0/derived/engineering/atomic-cavity-fixtures/results/known-collapse002/candidate.bin'
CUBE_SHA = 'f7e883868f142a53dbc7f9da43d0f19469348e6dfcf12c1149eaef9f37c0625e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def surface_bytes(points, faces):
    return (b'962SURF1'+struct.pack('<QQ', len(points), len(faces))
            +b''.join(struct.pack('<ddd', *p) for p in points)
            +b''.join(struct.pack('<QQQ', *f) for f in faces))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def audit(points, faces, expected_volume, expected_euler):
    """Exact literal determinant, complete incidence, connected vertex links."""
    used = set(); directed = Counter(); links = defaultdict(lambda: defaultdict(set))
    volume = Fraction(0)
    for t in faces:
        assert len(t) == len(set(t)) == 3 and all(0 <= i < len(points) for i in t)
        used.update(t)
        a, b, c = [tuple(Fraction(x) for x in points[i]) for i in t]
        normal = cross(tuple(y-x for x,y in zip(a,b)), tuple(y-x for x,y in zip(a,c)))
        assert any(normal)
        volume += sum(x*y for x,y in zip(a, cross(b,c)))/6
        for k,v in enumerate(t):
            x,y = t[(k+1)%3],t[(k+2)%3]
            directed[v,x] += 1; links[v][x].add(y); links[v][y].add(x)
    assert used == set(range(len(points)))
    undirected = Counter(tuple(sorted(e)) for e in directed.elements())
    assert all(n == 2 for n in undirected.values())
    assert all(directed[e] == directed[e[::-1]] == 1 for e in undirected)
    assert len({min(tuple(t[k:]+t[:k]) for k in range(3)) for t in faces}) == len(faces)
    for link in links.values():
        assert all(len(n) == 2 for n in link.values())
        seen = set(); pending = [next(iter(link))]
        while pending:
            v = pending.pop()
            if v not in seen: seen.add(v); pending.extend(link[v]-seen)
        assert seen == set(link)
    graph = defaultdict(set)
    for a,b in undirected: graph[a].add(b); graph[b].add(a)
    seen = set(); pending = [0]
    while pending:
        v = pending.pop()
        if v not in seen: seen.add(v); pending.extend(graph[v]-seen)
    assert seen == used and len(points)-len(undirected)+len(faces) == expected_euler
    assert volume == expected_volume
    return dict(vertices=len(points), faces=len(faces), edges=len(undirected),
                Euler=expected_euler, components=1, exact_signed_volume_mm3=str(volume),
                complete_opposite_edge_incidence=True, closed_vertex_links=True,
                duplicate_or_orphan_rows=False)


def run():
    if __debug__ is not True: raise RuntimeError('Assertions required for literal self-check')
    assert sha(CUBE) == CUBE_SHA
    raw = CUBE.read_bytes(); assert raw[:8] == b'962SURF1'
    nv,nf = struct.unpack_from('<QQ', raw, 8)
    assert nv == 9 and nf == 14 and len(raw) == 24+24*(nv+nf)
    cube = [list(x) for x in struct.iter_unpack('<ddd', raw[24:24+24*nv])]
    cube_faces = [list(x) for x in struct.iter_unpack('<QQQ', raw[24+24*nv:])]
    outer = [(-2,-2),(2,-2),(2,2),(-2,2)]
    inner = [(-1,-1),(1,-1),(1,1),(-1,1)]
    ring = [[x,y,z] for xy in [outer,inner] for z in [-1,1] for x,y in xy]
    rf = []
    for i in range(4):
        j = (i+1)%4
        rf += [[i,j,j+4],[i,j+4,i+4]]                    # outer walls
        rf += [[8+i,12+i,12+j],[8+i,12+j,8+j]]          # hole walls
        rf += [[4+i,4+j,12+j],[4+i,12+j,12+i]]          # top annulus
        rf += [[i,8+j,j],[i,8+i,8+j]]                  # bottom annulus
    cases = [
      ('cube-cut',cube,cube_faces,3511808,2,dict(returncode=0,volume_mm3=1755904,cap_area_mm2=23104,z_range_mm=[0,76],cap_outward_normal=[0,0,-1])),
      ('through-hole',ring,rf,24,0,dict(returncode=0,volume_mm3=12,cap_area_mm2=12,z_range_mm=[0,1],cap_outward_normal=[0,0,-1],central_open_xy_square=[[-1,-1],[1,1]],no_cap_triangle_intersects_open_hole=True)),
      ('above-noop',[[x,y,z+77] for x,y,z in cube],cube_faces,3511808,2,dict(returncode=0,volume_mm3=3511808,cap_area_mm2=0,z_range_mm=[1,153],all_coordinate_bytes_unchanged=True,oriented_face_multiset_unchanged=True)),
      ('empty-refusal',[[x,y,z-77] for x,y,z in cube],cube_faces,3511808,2,dict(returncode=3,status='rejected_empty_result',candidate_and_point_ID_files_absent=True))]
    targets = [HERE/'fixtures',HERE/'fixture-expectations.json',HERE/'literal-selfcheck.json']
    if any(p.exists() or p.is_symlink() for p in targets): raise FileExistsError('Existing fixture data preserved')
    (HERE/'fixtures').mkdir()
    records = []
    for name,points,faces,volume,euler,oracle in cases:
        metrics = audit(points,faces,volume,euler)
        path = HERE/'fixtures'/f'{name}.bin'
        data = surface_bytes(points,faces)
        if name == 'cube-cut': assert data == raw
        with path.open('xb') as f:f.write(data)
        assert path.read_bytes() == data
        records.append(dict(name=name,input_relative=path.relative_to(ROOT).as_posix(),
                            input_sha256=sha(path),input_bytes=len(data),points=points,
                            oriented_faces=faces,input_exact_audit=metrics,
                            expected_output=oracle,expected_output_Euler=None if name=='empty-refusal' else euler,
                            candidate_triangulation_not_predicted=True,native_result_credited=False))
    refs = dict(schema='962-fixed-z-volume-clip-literal-inputs/v1',plane=[0,0,-1,0],units='mm',
                cube_reused_from=CUBE.relative_to(ROOT).as_posix(),cube_source_sha256=CUBE_SHA,
                cases=records,all_head_execution_authorized=False,
                point_ID_semantics='Input coordinate-bit match or UINT64_MAX; not original Porsche or CGAL birth provenance')
    with (HERE/'fixture-expectations.json').open('x') as f:json.dump(refs,f,indent=2);f.write('\n')
    receipt = dict(schema='962-plane-clip-pure-literal-selfcheck/v1',source_sha256=sha(Path(__file__)),
                   reference_sha256=sha(HERE/'fixture-expectations.json'),cube_source_sha256=sha(CUBE),
                   input_sha256s={x['input_relative']:x['input_sha256'] for x in records},
                   cases=4,all_literal_topology_and_exact_volume_checks_passed=True,
                   native_or_scientific_imports=False,CGAL_calls=0,head_geometry_used=False)
    with (HERE/'literal-selfcheck.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print('PASS: four literal inputs; exact input volumes and full oriented topology; no CGAL call')


if __name__ == '__main__':
    run()
