"""Exact necessary centroid-ball screen on saved fixed-triple rows; no feasibility pass."""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-ball-screen-001'
FIXED = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-fixed-triples-001/readback-report.json'
GROUPS = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-assessment-001/review.json'
TIES = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-assessment-001/minimum-ties.json'
PINS = {
    FIXED: 'd65f86d5d1cabd3e2013a127c1cd9713a232cb1d1bd7817d459f84949d1e1c14',
    GROUPS: '44a1e632adfc35be9f352fc46dd9d305597b04a2d502bd8dd49e97d4a2ee2a3a',
    TIES: 'fa39306ff18637869f0d1b2b9fa7db4c65009c8cbe2f30b61f3a5ca13030587f',
    'twins/962-cylinder-head-f0/source/certify_fixed_face.py': '9b13f4dc7f2eca7da04e1587eb1f59a379a0d0c2101026f9b1d999ae09aaebb8',
    'twins/962-cylinder-head-f0/FIXED_FACE_QUALITY.md': '7d93764a19b57fba3788c320a6a6ebbda29e59117fa4c694c6392807ef0a4d1c',
    'twins/962-cylinder-head-f0/source/gmsh_sicn_reference.json': '28cf35720fa94611a17b219b60b2ead8c1153f6ae346e581d32fd1efe08f112d',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def saved_fraction(value):
    if (not isinstance(value, dict) or set(value) != {'numerator', 'denominator'}
            or any(type(v) is not str for v in value.values())
            or int(value['denominator']) <= 0):
        raise ValueError('Exact saved rational required')
    return Fraction(int(value['numerator']), int(value['denominator']))


def outer_radius_squared(S, T):
    """Q>=1/10 implies |p-centroid|^2 < U; U uses the positive root sum."""
    if type(S) is not Fraction or type(T) is not Fraction or S <= 0 or T <= 0 or S*S > 841*T:
        raise ValueError('Positive isolated-face-compatible S,T required')
    return Fraction(2, 3) * (899*T/S - S)


def disjoint(D, U, V):
    """Strict separation of two closed outer balls; no square roots or tolerance."""
    if any(type(x) is not Fraction for x in (D,U,V)) or min(D, U, V) < 0:
        raise ValueError('Nonnegative squared distances/radii required')
    gap = D-U-V
    return gap > 0 and gap*gap > 4*U*V


def face_bound(row):
    points = row['fixed_triple_coordinates_mm']
    bits = row['fixed_triple_binary64_hex']
    if (len(points) != 3 or any(len(p) != 3 for p in points)
            or [[float(x).hex() for x in p] for p in points] != bits):
        raise ValueError('Exact saved fixed-triple binary64 association required')
    q = [[Fraction.from_float(float(x)) for x in p] for p in points]
    centre = [sum(p[k] for p in q)/3 for k in range(3)]
    proof = row['exact_fixed_face_certificate']
    S = Fraction(2, 3) * saved_fraction(proof['sum_squared_edge_lengths_mm2'])
    T = Fraction(4, 3) * saved_fraction(proof['cross_squared_mm4'])
    if 4*T/(S*S) != saved_fraction(row['tight_isolated_apex_ceiling']['exact_triangle_SICN_squared']):
        raise ValueError('Saved ideal-face S,T and exact q-squared differ')
    return centre, outer_radius_squared(S, T), S, T


def main():
    if OUT.exists():
        raise FileExistsError('Fresh output required')
    for name, digest in PINS.items():
        p = ROOT/name
        if p.is_symlink() or sha(p) != digest:
            raise ValueError('Frozen saved input changed: '+name)
    fixed = json.loads((ROOT/FIXED).read_text())
    previous = json.loads((ROOT/GROUPS).read_text())
    ties = json.loads((ROOT/TIES).read_text())
    analysis = fixed['fixed_boundary_triple_ceiling_analysis']
    rows = analysis['rows']
    if (fixed['status'] != 'direct_saved_file_readback_completed'
            or fixed['bound_inputs_unchanged'] is not True
            or len(rows) != 195 or analysis['count'] != 195):
        raise ValueError('Complete stopped195-row input required')
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['interior_apex_node_tag']].append(row)
    if len({r['tetrahedron_tag'] for r in rows}) != 195 or len(grouped) != 144:
        raise ValueError('Complete unique195-cell/144-apex partition required')
    if dict(Counter(len(v) for v in grouped.values())) != {1:96, 2:46, 3:1, 4:1}:
        raise ValueError('Frozen apex multiplicities differ')
    shared = {a: sorted(v, key=lambda r:r['tetrahedron_tag']) for a,v in grouped.items() if len(v)>1}
    expected = {g['interior_apex_node_tag']: [r['tetrahedron_tag'] for r in g['fixed_triples']]
                for g in previous['shared_apex_groups_only']}
    if {a:[r['tetrahedron_tag'] for r in v] for a,v in shared.items()} != expected:
        raise ValueError('Exact prior48-group membership required')
    bounds = {}
    faces = []
    for apex, group in sorted(shared.items()):
        for row in group:
            tag = row['tetrahedron_tag']; centre,U,S,T = face_bound(row)
            bounds[tag] = (centre,U)
            faces.append(dict(tetrahedron_tag=tag, interior_apex_node_tag=apex,
                fixed_triple_node_tags=row['fixed_triple_node_tags'],
                source_coordinate_bits_sha256=row['fixed_triple_coordinate_bits_sha256'],
                exact_centroid_mm=[rational(x) for x in centre], exact_S_mm2=rational(S),
                exact_T_mm4=rational(T), squared_radius_upper_mm2=rational(U)))
    pairs = []
    for apex, group in sorted(shared.items()):
        for first,second in combinations(group,2):
            tags = [first['tetrahedron_tag'],second['tetrahedron_tag']]
            (c,U),(d,V) = [bounds[t] for t in tags]
            D = sum((x-y)**2 for x,y in zip(c,d)); gap = D-U-V
            pairs.append(dict(interior_apex_node_tag=apex, tetrahedron_tags=tags,
                exact_centroid_distance_squared_mm2=rational(D), gap_D_minus_U_minus_V_mm2=rational(gap),
                exact_gap_squared_minus_4UV_mm4=rational(gap*gap-4*U*V),
                strictly_disjoint_outer_balls_certified=disjoint(D,U,V),
                decision='strict_disjointness_certificate' if disjoint(D,U,V) else 'inconclusive'))
    if len(faces) != 99 or len(pairs) != 55:
        raise ValueError('All99 shared rows and55 within-apex pairs required')
    count = sum(p['strictly_disjoint_outer_balls_certified'] for p in pairs)
    report = dict(schema='962-exact-saved-shared-apex-centroid-ball-screen/v1',
        status='exact_shared_apex_pair_obstruction_certified' if count else 'no_shared_pair_obstruction_certified_inconclusive',
        source_sha256=sha(Path(__file__)), input_hashes=PINS, shared_groups=48, shared_cells=99,
        complete_pair_count=55, certified_disjoint_pair_count=count,
        exact_arithmetic='Fraction only; stored binary64 coordinates; no square roots/tolerance/grid',
        necessary_bound='Q>=.1 implies u=|sqrt(3/2)*(p-centroid)|^2 lies between roots of S*u^2+(S^2-899*T)*u+S*T<=0. Both roots positive; u+<root sum. Physical squared radius U=(2/3)*(899*T/S-S).',
        pair_certificate='D>U+V and (D-U-V)^2>4*U*V; strict separation of necessary outer balls',
        source_corner_scope='Unsigned necessary bound symmetric in the fixed triple; it also bounds the positive native-orientation subset. No exterior-face membership inferred.',
        smallest_ceiling_ties_retained=ties['all_exact_minimum_ties'],
        no_feasibility_or_global_infeasibility_from_inconclusive_pairs=True,
        selected_scope='Only the195 originally positive-poor class3 cells; initially-good fixed-triple cells are not added.',
        all_other_incident_cell_constraints_not_tested=True,
        fixed_boundary_connectivity_scope_only=True, native_or_optimizer_calls=0,
        engineering_accepted=False, physics_qualified=False, manufacturing_authorized=False,
        face_bounds=faces, pair_results=pairs)
    for name,digest in PINS.items():
        if sha(ROOT/name) != digest:raise ValueError('Input changed during query')
    report['bound_inputs_unchanged'] = True
    OUT.mkdir()
    with (OUT/'report.json').open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__ == '__main__':
    main()
