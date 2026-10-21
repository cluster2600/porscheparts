"""Independent fixed saved-storage association inspection; no producer import."""
import ast
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import time

ROOT = Path('project-role://engineering-checkout')
BASE = ROOT / 'work/962-engineering'
NATIVE = BASE / 'cp1-oneway-cooling-release-linear-001'
RUN = BASE / 'cp1-oneway-cooling-release-linear-native-storage-root-execution-001'
AUDIT = BASE / 'cp1-oneway-cooling-release-linear-native-storage-audit-001'
HERE = Path(__file__).resolve().parent
START = time.monotonic()


def require(ok, label):
    if not ok:
        raise AssertionError(label)
    if time.monotonic() - START > 58:
        raise TimeoutError('Own finite saved-byte inspection exceeded 58 seconds')


def descriptor(path):
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            'Expected canonical regular file: ' + str(path))
    stat0 = path.stat()
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    stat1 = path.stat()
    require((stat0.st_size, stat0.st_ino, stat0.st_mtime_ns) ==
            (stat1.st_size, stat1.st_ino, stat1.st_mtime_ns), 'File changed during opaque hash')
    return dict(path=str(path.relative_to(ROOT)), sha256=value.hexdigest(), bytes=stat1.st_size)


def load(path):
    return json.loads(path.read_bytes())


def compact(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


closed_path = RUN / 'closed-result.json'
result_path = AUDIT / 'complete-saved-audit.json'
require(descriptor(closed_path)['sha256'] ==
        '06c1221546d8b17f6894c66cd7fe9cedb5d0b0c34eea3e70f6ed724730a9bce2', 'Stopped root identity')
require(descriptor(result_path)['sha256'] ==
        '18c78ad66d9f21413c2bbc35813f175e2b011a7edc8973ac0228287f2d4cc6e9', 'Saved audit identity')
closed = load(closed_path)
authorization = load(RUN / 'authorization.json')
index = load(AUDIT / 'audit-index.json')
saved = load(result_path)
native_closed = load(BASE / 'cp1-oneway-cooling-release-linear-native-root-execution-001/closed-result.json')
receipt = load(NATIVE / 'native-execution.json')
actual = load(NATIVE / 'actual-contract.json')
accepted_manifest_path = BASE / 'cp1-oneway-cooling-release-inputs-001/transfer-manifest.json'
transfer = load(accepted_manifest_path)

require(closed['schema'] == '962-linear-cooling-saved-storage-root-once-closed/v1'
        and closed['returncode'] == 0 and closed['stop_reason'] is None
        and closed['signals'] == [] and closed['error'] is None
        and closed['waited_reaped'] is True and closed['owned_group_absent'] is True,
        'Root stopped lifecycle metadata')
require(closed['inputs_before'] == closed['inputs_after'] == authorization['input_records_before']
        and len(closed['inputs_before']) == 37, 'Complete root 35 plus child2 closure')
require(authorization['ordinary_seconds'] == 60 and authorization['TERM_grace_seconds'] == 8
        and authorization['sampled_RSS_stop_bytes'] == 2147483648
        and authorization['sampled_output_stop_bytes'] == 33554432
        and authorization['new_owned_session'] is True
        and authorization['verified_owned_KILL_wait'] is True
        and authorization['hard_OS_quota'] is False and authorization['automatic_retry'] is False
        and authorization['native_or_assessor_execution_authorized'] is False,
        'Exact ordinary saved-storage controls')
require(authorization['argv'][1:3] == ['-I', '-B']
        and authorization['argv'][3] == str(AUDIT / 'check_saved.py')
        and len(authorization['argv']) == 4, 'Selected saved-only source invocation')
require(closed['outer_python_before'] == closed['outer_python_after'] == authorization['outer_python'],
        'Root-attributed selected interpreter before/after')
require(closed['outer_python_before']['sha256'] ==
        '1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60',
        'Root-attributed selected1699 interpreter')
for field in ('source', 'index', 'child_peer', 'child_bindings', 'result', 'authorization', 'stdout', 'stderr'):
    row = closed[field]
    require(descriptor(ROOT / row['path']) == row, 'Current root descriptor: ' + field)
require(closed['source'] == index['source'] == authorization['source']
        and closed['index'] == authorization['index']
        and closed['child_peer'] == authorization['peer']
        and closed['child_bindings'] == authorization['peer_bindings'], 'Source/index/child joins')
require(closed['saved_lexical_storage_passed'] is True
        and closed['native_reexecution'] is False
        and closed['independent_3D_assessment_performed'] is False, 'Root scope remains lexical only')

source_tree = ast.parse((AUDIT / 'check_saved.py').read_text())
assignments = {n.targets[0].id: n.value for n in source_tree.body
               if isinstance(n, ast.Assign) and len(n.targets) == 1
               and isinstance(n.targets[0], ast.Name)}
pin_ast = assignments['PIN']
require(isinstance(pin_ast, ast.Dict), 'Literal fixed PIN dictionary syntax')
prefixes = dict(RUN=BASE / 'cp1-oneway-cooling-release-linear-native-root-execution-001',
                OUT=NATIVE, E=BASE, PREP=BASE / 'cp1-oneway-cooling-release-linear-prep-001')
source_pins = {}
for expression, expected in zip(pin_ast.keys, pin_ast.values):
    require(isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div)
            and isinstance(expression.left, ast.Name) and expression.left.id in prefixes
            and isinstance(expression.right, ast.Constant) and type(expression.right.value) is str
            and isinstance(expected, ast.Constant) and type(expected.value) is str,
            'Restricted named path/literal hash PIN syntax')
    path = prefixes[expression.left.id] / expression.right.value
    source_pins[str(path.relative_to(ROOT))] = expected.value
