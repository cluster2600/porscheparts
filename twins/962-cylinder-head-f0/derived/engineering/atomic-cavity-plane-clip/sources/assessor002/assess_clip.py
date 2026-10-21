"""Exact retained-output oracle for four fixed z>=0 clipping literals; no native imports."""
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT / 'work/962-engineering/atomic-cavity-plane-clip-prep-001'
EXPECTED_SHA = '36fa8bf24d9e7067b3d1881a42785f85d1c31ef155aa57c8275aab151908cbe9'
MAX_ID = (1 << 64) - 1


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(face):
    t = tuple(face)
    return min(t, t[1:] + t[:1], t[2:] + t[:2])


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def read(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), 'Regular mesh required')
    raw = path.read_bytes()
    need(raw[:8] == b'962SURF1' and len(raw) >= 24, 'Invalid codec')
    nv, nf = struct.unpack_from('<QQ', raw, 8)
    need(nv > 0 and nf > 0 and len(raw) == 24 + 24*(nv+nf), 'Invalid codec length/counts')
    rows = [raw[24+24*i:48+24*i] for i in range(nv)]
    floats = [struct.unpack('<ddd', row) for row in rows]
    need(all(math.isfinite(v) for p in floats for v in p), 'Nonfinite point')
    points = [tuple(F(v) for v in p) for p in floats]
    faces = list(struct.iter_unpack('<QQQ', raw[24+24*nv:]))
    need(len(set(points)) == nv, 'Duplicate coordinate rows')
    need(all(len(set(t)) == 3 and max(t) < nv for t in faces), 'Invalid face indices')
    need(len({tuple(sorted(t)) for t in faces}) == nf, 'Duplicate face')
    need(set(v for t in faces for v in t) == set(range(nv)), 'Orphan point')
    need(all(dot(cross(sub(points[b], points[a]), sub(points[c], points[a])),
                     cross(sub(points[b], points[a]), sub(points[c], points[a]))) > 0
             for a, b, c in faces), 'Degenerate triangle')
    return rows, points, faces


def connected(adjacency):
    remaining = set(adjacency)
    count = 0
    while remaining:
        count += 1
        todo = [remaining.pop()]
        while todo:
            for other in adjacency[todo.pop()]:
                if other in remaining:
                    remaining.remove(other)
                    todo.append(other)
    return count


def topology(points, faces, expected_euler):
    edges = Counter()
    balance = Counter()
    graph = defaultdict(set)
    links = defaultdict(list)
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            e = tuple(sorted((u, v)))
            edges[e] += 1
            balance[e] += 1 if u < v else -1
            graph[u].add(v)
            graph[v].add(u)
        for v, x, y in ((a, b, c), (b, c, a), (c, a, b)):
            links[v].append(tuple(sorted((x, y))))
    need(all(n == 2 for n in edges.values()) and not any(balance.values()), 'Nonclosed/orientation edge incidence')
    need(connected(graph) == 1, 'Multiple components')
    for pairs in links.values():
        need(len(pairs) == len(set(pairs)), 'Repeated vertex-link edge')
        link = defaultdict(set)
        for a, b in pairs:
            link[a].add(b)
            link[b].add(a)
        need(all(len(x) == 2 for x in link.values()) and connected(link) == 1, 'Noncyclic vertex link')
    euler = len(points) - len(edges) + len(faces)
    need(euler == expected_euler, 'Unexpected Euler characteristic')
    volume = sum(dot(points[a], cross(points[b], points[c])) for a, b, c in faces) / 6
    need(volume > 0, 'Nonpositive volume')
    return {'vertices': len(points), 'faces': len(faces), 'edges': len(edges),
            'Euler': euler, 'components': 1, 'exact_signed_volume_mm3': str(volume)}


def area(poly):
    return abs(sum((F(p[0])*q[1]-F(p[1])*q[0] for p, q in zip(poly, poly[1:]+poly[:1])), F(0))) / 2


