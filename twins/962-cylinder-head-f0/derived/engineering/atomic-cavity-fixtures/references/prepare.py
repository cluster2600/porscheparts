"""Freeze three tiny atomic-quotient references; pure stdlib, no native calls."""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OLD = ROOT/'work/962-engineering/remaining266-native-probe-prep-001'
HELPER = ROOT/'twins/962-cylinder-head-f0/source/check_finest_endpoint_fixtures.py'
PINS = {
    'known-collapse.bin': '366abee8edbfae85e54da1621a17ba35a6d298a8e4c66261ac83a1ec02cdf558',
    'known-collapse-origins.u64': '23c379d6c0f22ef64cdef873fd530df1f1419b4a3935e9323d5f1d82ca697b6a',
    'known-collapse-targets.u64': '5ec0616dd54ea5b98086a5ed5157fba570faf2b9e40c02b2cb1f91d38228803f',
    'all-fixed.bin': '69988b1e25cb06cdb41d8d9ef3ff8431ded95030f4497a4dc702fc590a285a35',
    'all-fixed-origins.u64': '23c379d6c0f22ef64cdef873fd530df1f1419b4a3935e9323d5f1d82ca697b6a',
    'all-fixed-targets.u64': '5ec0616dd54ea5b98086a5ed5157fba570faf2b9e40c02b2cb1f91d38228803f',
    'fixture-expectations.json': '734e7fbbd7d9818d3049127756e7b57c1e012b367d86597f3d8fa4ecfbc747fd',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def geometry(p, f):
    normals = []; bad = []; volume = Fraction(0); qualities = []
    for index, ids in enumerate(f):
        a, b, c = [[Fraction(x) for x in p[i]] for i in ids]
        u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        n = cross(u, v); area_squared = dot(n, n)
        total = dot(u, u)+dot(v, v)+sum((v[i]-u[i])**2 for i in range(3))
        assert area_squared > 0 and total > 0
        poor = 2523*area_squared < total*total  # Exactly q2 < 2/29.
        if poor:
            bad.append(index)
        quality = 2*math.sqrt(3)*math.sqrt(float(area_squared))/float(total)
        assert poor == (quality < 2/29)
        qualities.append(quality); normals.append([str(x) for x in n])
        volume += dot(a, cross(b, c))/6
        planes = [(axis, sign) for axis in range(3) for sign in [-1, 1]
                  if all(p[i][axis] == sign*76 for i in ids)]
        assert len(planes) == 1
        axis, sign = planes[0]
        assert sign*n[axis] > 0 and all(n[i] == 0 for i in range(3) if i != axis)
    return dict(poor_face_rows=bad, poor_faces=len(bad),
                minimum_triangle_SICN=min(qualities), signed_volume_mm3=str(volume),
                outward_unnormalized_face_normals_exact=normals,
                all_faces_outward_on_unchanged_cube_planes=True)


def topology(p, f, closed):
    canonical = [min(tuple(t[i:]+t[:i]) for i in range(3)) for t in f]
    assert len(set(canonical)) == len(f)
    directed = Counter((t[i], t[(i+1) % 3]) for t in f for i in range(3))
    edges = Counter(tuple(sorted(e)) for e in directed.elements())
    assert all(n in (1, 2) for n in edges.values())
    assert all(directed[e] == directed[e[::-1]] == 1 for e, n in edges.items() if n == 2)
    boundary = sorted(e for e, n in directed.items() if edges[tuple(sorted(e))] == 1)
    used = {v for t in f for v in t}; assert used
    if closed:
        assert used == set(range(len(p))) and not boundary
    boundary_vertices = {v for e in boundary for v in e}
    links = {v: defaultdict(set) for v in used}
    for t in f:
        assert len(set(t)) == 3
        for i, v in enumerate(t):
            a, b = t[(i+1) % 3], t[(i+2) % 3]
            links[v][a].add(b); links[v][b].add(a)
    for v, graph in links.items():
        seen = set(); pending = [next(iter(graph))]
        while pending:
            n = pending.pop()
            if n not in seen:
                seen.add(n); pending.extend(graph[n]-seen)
        assert seen == set(graph)
        degrees = sorted(len(x) for x in graph.values())
        assert degrees.count(1) == (2 if v in boundary_vertices else 0)
        assert all(n in (1, 2) for n in degrees)
    if boundary:
        assert len(boundary) == 4 and len(boundary_vertices) == 4
        assert all(sum(a == v for a, b in boundary) == sum(b == v for a, b in boundary) == 1
                   for v in boundary_vertices)
    euler = len(used)-len(edges)+len(f)
    assert euler == (2 if closed else 1)
    return dict(vertices=len(used), edges=len(edges), faces=len(f), Euler=euler,
                oriented_boundary_edges=boundary, edge_and_vertex_manifold=True,
                no_duplicate_or_orphan_faces=True)


def fixed_mask(p, f, poor):
    seeds = {i for row in poor for i in f[row]}
    patch = [i for i, t in enumerate(f) if any(v in seeds for v in t)]
    outside = set(range(len(f)))-set(patch)
    fixed = {v for i in outside for v in f[i]} | {i for i, point in enumerate(p) if abs(point[0]) == 76}
    return dict(original_seed_vertices=sorted(seeds), original_patch_face_rows=patch,
                fixed_original_IDs=sorted(fixed))


def run():
    expected = {str((OLD/n).relative_to(ROOT)): h for n, h in PINS.items()}
    expected[str(HELPER.relative_to(ROOT))] = '10efedb3df8875fd453a5298493f99cae54dd8fd4149cfcedcea901c76ec8b58'
    expected[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
    before = {n: sha(ROOT/n) for n in expected}; assert before == expected
    spec = importlib.util.spec_from_file_location('immutable_pure_cube_fixture', HELPER)
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    literal = json.loads((OLD/'fixture-expectations.json').read_text())['cases']
    cube, _ = h.fixture(split=False)
    bottom = [[0, 2, 1], [0, 3, 2]]
    sides = [[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
             [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]]
    top = [[4, 5, 9], [4, 9, 8], [5, 6, 10], [5, 10, 9],
           [6, 7, 11], [6, 11, 10], [7, 4, 8], [7, 8, 11], [8, 9, 10], [8, 10, 11]]
    four_p = list(cube[:8])+[(-2**-16, -2**-15, 76.0), (2**-16, -2**-15, 76.0),
                            (2**-16, 2**-15, 76.0), (-2**-16, 2**-15, 76.0)]
    four_f = bottom+top+sides
    expected_four = (four_p[:9], bottom+[[4, 5, 8], [5, 6, 8], [6, 7, 8], [7, 4, 8]]+sides)
    data = {'four-vertex-disk.bin': h.pack(four_p, four_f),
            'four-vertex-disk-origins.u64': b''.join(struct.pack('<Q', i) for i in range(12)),
            'four-vertex-disk-targets.u64': b''.join(struct.pack('<QQ', *e) for e in [(8, 9), (8, 11), (9, 10), (10, 11)]),
            'keepers-8.u64': struct.pack('<QQ', 8, 8)}
    cases = []
    for name, rotated, group, arrays, reference in [
            ('known-collapse', False, [8, 9], h.fixture(), h.fixture(split=False)),
            ('all-fixed', True, [8, 9], h.fixture(rotated=True), h.fixture(rotated=True)),
            ('four-vertex-disk', False, [8, 9, 10, 11], (four_p, four_f), expected_four)]:
        p, f = arrays; ep, ef = reference
        if name != 'four-vertex-disk':
            assert (OLD/(name+'.bin')).read_bytes() == h.pack(p, f)
            assert list(struct.iter_unpack('<Q', (OLD/(name+'-origins.u64')).read_bytes())) == [(i,) for i in range(len(p))]
            assert (OLD/(name+'-targets.u64')).read_bytes() == struct.pack('<QQ', 8, 9)
            raw = next(x for x in literal if x['name'] == name)
            assert raw['points'] == [list(x) for x in p] and raw['faces'] == [list(x) for x in f]
        gm, after = geometry(p, f), geometry(ep, ef)
        mask = fixed_mask(p, f, gm['poor_face_rows']); full = topology(p, f, True); result = topology(ep, ef, True)
        assert gm['signed_volume_mm3'] == after['signed_volume_mm3'] == '3511808'
        star_rows = [i for i, t in enumerate(f) if any(v in group for v in t)]
        disk = topology(p, [f[i] for i in star_rows], False)
        reject = name == 'all-fixed'
        assert bool(set(group) & set(mask['fixed_original_IDs'])) == reject
        assert mask['fixed_original_IDs'] == list(range(10 if reject else 8))
        if not reject:
            mapped = [[8 if v in group else v for v in t] for t in f]
            quotient = [t for t in mapped if len(set(t)) == 3]
            assert h.triangles(p, quotient) == h.triangles(ep, ef)
            assert topology(ep, ef, True)['Euler'] == 2 and after['poor_faces'] == 0
        assert gm['poor_faces'] == (4 if name == 'four-vertex-disk' else 2)
        native_input = str((OUT/(name+'.bin') if name == 'four-vertex-disk' else OLD/(name+'.bin')).relative_to(ROOT))
        suffix = OUT if name == 'four-vertex-disk' else OLD
        cases.append(dict(name=name, original_and_current_same_input=native_input,
            origins_input=str((suffix/(name+'-origins.u64')).relative_to(ROOT)),
            shortedges_input=str((suffix/(name+'-targets.u64')).relative_to(ROOT)),
            keepers_input=str((OUT/'keepers-8.u64').relative_to(ROOT)),
            group_current_IDs=group, keeper_row=[8, 8],
            expected_outcome='fixed_group_refusal_no_mutation' if reject else 'atomic_quotient_reference',
            expected_returncode='bind_after_source_review_not_predicted_here',
            input_points=p, input_oriented_faces=f, before=gm, before_topology=full,
            actual_source_policy_mask=mask, group_star_rows=star_rows, group_star_disk=disk,
            expected_points=ep, expected_oriented_faces=ef, expected_origins=list(range(len(ep))),
            expected_after=after, expected_after_topology=result,
            expected_removed_faces=0 if reject else len(f)-len(ef),
            expected_all_fixed_and_exterior_exact=True,
            native_fixture_result_credited=False, head_geometry_used=False))
    assert cases[2]['group_star_disk']['vertices'] == 8 and cases[2]['group_star_disk']['faces'] == 10
    assert cases[2]['before_topology'] == dict(vertices=12, edges=30, faces=20, Euler=2,
        oriented_boundary_edges=[], edge_and_vertex_manifold=True, no_duplicate_or_orphan_faces=True)
    assert cases[2]['expected_after_topology']['vertices'] == 9 and cases[2]['expected_after_topology']['edges'] == 21
    for n, raw in data.items():
        with (OUT/n).open('xb') as stream:
            stream.write(raw)
    reference = dict(schema='962-atomic-cavity-three-literal-references/v1', cases=cases,
        mask_policy='Existing original bad-seed incidence and exact x==+-76 clip, unchanged.',
        normal_reference='Every face lies on an original cube plane with exact outward rational normal; listed per face.',
        native_or_compile_or_SSH_calls=0, head_mutation=False, execution_authorized=False,
        manufacturing_authorized=False)
    with (OUT/'expectations.json').open('x') as stream:
        json.dump(reference, stream, indent=2, allow_nan=False); stream.write('\n')
    after = {n: sha(ROOT/n) for n in expected}; assert before == after
    receipt = dict(schema='962-atomic-cavity-fixture-pure-selfcheck/v1', status='all_three_full_array_references_pass',
        input_sha256=before, inputs_after_sha256=after, all_inputs_unchanged=True,
        outputs={n: dict(bytes=(OUT/n).stat().st_size, sha256=sha(OUT/n)) for n in list(data)+['expectations.json']},
        checks=['existing_two_inputs_bytes_origins_targets_unchanged', 'literal_complete_reference_faces',
                'oriented_edge_incidence_and_vertex_links', 'disk_boundaries_and_Euler',
                'exact_volume_and_outward_plane_normals', 'exact_poor_face_comparison',
                'original_fixed_mask_and_keeper_components', 'independent_quotient_reference'],
        native_compiler_SSH_Git_calls=0, execution_authorized=False, manufacturing_authorized=False)
    with (OUT/'selfcheck-receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    return receipt


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