require(len(source_pins) == 17 and source_pins == index['direct17_PIN_sha256'], 'All17 source PIN literals')
require(assignments['EXPECTED_CAPTURE_OUTPUT_COUNT'].value == 1122
        and assignments['EXPECTED_CAPTURE_OUTPUT_BYTES'].value == 423178297, 'Literal finite inventory counters')

selected = dict(closed['inputs_before'])
for path in [closed_path, result_path, RUN / 'authorization.json', RUN / 'stdout.log', RUN / 'stderr.log',
             RUN / 'own-review.json', accepted_manifest_path]:
    selected[str(path.relative_to(ROOT))] = descriptor(path)
current_before = {name: descriptor(ROOT / name) for name in selected}
require(current_before == selected, 'All selected current small/control metadata')
require(set(index['direct17_PIN_sha256']) <= set(selected), 'All17 source pins selected')
for name, expected in source_pins.items():
    require(current_before[name]['sha256'] == expected, 'Fresh direct source PIN: ' + name)
require(saved['direct_bindings'] == {name: {k: current_before[name][k] for k in ('sha256', 'bytes')}
                                  for name in source_pins}, 'Saved direct17 binding records')

inventory = native_closed['outputs']
require(inventory == index['complete_native_inventory'] == authorization['all1122_native_inventory_before_opaque']
        == closed['all1122_native_inventory_before_opaque'] == closed['all1122_native_inventory_after_opaque'],
        'Full1122 root/native/index before/after inventory equality')
require(len(inventory) == 1122 and sum(row['bytes'] for row in inventory.values()) == 423178297,
        'Exact1122/423178297 capture metadata')
for name, row in inventory.items():
    require(set(row) == {'path', 'sha256', 'bytes'}
            and row['path'] == str((NATIVE / name).relative_to(ROOT))
            and not Path(name).is_absolute() and '..' not in Path(name).parts,
            'Exact relative full native descriptor')