def side(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def intersection(subject, clipper):
    """Exact convex polygon intersection; boundaries count as zero area."""
    output = [tuple(F(x) for x in p) for p in subject]
    clipper = [tuple(F(x) for x in p) for p in clipper]
    signed = sum(p[0]*q[1]-p[1]*q[0] for p, q in zip(clipper, clipper[1:]+clipper[:1]))
    need(signed != 0, 'Degenerate clipping polygon')
    clipper = list(clipper if signed > 0 else reversed(clipper))
    for a, b in zip(clipper, clipper[1:]+clipper[:1]):
        previous, output = output, []
        if not previous:
            break
        s = previous[-1]
        ds = side(a, b, s)
        for e in previous:
            de = side(a, b, e)
            if (ds < 0) != (de < 0):
                t = ds / (ds-de)
                output.append(tuple(x+t*(y-x) for x, y in zip(s, e)))
            if de >= 0:
                output.append(e)
            s, ds = e, de
    return output


def rectangle(lo, hi):
    return [(F(lo[0]), F(lo[1])), (F(hi[0]), F(lo[1])),
            (F(hi[0]), F(hi[1])), (F(lo[0]), F(hi[1]))]


def cover(triangles, lo, hi, target, hole=None):
    outer = rectangle(lo, hi)
    for triangle in triangles:
        need(area(triangle) > 0 and area(intersection(triangle, outer)) == area(triangle), 'Triangle outside support rectangle')
        if hole:
            need(area(intersection(triangle, rectangle(*hole))) == 0, 'Triangle fills open hole')
    need(sum(area(t) for t in triangles) == target, 'Incomplete/extra support area')
    for i, t in enumerate(triangles):
        need(all(area(intersection(t, u)) == 0 for u in triangles[:i]), 'Positive-area overlap')


def supports(name):
    # Each patch: axis, coordinate, outward sign, projected lo/hi, exact area, hole.
    if name == 'cube-cut':
        return [(2, 0, -1, (-76, -76), (76, 76), 23104, None),
                (2, 76, 1, (-76, -76), (76, 76), 23104, None)] + [
            (a, s*76, s, (-76, 0), (76, 76), 11552, None)
            for a in (0, 1) for s in (-1, 1)]
    need(name == 'through-hole', 'Unsupported analytic support')
    return [(2, z, s, (-2, -2), (2, 2), 12, ((-1, -1), (1, 1)))
            for z, s in ((0, -1), (1, 1))] + [
        (a, s*r, s if r == 2 else -s, (-r, 0), (r, 1), 2*r, None)
        for r in (2, 1) for a in (0, 1) for s in (-1, 1)]


def audit_supports(name, points, faces):
    patches = supports(name)
    triangles = [[] for _ in patches]
    cap_faces = 0
    for face in faces:
        xyz = [points[v] for v in face]
        normal = cross(sub(xyz[1], xyz[0]), sub(xyz[2], xyz[0]))
        matches = [i for i, (a, c, *_rest) in enumerate(patches) if all(p[a] == c for p in xyz)]
        need(len(matches) == 1, 'Face has no unique literal support plane')
        i = matches[0]
        axis, coordinate, sign, *_rest = patches[i]
        need(normal[axis]*sign > 0, 'Incorrect outward patch winding')
        triangles[i].append([tuple(p[a] for a in range(3) if a != axis) for p in xyz])
        cap_faces += axis == 2 and coordinate == 0
    for ts, (_a, _c, _s, lo, hi, target, hole) in zip(triangles, patches):
        cover(ts, lo, hi, target, hole)
    return cap_faces


def coordinate_faces(rows, faces):
    return Counter(canonical([rows[v] for v in t]) for t in faces)


def audit_geometry(name, rows_in, points_in, faces_in, rows, points, faces, ids, expected):
    need(all(p[2] >= 0 for p in points), 'Below-plane output point')
    lookup = {row: i for i, row in enumerate(rows_in)}
    need(ids == [lookup.get(row, MAX_ID) for row in rows], 'Incorrect coordinate-match IDs')
    need(all(i != MAX_ID or p[2] == 0 for i, p in zip(ids, points)), 'Constructed off-plane point')
    retained = {i for i in ids if i != MAX_ID}
    need({i for i, p in enumerate(points_in) if p[2] > 0} <= retained, 'Missing above-plane source coordinate')
    original_faces = coordinate_faces(rows_in, [t for t in faces_in if all(points_in[v][2] > 0 for v in t)])
    output_faces = coordinate_faces(rows, faces)
    need(not (original_faces - output_faces), 'Changed wholly-above oriented source triangle')
    result = topology(points, faces, expected['Euler'])
    need(F(result['exact_signed_volume_mm3']) == expected['volume_mm3'], 'Wrong exact volume')
    need([min(p[2] for p in points), max(p[2] for p in points)] == expected['z_range_mm'], 'Wrong z range')
    if name == 'above-noop':
        need(Counter(rows) == Counter(rows_in) and output_faces == coordinate_faces(rows_in, faces_in), 'No-op geometry changed')
        cap_faces = 0
    else:
        cap_faces = audit_supports(name, points, faces)
    q2 = []
    for a, b, c in faces:
        u, v, w = sub(points[b], points[a]), sub(points[c], points[a]), sub(points[c], points[b])
        n = cross(u, v)
        q2.append(12*dot(n, n)/(dot(u, u)+dot(v, v)+dot(w, w))**2)
    result.update(cap_faces=cap_faces, exact_cap_area_mm2=str(expected['cap_area_mm2']),
                  retained=len(retained), constructed=ids.count(MAX_ID),
                  exact_minimum_triangle_quality_squared=str(min(q2)),
                  exact_faces_below_2_over_29=sum(q < F(4, 841) for q in q2))
    return result


def assess_case(name, directory):
    need(sha(PREP/'fixture-expectations.json') == EXPECTED_SHA, 'Frozen expectation drift')
    case = next(c for c in json.loads((PREP/'fixture-expectations.json').read_text())['cases'] if c['name'] == name)
    source = ROOT/case['input_relative']
    need(sha(source) == case['input_sha256'] and source.stat().st_size == case['input_bytes'], 'Frozen input drift')
    rows_in, points_in, faces_in = read(source)
    need(rows_in == [struct.pack('<ddd', *p) for p in case['points']] and faces_in == [tuple(t) for t in case['oriented_faces']], 'Literal input association')
    directory = Path(directory)
    need(directory.is_dir() and not directory.is_symlink(), 'Regular output directory required')
    need(all(p.is_file() and not p.is_symlink() for p in directory.iterdir()), 'Nonregular output member')
    report = json.loads((directory/'report.json').read_text(), parse_float=F,
                        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    need(report['plane'] == [0, 0, -1, 0] and report['clip_volume'] is True, 'Wrong plane/operation')
    need(all(report[k] is False for k in ('head_surface_admitted', 'physics_validated', 'manufacturing_authorized')), 'Scope flag changed')
    if name == 'empty-refusal':
        need({p.name for p in directory.iterdir()} == {'report.json'} and report['status'] == 'rejected_empty_result', 'Empty refusal closure/status')
        need(report['candidate_file_present'] is report['point_id_file_present'] is False, 'Unexpected empty export')
        result = {'case': name, 'expected_native_returncode': 3, 'report_only_empty_refusal': True}
    else:
        need({p.name for p in directory.iterdir()} == {'report.json', 'candidate.bin', 'input-point-ids.u64'}, 'Output closure')
        rows, points, faces = read(directory/'candidate.bin')
        raw_ids = (directory/'input-point-ids.u64').read_bytes()
        need(len(raw_ids) == 8*len(points), 'ID length')
        ids = [v[0] for v in struct.iter_unpack('<Q', raw_ids)]
        expected = dict(case['expected_output'], Euler=case['expected_output_Euler'])
        result = audit_geometry(name, rows_in, points_in, faces_in, rows, points, faces, ids, expected)
        need(report['status'] == 'proposal_exported_pending_independent_audits' and report['candidate_exported'] is True, 'Success status')
        need(report['kernel'] == 'EPECK_exact_clip_then_EPICK_binary64_embedding' and report['CGAL'] == '5.6', 'Source/runtime identity')
        need(report['ids_are_coordinate_matches_not_construction_history'] is True and report['new_point_id_sentinel'] == 'UINT64_MAX', 'ID semantics')
        need(report['volume_mesh_admitted'] is report['global_independent_topology_intersection_feature_CUB_checks_completed'] is False, 'Admission scope changed')
        counts = {'clip_calls': 1, 'input_vertices': len(points_in), 'input_faces': len(faces_in),
                  'output_vertices': len(points), 'output_faces': len(faces), 'plane_cap_faces': result['cap_faces'],
                  'exact_input_coordinate_matches': result['retained'], 'distinct_retained_input_ids': result['retained'],
                  'constructed_on_plane_coordinates': result['constructed'],
                  'unretained_input_coordinate_ids': len(points_in)-result['retained'],
                  'surface_faces_below_2_over_29': result['exact_faces_below_2_over_29']}
        need(all(type(report[k]) is int and report[k] == v for k, v in counts.items()), 'Native count mismatch')
        scalars = {'input_signed_volume_mm3': F(case['input_exact_audit']['exact_signed_volume_mm3']),
                   'input_zmin_mm': min(p[2] for p in points_in), 'input_zmax_mm': max(p[2] for p in points_in),
                   'output_signed_volume_mm3': expected['volume_mm3'], 'output_zmin_mm': expected['z_range_mm'][0],
                   'output_zmax_mm': expected['z_range_mm'][1], 'plane_cap_area_mm2': expected['cap_area_mm2']}
        need(all(type(report[k]) in (int, F) and report[k] == v for k, v in scalars.items()), 'Native scalar mismatch')
        minimum = report['minimum_surface_quality']
        need(type(minimum) in (int, F) and 0 < minimum <= 1, 'Invalid native quality')
        need(report['surface_quality_screen_passed'] is (result['exact_faces_below_2_over_29'] == 0), 'Native quality classification mismatch')
        result.update(case=name, expected_native_returncode=0, native_minimum_surface_quality=str(minimum),
                      native_minimum_not_equated_to_exact_squared_metric=True)
    result.update(input_sha256=sha(source), report_sha256=sha(directory/'report.json'),
                  complete_output_sha256={p.name: sha(p) for p in sorted(directory.iterdir())},
                  literal_software_geometry_only=True, head_or_physical_admission=False)
    need(sha(PREP/'fixture-expectations.json') == EXPECTED_SHA and sha(source) == case['input_sha256'], 'Input changed during read')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: assess_clip.py case-name completed-output-directory')
    print(json.dumps(assess_case(sys.argv[1], sys.argv[2]), indent=2, sort_keys=True))
