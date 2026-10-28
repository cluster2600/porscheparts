"""Independent saved-certificate verifier: Cartesian Gram polynomials and integer Sturm.

No worker import, copied scientific kernel, SymPy, native geometry or binary64 proposal.
The only mathematical input is the frozen saved certificate and accepted saved context.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations, permutations
from functools import lru_cache
import gzip, hashlib, json, math, struct, sys, time, traceback

ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E = ROOT / 'work/962-engineering'
HERE = Path(__file__).resolve().parent
OUT = E / 'head-star-current24-exact-segment-feasibility-002'
STATE = {'status': 'INCOMPLETE', 'phase': 'start', 'checks': 0, 'cases': []}

def insist(value, message):
    STATE['checks'] += 1
    if not value:
        raise AssertionError(message)

def fraction(value):
    if isinstance(value, dict):
        return F(int(value['numerator']), int(value['denominator']))
    return F(value)

def clean(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return tuple(p or [F(0)])

def plus(a, b):
    return clean([(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)
                  for i in range(max(len(a), len(b)))])

def scale(a, q):
    return clean([x*q for x in a])

def minus(a, b):
    return plus(a, scale(b, -1))

def times(a, b):
    out = [F(0)] * (len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i+j] += x*y
    return clean(out)

def power(a, exponent):
    answer = (F(1),)
    for _ in range(exponent):
        answer = times(answer, a)
    return answer

def value(p, q):
    answer = F(0)
    for c in reversed(p):
        answer = answer*q+c
    return answer

def primitive(p):
    p = clean(p)
    den = math.lcm(*(x.denominator if isinstance(x, F) else 1 for x in p))
    ints = [int(x*den) for x in p]
    divisor = math.gcd(*ints) or 1
    return clean([x//divisor for x in ints])

def sign_at(p, q):
    # Homogeneous integer Horner evaluation; no approximate root evaluation.
    a, b = q.numerator, q.denominator
    result, den_power = int(p[-1]), 1
    for c in reversed(p[:-1]):
        den_power *= b
        result = result*a + int(c)*den_power
    return (result > 0)-(result < 0)

def positive_prem(a, b):
    # Positive scalar multiples preserve Sturm signs. Each elimination multiplies
    # by abs(lc(b)); gcd division is positive, never an uncontrolled sign change.
    a, b = primitive(a), primitive(b)
    while a != (0,) and len(a) >= len(b):
        shift = len(a)-len(b)
        lead, orient = a[-1], 1 if b[-1] > 0 else -1
        work = [x*abs(b[-1]) for x in a]
        for i, c in enumerate(b):
            work[i+shift] -= lead*orient*c
        a = primitive(work)
    return a

@lru_cache(maxsize=None)
def sturm(p):
    p = primitive(p)
    if len(p) == 1:
        return (p,)
    derivative = primitive([i*p[i] for i in range(1, len(p))])
    seq = [p, derivative]
    while True:
        remainder = positive_prem(seq[-2], seq[-1])
        if remainder == (0,):
            break
        seq.append(primitive([-x for x in remainder]))
    return tuple(seq)

def variations(seq, q):
    if q == '-inf':
        signs = [((x[-1] > 0)-(x[-1] < 0)) * (-1 if (len(x)-1) % 2 else 1)
                 for x in seq]
    elif q == '+inf':
        signs = [(x[-1] > 0)-(x[-1] < 0) for x in seq]
    else:
        signs = [sign_at(x, q) for x in seq]
    signs = [s for s in signs if s]
    return sum(a != b for a, b in zip(signs, signs[1:]))

def roots_between(p, a, b):
    return variations(sturm(primitive(p)), a)-variations(sturm(primitive(p)), b)

def poly_record(row):
    descending = [fraction(x) for x in row['rational_coefficients_descending']]
    p = clean(reversed(descending))
    insist(len(descending) == len(p), 'Untrimmed recorded polynomial')
    insist(row['degree'] == (None if p == (0,) else len(p)-1), 'Polynomial degree metadata')
    den = math.lcm(*(x.denominator for x in descending))
    ints = [int(x*den) for x in descending]
    content = math.gcd(*ints) or 1
    insist(int(row['positive_denominator_lcm']) == den, 'Denominator LCM')
    insist(int(row['positive_content_divisor']) == content, 'Positive content')
    insist([int(x) for x in row['primitive_integer_coefficients_descending']] ==
            [x//content for x in ints], 'Primitive integer coefficients')
    return p

def cartesian_polynomials(start, end):
    vertices = [[(F(x), F(y)-F(x)) for x, y in zip(a, b)] for a, b in zip(start, end)]
    def edge(a, b):
        return [minus(vertices[b][i], vertices[a][i]) for i in range(3)]
    def inner(a, b):
        result = (F(0),)
        for x, y in zip(a, b):
            result = plus(result, times(x, y))
        return result
    rows = [edge(0, i) for i in (1, 2, 3)]
    determinant = (F(0),)
    for order in permutations(range(3)):
        inversions = sum(order[i] > order[j] for i in range(3) for j in range(i+1, 3))
        term = (F(1),)
        for i in range(3):
            term = times(term, rows[i][order[i]])
        determinant = plus(determinant, scale(term, -1 if inversions % 2 else 1))
    edge_sum = (F(0),)
    for a, b in combinations(range(4), 2):
        e = edge(a, b)
        edge_sum = plus(edge_sum, inner(e, e))
    face_sum = (F(0),)
    for a, b, c in combinations(range(4), 3):
        e, f = edge(a, b), edge(a, c)
        face_sum = plus(face_sum, minus(times(inner(e, e), inner(f, f)), power(inner(e, f), 2)))
    gate = minus(scale(power(determinant, 2), 3600), times(edge_sum, face_sum))
    return determinant, edge_sum, face_sum, gate

def word(x):
    return struct.pack('<d', x)

def boundary_faces(cells):
    incidence = {}
    for conn in cells:
        for omit in range(4):
            face = tuple(conn[i] for i in range(4) if i != omit)
            if omit % 2:
                face = (face[0], face[2], face[1])
            inv = sum(face[i] > face[j] for i in range(3) for j in range(i+1, 3))
            incidence.setdefault(tuple(sorted(face)), []).append(-1 if inv % 2 else 1)
    insist(all(len(v) <= 2 and (len(v) == 1 or sum(v) == 0) for v in incidence.values()),
           'Oriented manifold cell-star boundary')
    return {k: v[0] for k, v in incidence.items() if len(v) == 1}

def snapshot_interval(s):
    return tuple(fraction(x) for x in s['isolating_interval'])

def compare_boundary_to_rational(s, q, factors):
    a, b = snapshot_interval(s)
    if a == b:
        return (a > q)-(a < q)
    if q <= a:
        return 1
    if q >= b:
        return -1
    ref = s['algebraic_factor_references'][0]
    p = factors[ref['factor_ID']]['integer']
    if sign_at(p, q) == 0:
        return 0
    return -1 if roots_between(p, a, q) == 1 else 1

def check_classification(case, polys):
    cert = case['real_feasibility']
    constraints = cert['constraints']
    insist(len(constraints) == len(polys), 'Complete determinant/quality constraint count')
    factors, owners = {}, {}
    for item in cert['irreducible_factors']:
        fid = item['factor_ID']; p = poly_record(item['monic_polynomial']); ip = primitive(p)
        insist(fid not in factors and len(p) > 1 and p[-1] == 1, 'Unique monic factor identity')
        seq = sturm(ip)
        insist(len(seq[-1]) == 1, 'Each factor independently square-free')
        recorded_chain = [primitive(poly_record(x)) for x in item['sturm_chain']]
        insist(recorded_chain == list(seq), 'Every recorded Sturm chain independently reconstructed up to positive content')
        total = variations(seq, '-inf')-variations(seq, '+inf')
        insist(total == item['total_real_roots'] == len(item['all_real_isolators']), 'Complete total real-root count')
        last = None
        for index, root in enumerate(item['all_real_isolators']):
            a, b = snapshot_interval(root)
            insist(root['real_root_index'] == index and a <= b, 'Global factor root ordinal')
            insist(root['algebraic_factor_references'] == [{'factor_ID': fid, 'real_root_index': index}],
                   'Factor-root reference identity')
            insist(root['exact_rational'] == (None if a != b else {'numerator': str(a.numerator), 'denominator': str(a.denominator)}),
                   'Factor rational/algebraic snapshot')
            insist(last is None or last <= a, 'Ordered factor isolators')
            if a == b:
                insist(sign_at(ip, a) == 0, 'Exact rational factor root')
            else:
                insist(sign_at(ip, a) != 0 and sign_at(ip, b) != 0 and roots_between(ip, a, b) == 1,
                       'Certified one-root strict bracket')
            insist(root['root_count_in_saved_interval'] == 1, 'Declared isolated-root count')
            last = b
        factors[fid] = dict(poly=p, integer=ip, row=item)
        owners[fid] = {}
    insist(len({x['poly'] for x in factors.values()}) == len(factors), 'Distinct factor keys')
    integer_constraints = []
    for cid, row in enumerate(constraints):
        tag, kind, p = polys[cid]
        insist(row['constraint_ID'] == cid and row['cell_tag'] == tag and row['kind'] == kind,
               'Every original cell/constraint association')
        insist(poly_record(row['polynomial']) == p, 'Constraint polynomial equals independent geometry')
        insist(row['relation'] == ('strictly_positive' if kind == 'D' else 'nonnegative'), 'Strict determinant versus closed quality')
        insist(row['constant_or_zero'] is (len(p) == 1), 'Constant and zero explicit')
        if len(p) > 1:
            rebuilt = (fraction(row['factorization_content']),)
            used = []
            for part in row['factorization']:
                fid = part['factor_ID']; raw = poly_record(part['raw_factor']); mult = part['multiplicity']
                insist(type(mult) is int and mult > 0 and scale(raw, 1/raw[-1]) == factors[fid]['poly'], 'Factor multiplicity and raw/monic link')
                for previous in used:
                    insist(len(sturm(primitive(factors[previous]['poly']))[-1]) == 1, 'Square-free prior factor')
                    aa, bb = primitive(raw), factors[previous]['integer']
                    while bb != (0,):
                        aa, bb = bb, positive_prem(aa, bb)
                    insist(len(aa) == 1, 'Within-polynomial factors coprime, so recorded multiplicities exact')
                used.append(fid)
                owners[fid][str(cid)] = owners[fid].get(str(cid), 0)+mult
                rebuilt = times(rebuilt, power(raw, mult))
            insist(rebuilt == p, 'Complete exact factor-product reconstruction')
        else:
            insist(row['factorization'] == [], 'No hidden factors on constants/zero')
        integer_constraints.append(primitive(p))
    expected_refs = set()
    for fid, data in factors.items():
        ip = data['integer']
        for idx, root in enumerate(data['row']['all_real_isolators']):
            insist(root['constraint_multiplicities'] == owners[fid], 'Full original factor-root multiplicity ownership')
            a, b = snapshot_interval(root)
            inside = (0 <= a <= 1) if a == b else not (b <= 0 or a >= 1)
            if inside and a < 0 < b:
                inside = roots_between(ip, a, F(0)) == 0
            if inside and a < 1 < b:
                inside = roots_between(ip, a, F(1)) == 1
            if inside:
                expected_refs.add((fid, idx))
    bounds = cert['ordered_boundaries']; insist(len(bounds) >= 2, 'Both segment endpoints retained')
    insist(snapshot_interval(bounds[0]) == (F(0), F(0)) and snapshot_interval(bounds[-1]) == (F(1), F(1)), 'Strict segment endpoint identities')
    refs_seen = set()
    for i, point in enumerate(bounds):
        a, b = snapshot_interval(point)
        insist(0 <= a <= b <= 1, 'All selected root brackets inside segment')
        insist(point['exact_rational'] == (None if a != b else {'numerator': str(a.numerator), 'denominator': str(a.denominator)}), 'Rational versus algebraic snapshot')
        if i:
            insist(snapshot_interval(bounds[i-1])[1] < a, 'Certified strict global boundary order')
        own = {}
        for ref in point['algebraic_factor_references']:
            key = (ref['factor_ID'], ref['real_root_index']); insist(key not in refs_seen, 'No duplicated selected factor root')
            refs_seen.add(key); data = factors[key[0]]
            root = data['row']['all_real_isolators'][key[1]]
            insist(snapshot_interval(root) == (a, b), 'Boundary/factor isolator association')
            for cid, m in owners[key[0]].items():
                own[cid] = own.get(cid, 0)+m
        insist(point['constraint_multiplicities'] == own, 'Boundary full original owner set')
        insist(a == b or len(point['algebraic_factor_references']) == 1,
               'This saved certificate has one monic factor per nonrational root; no unproved cross-factor merge')
    insist(refs_seen == expected_refs, 'Every and only factor root in closed segment retained')
    atoms = cert['complete_sign_atoms']; insist(len(atoms) == 2*len(bounds)-1, 'Complete point/open-interval atom partition')
    for ai, atom in enumerate(atoms):
        bi = ai//2
        if ai % 2:
            insist(atom['kind'] == 'open_interval' and atom['left_boundary'] == bi and atom['right_boundary'] == bi+1, 'Open atom joins')
            sample = fraction(atom['sign_sample'])
            insist(snapshot_interval(bounds[bi])[1] < sample < snapshot_interval(bounds[bi+1])[0], 'Exact open-atom sample validity')
            signs = [sign_at(p, sample) for p in integer_constraints]
        else:
            insist(atom['kind'] == 'point' and atom['boundary'] == bi, 'Point atom joins')
            a, b = snapshot_interval(bounds[bi]); own = bounds[bi]['constraint_multiplicities']
            signs = [0 if a != b and str(cid) in own else sign_at(p, (a+b)/2)
                     for cid, p in enumerate(integer_constraints)]
        insist(atom['signs'] == signs, 'Every original polynomial sign independently evaluated')
        failed = [cid for cid, s in enumerate(signs) if not (s > 0 if polys[cid][1] == 'D' else s >= 0)]
        insist(atom['atom_ID'] == ai and atom['blocking_constraint_IDs'] == failed and atom['feasible'] is (not failed), 'Every blocker and strict/closed gate')
    for bi in range(1, len(bounds)-1):
        left, right = atoms[2*bi-1]['signs'], atoms[2*bi+1]['signs']
        for cid, mult in bounds[bi]['constraint_multiplicities'].items():
            k = int(cid)
            insist(left[k] != 0 and right[k] == left[k]*(-1 if mult % 2 else 1), 'Original multiplicity sign crossing')
    runs, active = [], []
    for atom in atoms:
        if atom['feasible']:
            active.append(atom['atom_ID'])
        elif active:
            runs.append(active); active = []
    if active:
        runs.append(active)
    comps = cert['connected_feasible_components']; insist(len(comps) == len(runs), 'All connected components retained')
    witnesses = []
    for ci, (component, run) in enumerate(zip(comps, runs)):
        li, ri = run[0]//2, (run[-1]+1)//2
        lc, rc = run[0] % 2 == 0, run[-1] % 2 == 0
        insist(component['component_index'] == ci and component['atom_IDs'] == run and
               component['left_boundary'] == li and component['right_boundary'] == ri and
               component['left_closed'] is lc and component['right_closed'] is rc, 'Component endpoints/singletons')
        sample = component['canonical_exact_sample']
        if sample['kind'] == 'exact_singleton':
            insist(li == ri and lc and rc and sample['algebraic_point'] == bounds[li], 'Exact singleton witness identity')
            witnesses.append({'component': ci, 'kind': 'exact_singleton', 'valid': True})
        else:
            q = fraction(sample['value'])
            left = compare_boundary_to_rational(bounds[li], q, factors)
            right = compare_boundary_to_rational(bounds[ri], q, factors)
            insist((left < 0 or left == 0 and lc) and (right > 0 or right == 0 and rc), 'Canonical rational witness belongs to component')
            insist(all(sign_at(p, q) > 0 if polys[k][1] == 'D' else sign_at(p, q) >= 0
                       for k, p in enumerate(integer_constraints)), 'Canonical rational witness satisfies all original constraints')
            witnesses.append({'component': ci, 'kind': sample['kind'], 'value': sample['value'],
                              'valid': True, 'minimum_denominator_property_independently_proved': False})
        insist(component['correctly_rounded_binary64_proposal'] is None and component['actual_word_recheck'] is None and component['binary64_existence_claim'] is False, 'No binary64 witness upgrade')
    insist(cert['real_path_feasible'] is bool(comps) and cert['real_path_classification_complete'] is True,
           'Complete finite-path classification status')
    insist(cert['binary64_word_construction_supported'] is False and cert['binary64_completeness'] is False,
           'Finite real path is not a binary64 completeness claim')
    return dict(factors=len(factors), real_factor_roots=sum(x['row']['total_real_roots'] for x in factors.values()),
                selected_root_boundaries=len(bounds)-2, atoms=len(atoms), feasible_components=len(comps),
                witnesses=witnesses, all_constraint_signs_checked=len(atoms)*len(constraints))

def no_duplicates(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError('Duplicate JSON key: '+k)
        result[k] = v
    return result

def load(path):
    return json.loads(path.read_text(), object_pairs_hook=no_duplicates,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))

def run_review():
    STATE['phase'] = 'bounded saved decode'
    manifest = load(OUT/'manifest.json'); data = (OUT/'real-segment-feasibility.json.gz').read_bytes()
    insist(len(data) == 5750611 and hashlib.sha256(data).hexdigest() == '74773078ca9ccccf02a9e3e7530b6fe753d7af065723ab70f0778976b8943226', 'Frozen compressed identity')
    chunks, count, digest = [], 0, hashlib.sha256()
    with gzip.open(OUT/'real-segment-feasibility.json.gz', 'rb') as stream:
        while True:
            block = stream.read(min(1048576, 35016403-count+1))
            if not block:
                break
            count += len(block); insist(count <= 35016403, 'Fixed inflation bound')
            digest.update(block); chunks.append(block)
    insist(count == 35016403 and digest.hexdigest() == '3e5d8c2d788e8510b8894e1a5811ef89c3a42716e1c1c2ba0debe4c20aed8c33', 'Full logical EOF/CRC/count/hash')
    logical = b''.join(chunks); chunks.clear()
    cert = json.loads(logical, object_pairs_hook=no_duplicates,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    del logical, data
    STATE['logical_bytes'] = count
    actual = load(E/'head-star-current24-exact-segment-feasibility-execution-prep-003/actual-contract.json')
    held = load(E/'head-star-current24-exact-segment-feasibility-prep-002/held-preparation.json')
    tuples = load(E/'head-star-current24-analytic-apex-prep-001/component-tuples.json')
    endpoint = load(E/'head-star-current24-analytic-apex-001/candidate-diagnostic.json')
    app = load(E/'head-star-current110-pass62-application-001/worker-report.json')
    selected = load(E/'head-star-current110-pass62-apply-prep-002/selected-proposals.json')
    groups = load(E/'head-star-current110-component-sicn-prep-001/component-manifest.json')
    insist(cert['source'] == actual['worker'] == manifest['source'] and cert['held_preparation'] == actual['held_preparation'] == manifest['held_preparation'], 'Scientific source/held joins')
    insist(cert['own_actual'] == manifest['own_actual'] and cert['input_records'] == held['input_records'] == actual['input_records'], 'Actual and all55 input joins')
    insist(cert['tuple_list'] == actual['tuple_list'] and cert['protection'] == endpoint['protection'], 'Tuple and prior-protection metadata')
    census = app['after']['complete_native_census']['complete_seed_star_census']
    points = {x['node_tag']: x['coordinates_mm'] for x in census['unique_incident_nodes']}
    for node in census['unique_incident_nodes']:
        insist([x.hex() for x in node['coordinates_mm']] == node['binary64_hex'], 'Saved context decimal/word association')
    cells = {x['tetrahedron_tag']: x['node_tags'] for x in census['complete_incident_tetrahedra']}
    seeds = set(census['movable_node_tags']); insist(len(points) == 271 and len(cells) == 499 and len(seeds) == 16, '271/499/16 full context')
    insist(sum(x['initially_positive_poor'] for x in census['complete_incident_tetrahedra']) == 24 and
           sum(len(set(c)&seeds) > 1 for c in cells.values()) == 33, '24poor/475good/33shared coverage')
    accepted = [x for x in groups['cases'] if x['component_ID'] in selected['component_IDs']]
    protected_nodes = {n for x in accepted for n in x['movable_node_tags']}
    protected_cells = {n for x in accepted for n in x['tetrahedron_tags']}
    insist(len(protected_nodes) == 66 and len(protected_cells) == 1983 and not protected_nodes&seeds and not protected_cells&set(cells), '66/1983 complete prior protection')
    baseline = {x['tetrahedron_tag']: x for x in endpoint['complete499_before_cell_rows']}
    endpoints = {x['tuple_ID']: x for x in endpoint['complete19_tuple_results']}
    expected_cases = {x['tuple_ID']: x for x in tuples['tuples']}
    insist(len(cert['complete19_segments']) == len(expected_cases) == 19, 'All nineteen tuples')
    seen, union, baseline_seen = set(), set(), set()
    for case in cert['complete19_segments']:
        tid = case['tuple_ID']; STATE['phase'] = tid
        insist(tid not in seen and tid in expected_cases, 'Unique fixed tuple identity'); seen.add(tid)
        descriptor = expected_cases[tid]
        insist(all(case[k] == v for k, v in descriptor.items()), 'Full tuple descriptor equality')
        target = endpoints[tid]
        changes = {x['seed_node_tag']: x['coordinates_mm'] for x in target['selected_proposal_associations']}
        endpoint_rows = {x['tetrahedron_tag']: x for x in target['complete_cell_rows']}
        local = case['complete_cell_polynomials']; insist(len(local) == descriptor['full_cell_count'] and [x['tetrahedron_tag'] for x in local] == descriptor['full_tetrahedron_tags'], 'Complete ordered full-star cells')
        poly_constraints, volume, rowproof = [], (F(0),), []
        native_boundary = boundary_faces([cells[t] for t in descriptor['full_tetrahedron_tags']])
        insist(not ({n for f in native_boundary for n in f}&set(changes)), 'All moving seeds strictly internal to full-star boundary')
        saved_boundary = {}
        for f in case['fixed_oriented_boundary']['oriented_boundary_faces']:
            inv = sum(f[i] > f[j] for i in range(3) for j in range(i+1, 3))
            saved_boundary[tuple(sorted(f))] = -1 if inv % 2 else 1
        insist(saved_boundary == native_boundary, 'Complete fixed oriented boundary equality')
        endpoint_fails = 0
        for index, row in enumerate(local):
            tag = row['tetrahedron_tag']; conn = cells[tag]; union.add(tag)
            insist(row['ordered_node_tags'] == conn, 'Ordered native connectivity')
            starts = [points[n] for n in conn]; ends = [changes.get(n, points[n]) for n in conn]
            insist(all(word(a) == word(b) for v,w in zip(row['original_vertices_mm'], starts) for a,b in zip(v,w)), 'Every original vertex bit')
            insist(all(word(a) == word(b) for v,w in zip(row['endpoint_vertices_mm'], ends) for a,b in zip(v,w)), 'Every endpoint/fixed vertex bit')
            ds = cartesian_polynomials(starts, ends)
            for key, p in zip(('D','S','T','P'), ds):
                insist(poly_record(row[key]) == p, 'Every Cartesian determinant/edge/face/quality coefficient')
            insist(row['D_constraint_ID'] == 2*index and row['P_constraint_ID'] == 2*index+1, 'Cell constraint IDs')
            for parameter, saved in [(F(0), baseline[tag]), (F(1), endpoint_rows[tag])]:
                d,s,t,p = [value(x, parameter) for x in ds]
                q2 = F(36)*d*d/(s*t) if s*t else None
                insist(d == fraction(saved['exact_native_ordered_determinant_mm3']) and q2 == (None if saved['exact_SICN_squared'] is None else fraction(saved['exact_SICN_squared'])), 'Every saved endpoint determinant/quality')
                insist(saved['positive_orientation'] is (d > 0) and saved['exact_point1_gate_passed'] is (d > 0 and p >= 0), 'Preserved endpoint gate/failure')
                if parameter == 1 and not saved['exact_point1_gate_passed']:
                    endpoint_fails += 1
            baseline_seen.add(tag); volume = plus(volume, ds[0]); poly_constraints.extend([(tag,'D',ds[0]),(tag,'P',ds[3])])
            rowproof.append({'tetrahedron_tag':tag,'all4_coefficients_and_both_endpoints_checked':True})
        insist(len(volume) == 1 and poly_record(case['own_summed_determinant_polynomial']) == volume and case['own_signed_volume_polynomial_constant'] is True, 'Exact complete volume polynomial identity')
        classified = check_classification(case, poly_constraints)
        insist(case['word_construction_status'] == 'UNSUPPORTED_NOT_ATTEMPTED' and case['rounded_word_proposals'] == [] and case['word_rechecks'] == [] and case['candidate_or_geometry_application'] is False, 'No geometry or word application')
        STATE['cases'].append(dict(tuple_ID=tid,component_ID=case['component_ID'],cells=len(local),
             endpoint_failed_dispositions=endpoint_fails,cell_checks=rowproof,**classified))
        print(json.dumps(dict(case=tid,cells=len(local),feasible_components=classified['feasible_components'])),flush=True)
    insist(seen == set(expected_cases) and union == baseline_seen == set(cells), 'All19/499 complete membership union')
    insist(sum(x['cells'] for x in STATE['cases']) == 916 and cert['complete_cell_dispositions'] == 916 and cert['complete_constraint_associations'] == 1832, '916/1832 totals')
    insist(cert['binary64_word_proposal_count'] == 0 and cert['binary64_existence_or_completeness'] is False and cert['global_infeasibility_proved'] is False and all(v is False for v in cert['qualification'].values()), 'All negative authority claims retained')
    STATE.update(status='PASS_ALL_SAVED_FINITE_CHECKS_WITH_LIMITS',phase='complete',
       cells=916,constraints=1832,unique_cells=499,baseline_unique_rows=499,
       feasible_tuple_IDs=[x['tuple_ID']for x in STATE['cases']if x['feasible_components']],
       minimum_denominator_witness_claim='NOT_INDEPENDENTLY_PROVED; exact witness membership and all original inequalities checked',
       irreducibility_claim='NOT_INDEPENDENTLY_FACTORED_OVER_QQ; exact products,multiplicities,square-freeness,within-polynomial coprimality,complete independent Sturm roots and certified in-segment order checked')

def selftest():
    insist(roots_between((-1,0,1), '-inf','+inf') == 2, 'Synthetic two roots')
    insist(roots_between((1,0,1), '-inf','+inf') == 0, 'Synthetic no roots')
    insist(len(sturm((1,-2,1))[-1]) == 2, 'Synthetic repeated root detected')
    insist(roots_between((-1,0,1), F(0),F(2)) == 1, 'Synthetic rational bracket')
    insist(sign_at((1,-3,2),F(1,3)) == 1, 'Synthetic homogeneous evaluation')
    STATE.update(status='PASS_SYNTHETIC_INDEPENDENT_POLYNOMIAL_CHECKS',phase='synthetic_only')

if __name__ == '__main__':
    began = time.monotonic()
    synthetic = '--self-test' in sys.argv
    try:
        selftest() if synthetic else run_review()
    except BaseException as exc:
        STATE.update(status='REVIEW_FAILURE_RETAINED',error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
    STATE['wall_seconds'] = time.monotonic()-began
    target = HERE/('synthetic-checks.json' if synthetic else 'arithmetic-checks.json')
    with target.open('x') as stream:
        json.dump(STATE,stream,indent=2,allow_nan=False);stream.write('\n')
    target.chmod(0o444)
    print(json.dumps(dict(status=STATE['status'],phase=STATE['phase'],checks=STATE['checks'],wall_seconds=STATE['wall_seconds'])),flush=True)
    raise SystemExit(0 if STATE['status'].startswith('PASS_') else 2)