entries = list(NATIVE.rglob('*'))
require(not any(p.is_symlink() for p in entries)
        and {str(p.relative_to(NATIVE)) for p in entries if p.is_file()} == set(inventory),
        'Complete native regular-file membership')
opaque_before = {name: descriptor(NATIVE / name) for name in inventory}
require(opaque_before == inventory, 'All1122 current bodies opaque byte identities')
require(receipt['complete_artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items()
                                             if n != 'native-execution.json'}, 'Complete recursive receipt map')
require(receipt['artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items()
                                    if n != 'native-execution.json' and '/' not in n}, 'Separate flat receipt map')
require(len(receipt['input_sha256']) == 19 and all(inventory[n]['sha256'] == h
        for n, h in receipt['input_sha256'].items()), 'Exact19 materialized input identities')
require(receipt['native_execution_completed'] is True and receipt['passed'] is False
        and receipt['independent_assessment_performed'] is False and receipt['automatic_retry'] is False
        and receipt['returncode'] == 0 and receipt['process_reaped'] is True, 'Original unassessed native receipt')
require(receipt['actual_contract_sha256'] == inventory['actual-contract.json']['sha256']
        and actual['source']['sha256'] == source_pins['work/962-engineering/cp1-oneway-cooling-release-linear-prep-001/run_mac.py']
        and actual['physics_contract']['sha256'] == inventory['frozen-contract.json']['sha256'],
        'Native actual/current physics/source join')
require(descriptor(accepted_manifest_path)['sha256'] ==
        inventory['transfer-manifest.json']['sha256'] == receipt['transfer_manifest_sha256'] ==
        'c774e62c67e16c29dc024b8cc8e6641570e316265960e58cd7170827f8cecd06', 'Accepted manifest byte alias')

coordinates = {}
sets = dict(old=set(), born=set(), shared=set())
for node in transfer['node_rows']:
    tag = node['source_node_id']
    require(type(tag) is int and tag >= 0 and tag not in coordinates, 'Unique typed source ID')
    xyz = node['coordinates_m']
    require(len(xyz) == 3 and all(type(x) is float and math.isfinite(x) for x in xyz)
            and [x.hex() for x in xyz] == node['binary64_hex'], 'Exact finite source coordinate words')
    coordinates[tag] = struct.pack('<ddd', *xyz)
    for key, flag in [('old', 'old2'), ('born', 'born3'), ('shared', 'shared')]:
        require(type(node[flag]) is bool, 'Typed source membership flag')
        if node[flag]:
            sets[key].add(tag)
require(len(coordinates) == 425 and len(set(coordinates.values())) == 425
        and len(sets['old']) == len(sets['born']) == 225 and len(sets['shared']) == 25
        and sets['old'] | sets['born'] == set(coordinates)
        and sets['old'] & sets['born'] == sets['shared']
        and len(sets['old'] - sets['born']) == len(sets['born'] - sets['old']) == 200,
        '425/225/225/25/disjoint200 source membership')
expected_source_map = dict(nodes=425, old225_IDs=sorted(sets['old']), born225_IDs=sorted(sets['born']),
                           shared25_IDs=sorted(sets['shared']),
                           ID_to_coordinate_binary64_LE_hex={str(tag): coordinates[tag].hex() for tag in sorted(coordinates)})
require(saved['source_node_map'] == expected_source_map, 'Complete saved425 ID/coordinate map')

expected_names = {}
for step in range(183):
    for phase in ('begin', 'end'):
        expected_names[f'thermoelastic_{phase}_{step:04d}.csv'] = ('nodal', phase, step)
        expected_names[f'thermoelastic_reference_{phase}_{step:04d}.csv'] = ('reference', phase, step)
require(set(saved['files']) == set(expected_names) and len(saved['files']) == 732,
        'All732 result file records')
