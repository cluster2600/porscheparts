"""One saved-association check; no producer, decoder, numerical oracle or native calls."""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
import re
import struct

ROOT = Path(__file__).resolve().parents[3]
E = 'work/962-engineering/'
HERE = Path(__file__).resolve().parent
ACT = E + 'cp1-oneway-thermoelastic-assessment-execution-prep-002/actual-contract.json'
IDX = E + 'cp1-oneway-thermoelastic-assessment-execution-prep-002/index.json'
RESULT = E + 'cp1-oneway-thermoelastic-assessment-002/assessment.json'
RUN = E + 'cp1-oneway-thermoelastic-assessment-root-execution-002/'
AUDIT = E + 'cp1-oneway-thermoelastic-transfer-native002-nodal-audit-001/complete-saved-audit.json'
NROOT = E + 'cp1-oneway-thermoelastic-transfer-root-execution-002/closed-result.json'
EXPECTED = {
    ACT: '5d76ec0fade67465e151292f5c7b9d3b5a954245c485af84e04967d68e86e78c',
    IDX: '6d60ff61c2eca596483a25141e7ac7fbff0f29944d802b82c986cc47fda15a20',
    RESULT: '14cf3817c819e9dde6968647d0e98b3dc0567bdebbbea5d2ca5dcc7c779c472a',
    RUN + 'closed-result.json': '46796521d8dbb9944771226f24723ec7c4e1c6ea9cdf6dc7dd8979d313dde050',
    RUN + 'launch.json': 'a5adf4a155e1cd7b93b9d3a6cb5ed764862191b7bc200aff485a65dd4da85d8a',
    RUN + 'child-peer-acceptance.json': '066a68754cd37bfd61d0badcc21377eef664f00cce073be8f294a10b7634c277',
    RUN + 'stdout.log': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    RUN + 'stderr.log': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    AUDIT: 'c6a70c0eb6727549e30ab81dd047dc825540dd454546514944fd3c9461abf4ee',
    NROOT: 'd898fca841c4e3c59f6320cce1a40b003137afa9f2f815d46e11d870594165dd',
}


def need(value, message):
    if not value:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def raw(name):
    path = ROOT / name
    need(not Path(name).is_absolute() and '..' not in Path(name).parts, 'relative pin')
    need(path.is_file() and not path.is_symlink() and path.resolve() == path, 'regular canonical pin: ' + name)
    return path.read_bytes()


def load(name):
    return json.loads(raw(name))


def words(xyz):
    need(len(xyz) == 3 and all(type(x) is float and math.isfinite(x) for x in xyz), 'finite float coordinate')
    return struct.pack('<ddd', *xyz).hex()


def pin_records(names):
    return {n: dict(sha256=digest(raw(n)), bytes=(ROOT / n).stat().st_size) for n in sorted(names)}


actual, index, result, closed, launch, audit, native_root = map(load, [ACT, IDX, RESULT, RUN + 'closed-result.json', RUN + 'launch.json', AUDIT, NROOT])
pins = actual['input_sha256']
need(len(pins) == actual['input_count'] == 1458, '1458 actual pins')
need(result['input_sha256'] == pins == closed['all1458_input_hashes_before'] == closed['all1458_input_hashes_after'], 'all1458 exact result/root maps')
need(closed['external_records_before'] == closed['external_records_after'], 'external records unchanged')
small = {n: r['sha256'] for n, r in index['fresh_small_body_checks'].items()}
need(len(small) == 137 and all(pins[n] == v for n, v in small.items()), '137 selected small bodies')
bound = {**small, **EXPECTED, **closed['external_records_before']}
before = pin_records(bound)
need(all(before[n]['sha256'] == h for n, h in bound.items()), 'fresh selected input identities')
for n, record in index['fresh_small_body_checks'].items():
    need(before[n] == record, 'selected small exact size/hash')
