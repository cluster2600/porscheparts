"""Independent fixed47 saved-association review; no geometric predicate replay."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
from collections import Counter, defaultdict
import hashlib
import json
import math
import struct
import time

ROOT = Path('project-root://')
BASE = 'work/962-engineering/'
OUT = Path(__file__).resolve().parent
PREFIX = 'head-star-current204-case-domains-'
MASTER = BASE + PREFIX + 'root-execution-001/closed-result.json'
INDEX = BASE + PREFIX + 'execution-prep-001/index.json'
SOURCE = BASE + PREFIX + 'prep-002/certify_domain.py'
MANIFEST = BASE + PREFIX + 'prep-002/case-manifest.json'
BATCH = BASE + 'head-star-current204-batch-shells-001/report.json'
CONTEXT = BASE + 'head-star-current204-union-context-001/readback-report.json'
CENSUS = BASE + 'head-star-current204-full-stars-001/readback-report.json'
NATIVE_CHECK = BASE + 'head-star-current204-Netgen-result-peer-001/independent-saved-check.json'
PINS = {
    MASTER: 'ed51811c2706f0cc13046a5169bd2b923f44d99431ca9196eb6450cb42e4296b',
    INDEX: '9f870ba43a3967d8ff735a660c15fcc13251aa4ac5e586d14eee1b577e719806',
    SOURCE: '7060580b7aa2743dec511bb9fc5e8cfb40ef86ea3332b068c5de9c845422efc8',
    MANIFEST: '0628df655f81a509a43d4b31e64e42f9285226e1653969f939dfa681d8c34cbd',
    BASE + PREFIX + 'source-peer-002/review.json': '435814e5c6a387745f6b7bd8afbc3e439ef16f90b06fcc6a064504a62782892b',
    BASE + PREFIX + 'root-source-001/review.json': 'e26e453b159fdd3befa0d6fa77c0117bb8aaec1a1ac5df12cefb74b9d8baa4e4',
    BASE + PREFIX + 'child-peer-001/review.json': '361df0ad58d6ab4cb7edbfb4d883d7639d2de198a7656b089d131c0660009877',
    BASE + PREFIX + 'root-execution-001/result-review.json': 'e5c37e918b706ebc4d006d071b247abe67e1c410923692a365225d64442dc75c',
}
QUAL = dict(native_application_authorized=False, head_execution_authorized=False,
    stitching_authorized=False, engineering_accepted=False, physics_qualified=False,
    manufacturing_authorized=False, material_qualified=False, process_calibrated=False)
CONTROL = dict(wall_timeout_seconds=300, start_new_session=True,
    timeout_group_SIGTERM_then_SIGKILL_if_needed=True,
    owned_process_wait_and_reap_required=True, hard_OS_CPU_or_RSS_quota=False)
PY_SHA = '1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60'
FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
PAIR_KEYS = {'shared_node_tags', 'expected_simplex_dimension', 'plane_triples_enumerated',
    'independent_plane_triples', 'intersection_vertices', 'illegal_intersection_vertices',
    'all_illegal_rational_witnesses', 'intersection_equals_tagged_shared_simplex', 'tetrahedron_tags'}
RAW = {}
DATA = {}
BEFORE = {}
start = time.monotonic()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read(name, expected=None):
    path = ROOT / name
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    assert path.is_file() and not path.is_symlink() and path.resolve() == path
    assert path.suffix in {'.json', '.py', '.md', '.diff', '.log', '.stdout', '.stderr'}
    if name not in RAW:
        RAW[name] = path.read_bytes()
        BEFORE[name] = digest(RAW[name])
    if expected is not None:
        assert BEFORE[name] == expected, name
    return RAW[name]

def obj(name, expected=None):
    read(name, expected)
    if name not in DATA:
        DATA[name] = json.loads(RAW[name])
    return DATA[name]

def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()

def ratio(row):
    assert set(row) == {'numerator', 'denominator'}
    assert type(row['numerator']) in (str, int) and type(row['denominator']) in (str, int)
    n, d = int(row['numerator']), int(row['denominator'])
    assert d > 0
    return Fraction(n, d)

def words(xyz):
    assert len(xyz) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in xyz)
    return struct.pack('<3d', *xyz)

def oriented(row):
    # Tag rotation only: no coordinates, halfspaces, predicates or intersections.
    return min(tuple(row[i:] + row[:i]) for i in range(3))

for name, expected in PINS.items():
    read(name, expected)
master = obj(MASTER)
index = obj(INDEX)
manifest = obj(MANIFEST)
assert master['schema'] == '962-root-fixed47-domain-serial-closed/v1'
assert master['selected_count'] == master['attempted_count'] == index['case_count'] == manifest['selected_count'] == 47
assert master['halt'] is None and master['unattempted_apices'] == [] and master['automatic_retry'] is False
assert master['native_or_head_execution'] is False and master['physics_qualified'] is master['manufacturing_authorized'] is False
order = manifest['accepted_apices']
assert order == sorted(set(order)) == index['selected_case_order'] == [x['apex'] for x in master['cases']]
assert master['index_sha256'] == PINS[INDEX] and master['child_peer_sha256'] == PINS[BASE + PREFIX + 'child-peer-001/review.json']
assert index['source_sha256'] == PINS[SOURCE] and index['automatic_retry'] is False
case_map = {c['apex']: c for c in manifest['cases_in_accepted_order']}
assert sorted(case_map) == order
actual_rows = {c['apex']: c for c in index['cases']}
actuals = {}
all_actual_pins = {}
for apex in order:
    item = actual_rows[apex]
    actual = obj(item['actual_path'], item['actual_sha256'])
    assert len(RAW[item['actual_path']]) == item['bytes']
    assert actual['input_count'] == len(actual['input_hashes']) == item['input_count'] == 39
    actuals[apex] = actual
    for name, expected in actual['input_hashes'].items():
        if name in all_actual_pins:
            assert all_actual_pins[name] == expected
        all_actual_pins[name] = expected
        read(name, expected)
assert len(all_actual_pins) == 315
# All exact actual pin bodies are loaded before saved result association checks.
batch = obj(BATCH)
context = obj(CONTEXT)
census = obj(CENSUS)['complete_seed_star_census']
native_check = obj(NATIVE_CHECK)
native_cases = {r['apex']: r for r in native_check['case_ledger']}
batch_cases = {r['apex']: r for r in batch['all_candidate_star_records']}
context_cases = {r['apex']: r for r in context['selected_case_contexts']}
native_points = {r['node_tag']: r for r in context['selected_original_native_node_rows']}
context_faces = {tuple(r['shell_face_key']): r for r in context['all_selected_shell_face_records']}
assert context['original_parent_MSH_sha256'] == manifest['source_parent_MSH_identity_metadata_only']['sha256']
assert context['full_array_sha256s'] == manifest['current_full_array_sha256s']
cases = []
totals = Counter()
aggregate_hist = Counter()

for entry in master['cases']:
    apex = entry['apex']
    case = case_map[apex]
    actual_item = actual_rows[apex]
    actual = actuals[apex]
    record = batch_cases[apex]
    shell, observation = record['shell'], record['observation']
    for value, key in [(record, 'source_record_sha256'), (shell, 'shell_serialized_sha256'), (observation, 'observation_serialized_sha256')]:
        assert digest(encoded(value)) == case[key]
    assert actual['case_apex'] == apex and actual['case_record_sha256'] == case['source_record_sha256']
    assert actual['source'] == SOURCE and actual['source_sha256'] == PINS[SOURCE]
    assert actual['case_manifest'] == MANIFEST and actual['case_manifest_sha256'] == PINS[MANIFEST]
    assert actual['qualification'] == QUAL and actual['ordinary_controls'] == CONTROL
    assert actual['python_sha256'] == PY_SHA and actual['automatic_retry'] is False
    assert actual['diagnostic_execution_authorized'] is True and actual['native_execution_authorized'] is False
    assert actual['method'] == 'complete_old_and_candidate_exact_pairs56_and_common_shell'
    assert actual['exact_counts'] == actual_item['exact_counts'] == {k: case[k] for k in actual_item['exact_counts']}
    assert actual['output_directory'] == case['output_directory'] == actual_item['output_directory']
    closed = obj(entry['closed_path'], entry['closed_sha256'])
    root_dir = str(Path(entry['closed_path']).parent)
    launch_name = root_dir + '/launch.json'
    launch = obj(launch_name, closed['root_launch_sha256'])
    for stream in ['stdout', 'stderr']:
        read(root_dir + '/' + stream + '.log', closed[stream + '_sha256'])
    assert set(entry['output_files']) == set(closed['output_files']) == {'report.json'}
    assert entry['output_files'] == closed['output_files']
    assert closed['case_apex'] == apex and closed['actual_sha256'] == launch['actual_sha256'] == actual_item['actual_sha256']
    assert launch['index_sha256'] == closed['index_sha256'] == PINS[INDEX]
    assert launch['child_peer_sha256'] == closed['child_peer_sha256'] == master['child_peer_sha256']
    assert launch['query_pid'] == closed['query_pid'] == launch['query_pgid']
    assert launch['owned_new_session'] is True and closed['query_reaped'] is closed['observed_owned_leader_absent'] is True
    assert closed['universal_descendant_absence_claimed'] is closed['fallback_SIGKILL'] is False
    assert launch['argv'] == [actual['selected_python'], '-I', '-B', str(ROOT / SOURCE), str(ROOT / actual_item['actual_path']), actual_item['actual_sha256']]
    assert entry['returncode'] == closed['returncode'] == 0
    assert entry['stop_reason'] is entry['error'] is closed['root_stop_reason'] is closed['root_error'] is None
    assert closed['all39_input_pins_actual_python_unchanged'] is True and closed['native_assessor_or_head_execution'] is False
    assert closed['physics_qualified'] is closed['manufacturing_authorized'] is False
    assert entry['wall_seconds'] == closed['wall_seconds'] and 0 <= closed['wall_seconds'] < 300
    report_name = actual['output_directory'] + '/report.json'
    out_dir = ROOT / actual['output_directory']
    assert sorted(p.name for p in out_dir.iterdir()) == ['report.json']
    report = obj(report_name, closed['output_files']['report.json']['sha256'])
    assert len(RAW[report_name]) == closed['output_files']['report.json']['bytes']
    assert report['schema'] == '962-current204-fixed47-one-case-domain-result/v1'
    assert report['status'] == 'same_compact_oriented_local_domain'
    assert report['source_sha256'] == PINS[SOURCE] and report['contract_sha256'] == actual_item['actual_sha256']
    assert report['input_hashes'] == actual['input_hashes']
    assert report['case_apex'] == apex and report['case_record_sha256'] == case['source_record_sha256']
    assert report['qualification'] == QUAL and report['coordinates_changed'] is False
    assert report['native_optimizer_or_meshwrite_calls'] == 0
    for key in ['exact_common_shell_coordinate_words', 'exact_identical_oriented_boundary', 'exact_signed_volume_identity',
                'exact_old_pair_embedding', 'exact_candidate_pair_embedding', 'local_domain_equivalence_proved',
                'bound_inputs_unchanged', 'future_subset_masks_and_originaltag_parameter_projection_required']:
        assert report[key] is True
    assert report['parent_context_sha256'] == all_actual_pins[CONTEXT]
    assert report['pair_failures'] == {'old': 0, 'candidate': 0}
    nv, nf, k, n, m, interior_count = [case[x] for x in ['NV', 'NF', 'K', 'N', 'M', 'I']]
    assert n == nv + interior_count and interior_count >= 1 and m >= k
    assert case['old_unordered_pairs'] == k * (k - 1) // 2
    assert case['candidate_unordered_pairs'] == m * (m - 1) // 2
    assert report['old_complete_unordered_pairs'] == case['old_unordered_pairs']
    assert report['candidate_complete_unordered_pairs'] == case['candidate_unordered_pairs']
    assert report['complete_unordered_pairs'] == case['total_pairs'] == case['old_unordered_pairs'] + case['candidate_unordered_pairs']
    assert report['plane_triples_enumerated'] == case['plane_triples'] == 56 * case['total_pairs']
    mapping = {str(t): i + 1 for i, t in enumerate(shell['local_to_global_node_tags'])}
    mapping[str(apex)] = nv + 1
    assert report['original_global_to_comparison_node_tags'] == mapping
    assert shell['global_to_local_node_tags'] == {key: value for key, value in mapping.items() if key != str(apex)}
    assert len(mapping) == nv + 1 and sorted(map(int, mapping)) == case['old_vertex_tags']
    global_keys = ['boundary_global_node_tags', 'other_interior_global_node_tags']
    local_keys = ['boundary_local_node_tags', 'other_interior_local_node_tags']
    assert set(observation['original_source_classifications']) == set(global_keys)
    assert set(shell['original_source_classifications']) == set(global_keys + local_keys)
    for global_key, local_key in zip(global_keys, local_keys):
        values = observation['original_source_classifications'][global_key]
        assert shell['original_source_classifications'][global_key] == values
        assert shell['original_source_classifications'][local_key] == [mapping[str(t)] for t in values]
    cc = context_cases[apex]
    assert cc['case_record_sha256'] == case['source_record_sha256']
    assert cc['old_cell_tags'] == case['old_tetrahedron_tags'] and cc['shell_node_tags'] == shell['local_to_global_node_tags']
    old_raw = observation['native_ordered_cell_rows']
    assert old_raw == [r for r in census['complete_incident_tetrahedra'] if apex in r['node_tags']]
    assert [{'tetrahedron_tag': r['tetrahedron_tag'], 'node_tags': r['node_tags']} for r in old_raw] == [
        r for r in context['complete_old_selected_apex_incident_rows'] if apex in r['node_tags']]
    old_cells = {r['tetrahedron_tag']: [mapping[str(t)] for t in r['node_tags']] for r in old_raw}
    assert list(old_cells) == case['old_tetrahedron_tags'] and len(old_cells) == k
    old_points = {r['node_tag']: r for r in observation['selected_node_rows']}
    assert set(old_points) == set(map(int, mapping))
    for tag, row in old_points.items():
        assert words(row['coordinates_mm']) == words(native_points[tag]['coordinates_mm'])
        assert [float(v).hex() for v in row['coordinates_mm']] == row['binary64_hex'] == native_points[tag]['binary64_hex']
        assert row['binary64_little_endian_bytes_hex'] == words(row['coordinates_mm']).hex()
        expected_dim = 2 if tag in observation['original_source_classifications']['boundary_global_node_tags'] else 3
        assert native_points[tag]['dimension'] == expected_dim and native_points[tag]['entity_tag'] == 1
    arrays = obj(case['records']['arrays']['path'], case['records']['arrays']['sha256'])
    worker = obj(case['records']['worker']['path'], case['records']['worker']['sha256'])
    saved = arrays['saved_reopen']
    assert arrays['after'] == saved and worker['after'] == worker['saved_reopen']
    assert len(saved['node_tags']) == len(saved['coordinates_mm']) == n
    points = dict(zip(saved['node_tags'], saved['coordinates_mm']))
    assert saved['node_tags'] == sorted(points) and len(points) == n
    assert [words(x) for x in saved['coordinates_mm']] == [words(x) for x in arrays['after']['coordinates_mm']]
    interior = sorted(r[0] for r in worker['saved_reopen']['node_classifications'] if r[1] == 3)
    assert interior == case['candidate_interior_node_tags'] == report['candidate_interior_node_tags']
    assert worker['saved_reopen']['node_classifications'] == [[t, 2 if t <= nv else 3] for t in saved['node_tags']]
    assert worker['saved_reopen']['node_entity_classifications'] == [[t, 2 if t <= nv else 3, 1] for t in saved['node_tags']]
    assert set(points) == set(range(1, nv + 1)) | set(interior)
    assert [r['local_node_tag'] for r in shell['vertex_rows']] == list(range(1, nv + 1))
    for row in shell['vertex_rows']:
        tag = row['source_global_node_tag']
        assert words(points[row['local_node_tag']]) == words(old_points[tag]['coordinates_mm'])
        assert words(points[row['local_node_tag']]).hex() == row['binary64_little_endian_bytes_hex']
    candidate_cells = dict(zip(saved['tetra_tags'], saved['tetra_node_tags']))
    assert list(candidate_cells) == sorted(candidate_cells) and len(candidate_cells) == m
    assert set().union(*(set(x) for x in candidate_cells.values())) == set(points)
    candidate_native = saved['native_qualities']['SICN']
    assert len(candidate_native) == m and all(type(x) is float and math.isfinite(x) and x >= .1 for x in candidate_native)
    assert digest(b''.join(struct.pack('<d', x) for x in candidate_native)) == case['native_SICN']['array_sha256']
    expected_boundary = sorted(oriented(r['local_node_tags']) for r in shell['oriented_triangle_rows'])
    assert len(expected_boundary) == nf and len(set(expected_boundary)) == nf
    for face in shell['oriented_triangle_rows']:
        global_face = [shell['local_to_global_node_tags'][t - 1] for t in face['local_node_tags']]
        hit = context_faces[tuple(sorted(global_face))]
        assert oriented(global_face) == oriented(hit['oriented_shell_face'])
        removed = [r for r in hit['owners'] if r['removed_star_owner']]
        assert len(removed) == 1 and removed[0]['tetrahedron_tag'] in old_cells
    stage_rows = {}
    case_hist = Counter()
    for stage, cells, count, pair_count, internal_count in [
        ('old', old_cells, k, case['old_unordered_pairs'], case['original_internal_pairs']),
        ('candidate', candidate_cells, m, case['candidate_unordered_pairs'], case['candidate_internal_pairs'])]:
        data = report[stage]
        quality = data['quality_rows']
        assert data['cell_count'] == len(cells) == count
        assert len({tuple(sorted(c)) for c in cells.values()}) == count
        assert len(quality) == count and [r['tetrahedron_tag'] for r in quality] == sorted(cells)
        incidence = defaultdict(list)
        total_det = Fraction(0)
        poor = 0
        max_saved_native_error = 0.0
        native_by_tag = ({r['tetrahedron_tag']: r['initial_native_SICN'] for r in old_raw}
                         if stage == 'old' else dict(zip(saved['tetra_tags'], candidate_native)))
        for row in quality:
            tag = row['tetrahedron_tag']
            assert row['ordered_node_tags'] == cells[tag] and len(set(cells[tag])) == 4
            det = ratio(row['exact_determinant_mm3'])
            q2 = ratio(row['exact_SICN_squared'])
            assert det > 0 and q2 > 0
            passed = q2 >= Fraction(1, 100)
            assert row['exact_point1_gate_passed'] is passed
            # Saved rational-to-saved-native comparison only: no coordinates or
            # geometric quality formula. Retain the existing scalar comparison.
            computed = math.sqrt(float(q2))
            observed = native_by_tag[tag]
            assert type(observed) is float and math.isfinite(observed) and observed > 0
            assert math.isclose(computed, observed, rel_tol=1e-11, abs_tol=1e-14)
            max_saved_native_error = max(max_saved_native_error, abs(computed - observed))
            poor += not passed
            if stage == 'candidate':
                assert passed
            total_det += det
            for pattern in FACES:
                face = [cells[tag][i] for i in pattern]
                incidence[tuple(sorted(face))].append(face)
        boundary, internals = [], 0
        for faces in incidence.values():
            assert len(faces) in [1, 2]
            if len(faces) == 1:
                boundary.append(oriented(faces[0]))
            else:
                assert oriented(faces[0]) == oriented(list(reversed(faces[1])))
                internals += 1
        assert sorted(boundary) == expected_boundary == [tuple(x) for x in data['oriented_boundary']]
        assert internals == internal_count == data['internal_face_pairs'] == (4 * count - nf) // 2
        assert data['all_exact_positive'] is True
        assert total_det / 6 == ratio(data['exact_signed_volume_mm3']) == ratio(case['exact_volume_mm3']) == ratio(shell['exact_enclosed_volume_mm3'])
        pairs = report['pair_results'][stage]
        assert len(pairs) == pair_count
        independent_counts, vertex_counts = Counter(), Counter()
        for row, expected_tags in zip(pairs, combinations(sorted(cells), 2)):
            assert set(row) == PAIR_KEYS and row['tetrahedron_tags'] == list(expected_tags)
            shared = sorted(set(cells[expected_tags[0]]) & set(cells[expected_tags[1]]))
            assert 0 <= len(shared) <= 3 and row['shared_node_tags'] == shared
            assert row['expected_simplex_dimension'] == len(shared) - 1
            assert row['plane_triples_enumerated'] == 56
            assert type(row['independent_plane_triples']) is int and 0 <= row['independent_plane_triples'] <= 56
            assert row['intersection_vertices'] == len(shared)
            assert row['illegal_intersection_vertices'] == 0 and row['all_illegal_rational_witnesses'] == []
            assert row['intersection_equals_tagged_shared_simplex'] is True
            case_hist[stage + '/shared' + str(len(shared))] += 1
            independent_counts[row['independent_plane_triples']] += 1
            vertex_counts[row['intersection_vertices']] += 1
        stage_rows[stage] = dict(cells=count, pairs=len(pairs), triples=56 * len(pairs), positive_saved_rationals=True,
            saved_squared_quality_poor=poor, internal_opposite_pairs=internals, shell_faces=len(boundary),
            exact_volume=data['exact_signed_volume_mm3'], ordered_cell_rows_sha256=digest(encoded(quality)),
            maximum_saved_rational_to_saved_native_SICN_error=max_saved_native_error,
            full_pair_rows_sha256=digest(encoded(pairs)), independent_plane_triples_observed_histogram=dict(sorted(independent_counts.items())),
            intersection_vertex_observed_histogram=dict(sorted(vertex_counts.items())))
        totals[stage + '_cells'] += count
        totals[stage + '_pairs'] += len(pairs)
        totals[stage + '_poor'] += poor
    native = native_cases[apex]
    assert native['strict_SICN_gate_pass'] is native['later_head_storage_compatible'] is True and native['next_stage'] == 'domain'
    assert (native['after']['nodes'], native['after']['tetrahedra'], native['after']['interiors']) == (n, m, interior_count)
    assert native['after']['exact_squared_quality_poor'] == 0 and native['after']['exact_positive_volume_equals_source'] is True
    assert native['after']['native_SICN'] == case['native_SICN'] == worker['saved_reopen']['quality']['SICN']
    assert native['complete8_output_inventory']['arrays.json']['sha256'] == case['records']['arrays']['sha256']
    for role in ['worker', 'arrays', 'receipt', 'actual', 'root_closed']:
        record_id = case['records'][role]
        read(record_id['path'], record_id['sha256'])
        assert len(RAW[record_id['path']]) == record_id['bytes']
    assert report['source_candidate_report_sha256'] == case['records']['worker']['sha256']
    assert report['source_candidate_arrays_sha256'] == case['records']['arrays']['sha256']
    assert report['source_candidate_independent_peer_sha256'] == all_actual_pins[BASE + 'head-star-current204-Netgen-result-peer-001/review.json']
    assert report['old']['exact_signed_volume_mm3'] == report['candidate']['exact_signed_volume_mm3']
    aggregate_hist.update(case_hist)
    cases.append(dict(apex=apex, actual=actual_item, root_closed=dict(path=entry['closed_path'], sha256=entry['closed_sha256']),
        root_launch=dict(path=launch_name, sha256=closed['root_launch_sha256']),
        sole_output=dict(path=report_name, sha256=BEFORE[report_name], bytes=len(RAW[report_name])),
        samecase_source_record_sha256=case['source_record_sha256'], original_global_local_inverse_exact=True,
        original_and_fixed_shell_coordinate_words_and_true_classes_match=True, complete_incidence_and_oriented_shell_match=True,
        old=stage_rows['old'], candidate=stage_rows['candidate'], shared_tag_pair_histogram=dict(sorted(case_hist.items())),
        all_pair_metadata_and_shared_simplex_verdicts_clear=True, all39_current_actual_pins_and_prior_native_associations_match=True,
        lifecycle=dict(returncode=0, natural_no_stop_or_error=True, root_wait_reaped_observed_query_leader_absent=True,
            no_fallback_kill=True, universal_descendant_absence_claimed=False, native_or_head_execution=False,
            root_wall_seconds=closed['wall_seconds']), qualification=QUAL))

assert totals['old_cells'] == 2078 and totals['candidate_cells'] == 2972
assert totals['old_pairs'] == 48243 and totals['candidate_pairs'] == 99674
assert totals['old_poor'] == 75 and totals['candidate_poor'] == 0
assert totals['old_pairs'] + totals['candidate_pairs'] == index['total_pairs'] == 147917
assert 56 * index['total_pairs'] == index['total_plane_triples'] == 8283352
after = {}
for name, old in BEFORE.items():
    path = ROOT / name
    assert path.is_file() and not path.is_symlink()
    after[name] = digest(path.read_bytes())
    assert after[name] == old
result = dict(schema='962-current204-fixed47-independent-saved-domain-associations/v1',
    status='CLEAR_ALL47_COMPLETE_SAVED_ASSOCIATIONS_NO_GEOMETRY_REPLAY',
    root_master_sha256=PINS[MASTER], actual_index_sha256=PINS[INDEX], source_sha256=PINS[SOURCE],
    current_source_peer_sha256=PINS[BASE + PREFIX + 'source-peer-002/review.json'],
    selected_python_sha256_root_attributed_no_runtime_body_read=PY_SHA,
    input_sha256_before=BEFORE, input_sha256_after=after, all_consumed_saved_inputs_unchanged=True,
    all315_unique_actual_pins_current=True, case_count=47,
    complete47_report_bytes=sum(x['sole_output']['bytes'] for x in cases), case_ledger=cases,
    totals=dict(totals), complete_unordered_pairs=147917, complete_plane_triples=8283352,
    shared_tag_pair_histogram=dict(sorted(aggregate_hist.items())),
    checked_scope='Saved bytes/control/tag/coordinate-word/classification/combinatorial incidence/rational-field bookkeeping and complete pair-verdict metadata only.',
    not_replayed=['exact coordinate determinant/SICN formula', 'face halfspace predicates', 'plane rank/Cramer intersections',
        'shared-simplex geometry predicates', 'producer/helper modules', 'native/optimizer/head', 'runtime/MSH bodies'],
    geometry_kernel_and_compact_chain_source_root_execution_attributed=True,
    reviewer_role='Authored earlier batch selector and head-application donor, and prior local-domain caller lineage. Did not author finite47 adapter/root queries. This is independent saved-association checking, not independent derivation/replay of retained geometry mathematics.',
    subset_preservation_and_originaltag_parameter_checks_still_required_before_head_application=True,
    head_mesh_unchanged_and_whole_head_gate_not_accepted=True,
    native_or_head_application_authorized=False, engineering_accepted=False, physics_qualified=False,
    material_qualified=False, process_calibrated=False, manufacturing_authorized=False,
    checker_wall_seconds=time.monotonic() - start)
target = OUT / 'independent-saved-check.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps(dict(status=result['status'], cases=47, unique_saved_inputs=len(BEFORE), unique_actual_pins=315,
    totals=dict(totals), pairs=147917, triples=8283352, saved_report_bytes=result['complete47_report_bytes'],
    saved_check_sha256=digest(target.read_bytes()), checker_wall_seconds=result['checker_wall_seconds'])))