begin_header = ['disp_x', 'disp_y', 'disp_z', 'id', 'temperature', 'x', 'y', 'z']
end_header = ['disp_x', 'disp_y', 'disp_z', 'id', 'rx', 'ry', 'rz', 'temperature', 'x', 'y', 'z']
reference_header = ['born_reference_temperature', 'id', 'x', 'y', 'z']
totals = {kind: dict(files=0, raw_rows=0, postbirth_doublet_groups=0) for kind in ('nodal', 'reference')}
unique_nodal = 0
verified_files = {}
for filename, (kind, phase, step) in expected_names.items():
    raw = (NATIVE / filename).read_bytes()
    require(dict(path=str((NATIVE / filename).relative_to(ROOT)), sha256=digest(raw), bytes=len(raw))
            == inventory[filename], 'Raw requested CSV body identity')
    parsed = list(csv.reader(io.StringIO(raw.decode('utf-8'), newline='')))
    require(bool(parsed), 'Explicit CSV header')
    header, rows = parsed[0], parsed[1:]
    require(header == (reference_header if kind == 'reference' else
                       begin_header if phase == 'begin' else end_header), 'Exact declared lexical field order')
    positions = {}
    ids = []
    raw_ids = []
    stream = bytearray()
    active = (sets['born'] if step >= 80 else set()) if kind == 'reference' else (
        set(coordinates) if step >= 80 else sets['old'])
    for line, tokens in enumerate(rows, 2):
        require(len(tokens) == len(header) and all(t != '' for t in tokens), 'No malformed/padded CSV rows')
        values = dict(zip(header, tokens))
        token = values['id']
        require(token.isascii() and token.isdecimal(), 'Explicit lexical nonnegative source ID')
        tag = int(token)
        require(tag in active and all(math.isfinite(float(t)) for t in tokens), 'Finite active-node tokens')
        require(struct.pack('<ddd', *(float(values[a]) for a in ('x', 'y', 'z'))) == coordinates[tag],
                'Raw source ID and complete binary64 coordinate words')
        positions.setdefault(tag, []).append((line, tokens))
        ids.append(tag)
        raw_ids.append(token)
        stream.extend(struct.pack('<Q', tag) + coordinates[tag])
    require(set(positions) == active and len(set(raw_ids)) == len(positions), 'Full active IDs/no lexical alias')
    duplicate_ids = sorted(tag for tag, entries in positions.items() if len(entries) > 1)
    require(set(duplicate_ids) == (sets['shared'] if kind == 'nodal' and step >= 80 else set()),
            'Only exact shared25 postbirth nodal IDs repeat')
    require(all(len(entries) == (2 if tag in duplicate_ids else 1)
                for tag, entries in positions.items()), 'No missing/triple/unexpected multiplicity')
    histogram = {}
    lexical_histogram = {}
    for entries in positions.values():
        key = str(len(entries))
        histogram[key] = histogram.get(key, 0) + 1
    for token in set(raw_ids):
        key = str(raw_ids.count(token))
        lexical_histogram[key] = lexical_histogram.get(key, 0) + 1
    groups = []
    for tag in duplicate_ids:
        entries = positions[tag]
        require(entries[0][1] == entries[1][1], 'All present tokens equal, including reactions and signed zero')
        groups.append(dict(source_ID=tag, original_CSV_lines=[n for n, _ in entries],
                           header_plus_row_tokens_SHA256=[digest(compact([header, tokens])) for _, tokens in entries],
                           all_present_header_tokens_lexically_identical=True,
                           source_coordinate_binary64_LE_hex=coordinates[tag].hex(),
                           source_shared25_interface_member=True))
    computed = dict(path=str((NATIVE / filename).relative_to(ROOT)), sha256=digest(raw), bytes=len(raw),
                    kind=kind, phase=phase, step=step, header=header, raw_rows=len(rows), unique_IDs=len(positions),
                    multiplicity_counts=histogram, distinct_original_ID_tokens=len(set(raw_ids)),
                    raw_ordered_ID_tokens=raw_ids, lexical_ID_multiplicity_counts=lexical_histogram,
                    raw_ordered_source_IDs=ids,
                    ordered_source_ID_u64_plus_coordinate_binary64_LE_sha256=digest(stream),
                    all_rows_source_ID_coordinate_words_exact=True, duplicate_IDs=duplicate_ids,
                    duplicate_groups=groups, all_duplicate_groups_full_row_lexically_identical=True)
    require(list(computed) == list(saved['files'][filename]) and computed == saved['files'][filename],
            'Every complete saved record/provenance/hash association: ' + filename)
    totals[kind]['files'] += 1
    totals[kind]['raw_rows'] += len(rows)
    totals[kind]['postbirth_doublet_groups'] += len(groups)
    if kind == 'nodal':
        unique_nodal += len(positions)
    verified_files[filename] = dict(kind=kind, phase=phase, step=step, raw_rows=len(rows),
                                    unique_IDs=len(positions), duplicate_groups=len(groups),
                                    complete_record_compact_JSON_sha256=digest(compact(computed)),
                                    raw_csv_sha256=digest(raw), full_record_exact=True)