need(closed['actual_sha256'] == result['actual_sha256'] == digest(raw(ACT)), 'actual joined')
need(closed['launch_sha256'] == digest(raw(RUN + 'launch.json')), 'launch joined')
need(launch['actual_sha256'] == closed['actual_sha256'] and launch['index_sha256'] == digest(raw(IDX)), 'launch actual/index')
need(closed['child_peer_sha256'] == launch['peer_sha256'] and closed['child_bindings_sha256'] == launch['bindings_sha256'], 'child peer joins')
need(launch['argv'][-3:] == [str(ROOT / actual['source']['path']), str(ROOT / ACT), digest(raw(ACT))], 'exact source/actual argv')
need(launch['argv'][1:3] == ['-I', '-B'], 'isolated selected argv')
need(launch['assessor_pid'] == launch['assessor_pgid'] == closed['assessor_pid'] and launch['new_owned_session'] is True, 'owned lifecycle association')
need(closed['returncode'] == 0 and closed['stop_reason'] is None and closed['controller_error'] is None, 'natural RC0')
need(all(closed[k] is False for k in ('SIGTERM_requested', 'fallback_SIGKILL', 'native_solver_replayed')), 'no stop or native replay')
need(closed['wait_reaped'] is True and closed['owned_assessor_observed_absent'] is True, 'root recorded wait/absence')
need(0 < closed['process_wall_seconds'] < 300 and len(closed['RSS_samples']) == 559, 'bounded observed process')
need(closed['max_sampled_owned_leader_RSS_bytes'] == max(r['RSS_bytes'] for r in closed['RSS_samples']) < 2**31, 'sampled leader RSS')
need(closed['stream_bytes'] == 0 and raw(RUN + 'stdout.log') == raw(RUN + 'stderr.log') == b'', 'empty root streams')
need(closed['output_files'] == {'assessment.json': before[RESULT]} and closed['output_count'] == 1 and closed['output_bytes'] == before[RESULT]['bytes'], 'single result closure')
out = ROOT / actual['output_directory']
need(not out.is_symlink() and {p.name for p in out.iterdir()} == {'assessment.json'}, 'exact sole result file')
selection = load(actual['runtime_selection'])
need(len(selection['files']) == 258 and selection['files'] == actual['decoder_runtime_metadata']['files'] == closed['selected258_runtime_before'] == closed['selected258_runtime_after'], '258 runtime identities metadata join')
need(closed['python_before'] == closed['python_after'] == selection['Python_sha256'] == '1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60', 'selected Python metadata')
need(closed['all1458_before_after_unchanged'] is True and closed['selected258_runtime_before_after_unchanged'] is True, 'root unchanged flags')
inventory = actual['native_output_inventory']
receipt = load(actual['native_directory'] + '/native-execution.json')
need(len(inventory) == 990 and inventory == native_root['complete_recursive_output_inventory'], 'full990 native inventory metadata')
need(sum(r['bytes'] for r in inventory.values()) == 359397778, 'native inventory byte sum')
need(receipt['complete_artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items() if n != 'native-execution.json'}, '989 complete receipt map')
need(receipt['artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items() if n != 'native-execution.json' and Path(n).name == n}, '978 flat receipt map')
need(len(receipt['complete_artifact_sha256']) == 989 and len(receipt['artifact_sha256']) == 978 and receipt['passed'] is False and receipt['independent_assessment_performed'] is False, 'native original flags unchanged')
need(result['native_original_receipt_passed_field'] is False and result['native_receipt_is_not_assessment_authority'] is True, 'separate assessment')
need(result['source_physics_contract_sha256'] == receipt['physics_contract_sha256'] == actual['source_physics_contract']['sha256'], 'physics source binding')
policy = load(E + 'cp1-oneway-thermoelastic-assessor-prep-003/POLICY.json')
need(result['policy_sha256'] == actual['POLICY_sha256'] == digest(raw(E + 'cp1-oneway-thermoelastic-assessor-prep-003/POLICY.json')), 'unchanged policy binding')
need(result['passed'] is True and closed['observed_source_assessment_passed'] is True and result['source_and_runtime_inputs_unchanged'] is True, 'source reported pass')
need(result['decoder_runtime_selection_sha256'] == digest(raw(actual['runtime_selection'])) and result['decoder_selected_file_count'] == 258, 'decoder selection')
for k in ('PETSc_order_assumed', 'work_equals_2U_used', 'material_process_head_or_manufacturing_qualified', 'decoder_complete_ABI_or_OS_closure_claimed', 'mechanical_space_time_convergence', 'head_execution_authorized', 'engineering_accepted', 'physics_qualified', 'material_qualified', 'process_calibrated', 'manufacturing_authorized'):
    need(result[k] is False, 'false qualification or unsupported shortcut: ' + k)
limits = policy['absolute_SI_limits']
need(set(result['maximum_SI_errors']) == set(result['scalar_comparisons']) == set(limits) - {'QP_coordinate_m'}, 'six SI maximum/count units')
for unit, error in result['maximum_SI_errors'].items():
    need(type(error) is float and math.isfinite(error) and 0 <= error <= limits[unit], 'reported maximum within unchanged SI gate')

# Structural comparison counts from the reviewed loop cardinalities, not tensor/FEM evaluation.
counts = Counter(); qsum = Counter(); phase_counts = Counter()
for step in range(161):
    n, q, subset_nodes = (225, 1024, 225) if step < 80 else (425, 2048, 450)
    for phase in ('begin', 'end'):
        phase_counts[phase] += 1; qsum[phase] += q
        counts.update(temperature_K=n, displacement_m=6, stress_Pa=6*q, strain=24*q, force_N=3*subset_nodes + 3*n - 6)
        if phase == 'begin' and step:
            previous_n = 225 if step <= 80 else 425
            counts.update(temperature_K=previous_n, displacement_m=3*previous_n, stress_Pa=6*q, strain=24*q)
        if phase == 'begin' and step == 80:
            counts['displacement_m'] += 600
        if step >= 80:
            counts['temperature_K'] += 225
        if phase == 'end':
            counts.update(temperature_K=n + (225 if step >= 80 else 0), displacement_m=3*n, stress_Pa=6*q, strain=24*q, force_N=6*n + 6, moment_Nm=6)
need(dict(counts) == result['scalar_comparisons'] and dict(qsum) == result['quadrature_rows'] == {'begin': 247808, 'end': 247808}, 'all structural comparison counts')
transfer = load(actual['transfer_manifest'])
geometry = {r['source_node_id']: r['coordinates_m'] for r in transfer['node_rows']}
native_nodes = result['native_nodes']
need(len(native_nodes) == len(geometry) == 425 and [r['id'] for r in native_nodes] == sorted(geometry), '425 saved native IDs')
coords = audit['source_node_map']['ID_to_coordinate_binary64_LE_hex']
need(all(words(r['coordinates_m']) == words(geometry[r['id']]) == coords[str(r['id'])] for r in native_nodes), 'all425 saved coordinate words join source/audit')
cells = result['native_ordered_cells']
need(len(cells) == 256 and [r['id'] for r in cells] == list(range(256)), '256 complete ordered saved cell IDs')
need(all(len(r['nodes']) == len(set(r['nodes'])) == 8 and all(type(t) is int and t in geometry for t in r['nodes']) for r in cells), 'saved HEX8 connectivity shape/IDs')
qpmap = result['observed_QP_ID_coordinate_map']
need(len(qpmap) == 2048 and [(r['elem_id'], r['qp_id']) for r in qpmap] == [(t, q) for t in range(256) for q in range(8)], 'complete saved2048 QP ID map')
for row in qpmap:
    words(row['coordinates_m'])
need([r['filename'] for r in result['exodus_family']] == actual['exodus_family'], 'two fixed family names')
frame_steps = []
for i, family in enumerate(result['exodus_family']):
    need(family['sha256'] == inventory[family['filename']]['sha256'] and family['magic'] == '43444602', 'saved CDF2 family identity/magic')
    need(family['node_map'] == list(range(1, 426)) and sorted(family['element_map']) == list(range(1, 257)), 'saved external ID map coverage')
    need(family['block_ids'] == ([1, 2] if i == 0 else [2, 3]) and family['block_status'] == [1, 1], 'saved family block metadata')
    steps = [round(t*400) for t in family['times']]
    need(steps == list(range(80)) if i == 0 else steps == list(range(80, 161)), 'saved family time split')
    need(all(type(t) is float and math.isfinite(t) and abs(t-s/400) <= 5e-13 for t, s in zip(family['times'], steps)), 'saved frame step association')
    frame_steps.extend(steps)
need(frame_steps == list(range(161)), 'complete161 saved frame metadata')

shared = audit['source_node_map']['shared25_IDs']
old = set(audit['source_node_map']['old225_IDs']); born = set(audit['source_node_map']['born225_IDs'])
need(len(old) == len(born) == 225 and sorted(old & born) == shared and old | born == set(geometry), 'source partition joins')
need(len(result['phase_summaries']) == 322 and len(audit['files']) == 644, 'complete phases/audit storage')
storage_checks = []; csv_expected = {}; duplicate_count = 0
for position, summary in enumerate(result['phase_summaries']):
    step, phase = divmod(position, 2); phase = ('begin', 'end')[phase]
    need(summary['step'] == step and summary['phase'] == phase, 'ordered step/phase')
    need((summary['active_nodes'], summary['active_cells'], summary['quadrature_rows']) == ((225, 128, 1024) if step < 80 else (425, 256, 2048)), 'phase full cardinality')
    energy = summary['elastic_strain_energy_J_diagnostic']
    need(type(energy) is float and math.isfinite(energy) and energy >= 0, 'finite nonnegative source energy diagnostic')
    for kind, key, filename, active, expected_dups, fields in [
        ('nodal', 'native_nodal_storage', f'thermoelastic_{phase}_{step:04d}.csv', old if step < 80 else set(geometry), shared if step >= 80 else [], ['id','x','y','z','disp_x','disp_y','disp_z','temperature'] + (['rx','ry','rz'] if phase == 'end' else [])),
        ('reference', 'born_reference_storage', f'thermoelastic_reference_{phase}_{step:04d}.csv', set() if step < 80 else born, [], ['id','x','y','z','born_reference_temperature']),
    ]:
        storage = summary[key]; observed = audit['files'][filename]
        need(storage['filename'] == filename and storage['comparison_field_order'] == fields, 'exact storage family/field order')
        need(storage['raw_csv_sha256'] == observed['sha256'] == inventory[filename]['sha256'], 'storage/audit/inventory SHA association')
        need(observed['kind'] == kind and observed['phase'] == phase and observed['step'] == step and observed['bytes'] == inventory[filename]['bytes'], 'audit role/size association')
        need(storage['raw_row_count'] == observed['raw_rows'] == len(active)+len(expected_dups) and storage['unique_source_ID_count'] == observed['unique_IDs'] == len(active), 'raw and unique cardinality')
        need(storage['expected_shared_doublet_IDs'] == observed['duplicate_IDs'] == list(expected_dups), 'complete expected doublet set')
        need(set(observed['raw_ordered_source_IDs']) == active and Counter(observed['raw_ordered_source_IDs']) == Counter({t: 2 if t in expected_dups else 1 for t in active}), 'saved audit allID multiplicities')
        need(storage['raw_rows_rewritten_or_averaged'] is False, 'raw storage not rewritten')
        groups = observed['duplicate_groups']; reported = storage['verified_doublets']
        need(len(groups) == len(reported) == len(expected_dups), 'complete doublet records')
        for g, s in zip(groups, reported):
            need(g['source_ID'] == s['source_node_id'] and g['original_CSV_lines'] == s['csv_line_numbers_1_based'], 'audit/result doublet ID/line association')
            need(g['all_present_header_tokens_lexically_identical'] is True and len(set(g['header_plus_row_tokens_SHA256'])) == 1 and re.fullmatch('[0-9a-f]{64}', s['complete_field_token_sha256']), 'two declared token encodings')
        if active:
            need(storage['all_duplicate_complete_field_tokens_identical'] is True and storage['all_other_multiplicities_one'] is True, 'strict reader storage flags')
        duplicate_count += len(reported)
        name = actual['native_directory'] + '/' + filename
        csv_expected[name] = observed['sha256']
        storage_checks.append(dict(filename=filename, sha256=observed['sha256'], bytes=observed['bytes'], phase=phase, step=step, raw_rows=observed['raw_rows'], unique_IDs=observed['unique_IDs'], verified_doublets=reported))
need(duplicate_count == 4050 and len(csv_expected) == 644, 'complete4050 shared groups/644 files')

# Independently bridge both previously declared token encodings, preserving every raw byte.
csv_before = pin_records(csv_expected)
need(all(csv_before[n]['sha256'] == h for n, h in csv_expected.items()), 'all644 lexical input bytes')
for record in storage_checks:
    filename = record['filename']; observed = audit['files'][filename]
    payload = raw(actual['native_directory'] + '/' + filename)
    parsed = list(csv.reader(io.StringIO(payload.decode('utf-8'), newline='')))
    header, rows = parsed[0], parsed[1:]
    need(header == observed['header'] and len(header) == len(set(header)) and all(len(r) == len(header) for r in rows), 'complete lexical header/row shape')
    ids = [int(row[header.index('id')]) for row in rows]
    need(ids == observed['raw_ordered_source_IDs'] and [row[header.index('id')] for row in rows] == observed['raw_ordered_ID_tokens'], 'full ordered originalID token association')
    coord_data = bytearray()
    for tag, row in zip(ids, rows):
        xyz = [float(row[header.index(k)]) for k in 'xyz']
        need(words(xyz) == coords[str(tag)], 'rawCSV/source coordinate words')
        coord_data.extend(struct.pack('<Q', tag)); coord_data.extend(bytes.fromhex(words(xyz)))
    need(digest(coord_data) == observed['ordered_source_ID_u64_plus_coordinate_binary64_LE_sha256'], 'complete orderedID/coordinate digest')
    positions = defaultdict(list)
    for line, (tag, row) in enumerate(zip(ids, rows), 2):
        positions[tag].append((line, row))
    groups = {g['source_ID']: g for g in observed['duplicate_groups']}
    fields = ['id','x','y','z','born_reference_temperature'] if observed['kind'] == 'reference' else ['id','x','y','z','disp_x','disp_y','disp_z','temperature'] + (['rx','ry','rz'] if record['phase'] == 'end' else [])
    for s in record['verified_doublets']:
        tag = s['source_node_id']; pair = positions[tag]; g = groups[tag]
        need(len(pair) == 2 and pair[0][1] == pair[1][1] and [p[0] for p in pair] == s['csv_line_numbers_1_based'], 'complete identical pair and logical row ordinals')
        need([digest(json.dumps([header, row], separators=(',', ':'), ensure_ascii=False).encode()) for _, row in pair] == g['header_plus_row_tokens_SHA256'], 'prior audit token digests reproduced')
        reordered = [pair[0][1][header.index(k)] for k in fields]
        need(digest(json.dumps(reordered, separators=(',', ':')).encode()) == s['complete_field_token_sha256'], 'assessor token digest reproduced independently')
csv_after = pin_records(csv_expected)
after = pin_records(bound)
need(csv_before == csv_after and before == after, 'all read bytes unchanged')
report = dict(
    schema='962-cp1-oneway-thermoelastic-assessment002-independent-saved-associations/v1',
    status='PASS_SAVED_ASSOCIATIONS_ONLY', direct_records_before=before, direct_records_after=after,
    all1458_actual_identity_values=pins, all258_selected_decoder_identity_values=selection['files'],
    full990_native_inventory=inventory, native989_complete_and978_flat_maps_joined=True,
    runtime_and_unselected_native_body_freshness_attributed_to_root=True,
    all644_lexical_CSV_records_before=csv_before, all644_lexical_CSV_records_after=csv_after,
    complete_phase_storage_associations=storage_checks,
    phases=322, each_phase_quadrature_total=dict(qsum), saved_native_nodes=425, saved_ordered_cells=256, saved_QP_ID_coordinate_rows=2048,
    independently_derived_structural_comparison_counts=dict(counts), reported_maximum_SI_errors=result['maximum_SI_errors'], unchanged_absolute_SI_limits=limits,
    both_token_encodings_independently_reproduced_groups=4050,
    exact_raw_source_files_preserved=True, line_numbers_scope='Logical parsed CSV record ordinals starting at2, as in the unchanged reader; raw byte SHA retains file authority.',
    root_lifecycle_association=dict(returncode=closed['returncode'], process_wall_seconds=closed['process_wall_seconds'], wait_reaped=closed['wait_reaped'], observed_owned_assessor_absent=closed['owned_assessor_observed_absent'], RSS_samples=len(closed['RSS_samples']), sampled_leader_RSS_max_bytes=closed['max_sampled_owned_leader_RSS_bytes']),
    numerical_maxima_comparisons_and_FEM_Exodus_geometry_acceptance_attributed_to_unchanged_assessor_and_root=True,
    original_native_passed_field=receipt['passed'], original_native_assessment_field=receipt['independent_assessment_performed'],
    producer_helper_assessor_guard_import_or_execution=False, numerical_FEM_constitutive_quadrature_or_Exodus_geometry_re_evaluation=False,
    native_execution=False, engineering_accepted=False, physics_qualified=False, material_qualified=False, process_calibrated=False, manufacturing_authorized=False,
)
(HERE / 'independent-saved-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(status=report['status'], phases=322, lexical_CSV_files=644, doublet_groups=4050, input_identity_count=1458, decoder_identity_count=258)))