require(totals == saved['totals'] == {
    'nodal': {'files': 366, 'raw_rows': 128700, 'postbirth_doublet_groups': 5150},
    'reference': {'files': 366, 'raw_rows': 46350, 'postbirth_doublet_groups': 0}}
    and unique_nodal == 123550, 'Exact totals and unique nodal phase associations')
require(saved['status'] == 'PASS_OBSERVED_MULTIPLICITY_AND_LEXICAL_ASSOCIATIONS_ONLY'
        and saved['negatives'] == [] and saved['scanned_CSVs'] == saved['expected_CSVs'] == 732
        and saved['native_CSVs_rewritten_or_deduplicated'] is False
        and saved['native_receipt_original_passed'] is False
        and saved['independent_mechanical_assessment_performed'] is False, 'Original strict storage result scope')
opaque_after = {name: descriptor(NATIVE / name) for name in inventory}
current_after = {name: descriptor(ROOT / name) for name in selected}
require(opaque_before == opaque_after == inventory and current_before == current_after,
        'Complete native1122 and selected metadata before/after unchanged')
output = dict(schema='962-linear-cooling-independent-complete-storage-associations/v1',
              decision='CLEAR_COMPLETE_SAVED_LEXICAL_STORAGE_ASSOCIATIONS_ONLY',
              selected_records_before=current_before, selected_records_after=current_after,
              full1122_native_inventory_before=opaque_before, full1122_native_inventory_after=opaque_after,
              all732_complete_record_checks=verified_files, all732_record_key_order_and_values_exact=True,
              source_node_map=expected_source_map, totals=totals, unique_nodal_phase_associations=unique_nodal,
              native_output_count=1122, native_output_bytes=423178297,
              metadata_PIN_count=17, root_input_records=37,
              source_PIN_literals_and_count_bounds_checked_without_execution=True,
              requested732_raw_csvs_parsed_only=True, other390_files_hashed_opaque_only=True,
              raw_csvs_rewritten_averaged_or_deduplicated=False,
              original_native_passed=False, independent_3D_assessment_performed=False,
              scientific_constitutive_FEM_or_geometry_recomputed=False,
              root_lifecycle_runtime_Python_process_absence_and_sampled_RSS_attributed=True,
              no_universal_process_absence_or_true_peak_RSS_claim=True,
              all_selected_before_after_unchanged=True, failures=[],
              own_wall_seconds=time.monotonic() - START)
data = (json.dumps(output, indent=2, allow_nan=False) + '\n').encode()
with (HERE / 'independent-saved-check.json').open('xb') as stream:
    stream.write(data)
print(json.dumps(dict(decision=output['decision'], native_files=1122, parsed_CSVs=732,
                      totals=totals, unique_nodal_phase_associations=unique_nodal,
                      selected_current_records=len(selected), own_wall_seconds=output['own_wall_seconds'])))
