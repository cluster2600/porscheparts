"""Independent byte/metadata review of one stopped native002 capture; no FE oracle."""
import csv
import hashlib
import json
from pathlib import Path
import re
from collections import Counter
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / 'work/962-engineering'
HERE = Path(__file__).resolve().parent
OUT = E / 'cp1-oneway-thermoelastic-transfer-002'
EXEC = E / 'cp1-oneway-thermoelastic-transfer-root-execution-002'
ACTUAL = E / 'cp1-oneway-thermoelastic-transfer-execution-prep-002/actual-contract.json'
INDEX = ACTUAL.with_name('index.json')

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def data(path):
    return json.loads(path.read_text())

def identity(path):
    assert path.is_file() and not path.is_symlink() and path.resolve() == path
    return dict(sha256=digest(path), bytes=path.stat().st_size)

def rel(path):
    return str(path.relative_to(ROOT))

a = data(ACTUAL)
ix = data(INDEX)
closed = data(EXEC / 'closed-result.json')
launch = data(EXEC / 'launch.json')
accepted = data(EXEC / 'child-peer-acceptance.json')
receipt = data(OUT / 'native-execution.json')
assert digest(ACTUAL) == '9fd012256eb321f1a7717164cd929c6f0e89a3c4d75e02f96710a45b34d9cefb'
assert digest(INDEX) == 'efc77e0c9574af1263606b287d106b26d6e1146aa6c9d92745503901974b8bda'
assert digest(OUT / 'native-execution.json') == '728fe39456b4c4d92bb61ea1a34ca6f8915bc09c701168d03600dc1b56d8c574'
assert closed['actual_sha256'] == digest(ACTUAL) == receipt['actual_contract_sha256'] == receipt['contract_sha256']
assert closed['index_sha256'] == digest(INDEX)
assert digest(EXEC / 'launch.json') == closed['root_launch_sha256']
assert launch['argv'] == ix['planned_adapter_argv'] and launch['actual_sha256'] == digest(ACTUAL)
assert closed['peer_sha256'] == launch['child_peer_sha256'] == accepted['peer_sha256'] == 'e92fbb3d53371dcd7a81a4a6fb82f821c4ba378d04f308cbdc78f5ac043c610f'
assert closed['bindings_sha256'] == launch['child_bindings_sha256'] == accepted['bindings_sha256'] == 'c48e3b190484593fc2cbe8a97383eccc41d3d1289b7f7f7413f3b5a172675995'
assert accepted['declared_controller_argv_exact'] is True
assert closed['all437_inputs_before'] == closed['all437_inputs_after'] == a['input_sha256'] and len(a['input_sha256']) == 437
assert closed['all437_before_after_unchanged'] is True
assert closed['selected19_files_before'] == closed['selected19_files_after'] == a['runtime_sha256s'] and len(a['runtime_sha256s']) == 19
assert closed['selected13_links_before'] == closed['selected13_links_after'] == a['runtime_symlinks'] and len(a['runtime_symlinks']) == 13
assert closed['selected19_files13_links_before_after_unchanged'] is True
assert closed['selected_python_before'] == closed['selected_python_after'] == a['controller_interpreter']['sha256'] == launch['selected_python_sha256']
assert closed['external_records_before'] == closed['external_records_after']
small = {k: v for k, v in a['input_sha256'].items() if not k.endswith('.csv')}
assert len(small) == 115
records = {ROOT / k for k in small} | {ROOT / k for k in closed['external_records_before']} | {EXEC / name for name in ('closed-result.json', 'launch.json', 'child-peer-acceptance.json', 'adapter.stdout.log', 'adapter.stderr.log')}
assert all(p.is_file() and not p.is_symlink() for p in records)
record_before = {rel(p): identity(p) for p in sorted(records)}
assert all(record_before[k]['sha256'] == v for k, v in small.items())
assert all(record_before[k]['sha256'] == v for k, v in closed['external_records_before'].items())
for k in ('returncode', 'native_returncode'):
    assert closed[k] == 0
assert closed['stop_reason'] is None and closed['controller_error'] is None
assert closed['SIGTERM_requested'] is False and closed['fallback_SIGKILL'] is False
assert closed['adapter_wait_reaped'] is True and closed['owned_adapter_observed_absent'] is True
assert closed['native_PID_directly_observed'] is False
assert launch['owned_adapter_only'] is True and launch['native_cleanup_attributed_to_frozen_adapter_finally'] is True
assert closed['adapter_pid'] == launch['adapter_pid'] == launch['adapter_pgid']
assert launch['outer_wall_seconds'] == a['outer_wall_seconds'] == 115 and launch['grace_seconds'] == 10
assert closed['native_execution_completed'] is True and closed['native_stop_reason'] is None
assert receipt['returncode'] == 0 and receipt['native_execution_completed'] is True and receipt['process_reaped'] is True
assert receipt['jobs'] == [dict(name='native', returncode=0, process_reaped=True)]
assert receipt['passed'] is False and receipt['independent_assessment_performed'] is False and closed['independent_assessment_performed'] is False
assert receipt['stop_reason'] is None and receipt['controller_error'] is None and receipt['controller_SIGTERM_requested'] is False
assert receipt['inputs_unchanged'] is True and receipt['binary_and_runtime_unchanged'] is True
assert receipt['resources'] == a['resources'] and receipt['runtime_sha256s'] == a['runtime_sha256s'] and receipt['runtime_symlinks'] == a['runtime_symlinks']
assert receipt['command'] == [str(E / 'moose-local-installed-002/bin/combined-opt'), '-skip_petscrc', '--n-threads=1', '-i', 'thermoelastic-birth.i']
assert json.loads((EXEC / 'adapter.stdout.log').read_text()) == receipt
assert (EXEC / 'adapter.stderr.log').stat().st_size == 0
entries = list(OUT.rglob('*'))
assert not any(p.is_symlink() for p in entries)
files = {str(p.relative_to(OUT)): p for p in entries if p.is_file()}
assert set(files) == set(closed['complete_recursive_output_inventory']) and len(files) == closed['output_count'] == 990
inventory = {k: identity(v) for k, v in sorted(files.items())}
assert inventory == closed['complete_recursive_output_inventory']
assert sum(v['bytes'] for v in inventory.values()) == closed['output_bytes'] == 359397778
assert receipt['complete_artifact_sha256'] == {k: v['sha256'] for k, v in inventory.items() if k != 'native-execution.json'}
assert receipt['artifact_sha256'] == {k: v['sha256'] for k, v in inventory.items() if k != 'native-execution.json' and Path(k).name == k}
assert len(receipt['complete_artifact_sha256']) == 989 and len(receipt['artifact_sha256']) == 978
assert receipt['final_output_bytes_before_receipt'] == closed['output_bytes'] - inventory['native-execution.json']['bytes']
prep = E / 'cp1-oneway-thermoelastic-transfer-prep-002'
transfer = E / 'cp1-oneway-thermoelastic-transfer-inputs-001'
prim = E / 'cp1-oneway-thermoelastic-transfer-source-peer-001/primary-sources.json'
sources = [prep / x for x in ['run_mac.py', 'held-preparation.json', 'METHOD.md', 'thermoelastic-birth.i', 'card.json', 'case-contract.json']] + [transfer / x for x in ['old-end.grid', 'born-end.grid', 'born-begin80.grid', 'transfer-manifest.json']] + [prim]
aliases = {str(Path('source-snapshots') / p.relative_to(ROOT)): rel(p) for p in sources}
aliases.update({'actual-contract.json': rel(ACTUAL), 'frozen-contract.json': rel(prep / 'case-contract.json'), 'thermoelastic-birth.i': rel(prep / 'thermoelastic-birth.i'), 'card.json': rel(prep / 'card.json')})
aliases.update({name: rel(transfer / name) for name in ['old-end.grid', 'born-end.grid', 'born-begin80.grid', 'transfer-manifest.json']})
assert len(aliases) == len(receipt['input_sha256']) == 19
assert receipt['input_sha256'] == {name: inventory[name]['sha256'] for name in aliases}
assert all(inventory[name]['sha256'] == digest(ROOT / original) for name, original in aliases.items())
assert receipt['physics_contract_sha256'] == a['source_physics_contract_sha256'] == digest(prep / 'case-contract.json')
assert receipt['transfer_manifest_sha256'] == a['transfer_manifest_sha256'] == digest(transfer / 'transfer-manifest.json')
assert data(OUT / 'card.json') == data(prep / 'card.json')
launch_native = data(OUT / 'launch.json')
assert launch_native['status'] == 'running' and launch_native['passed'] is False and launch_native['native_execution_completed'] is False
assert launch_native['input_sha256'] == receipt['input_sha256'] and launch_native['jobs'] == []
assert launch_native['command'] == receipt['command']
# CSV capture metadata only: schema/cardinality/name ranges, never tensor or ID acceptance.
component = ('xx', 'xy', 'xz', 'yy', 'yz', 'zz')
tensor = ('elastic_strain', 'mechanical_strain', 'stress', 'thermal_eigenstrain', 'total_strain')
headers = {
 'begin': ['disp_x', 'disp_y', 'disp_z', 'id', 'temperature', 'x', 'y', 'z'],
 'end': ['disp_x', 'disp_y', 'disp_z', 'id', 'rx', 'ry', 'rz', 'temperature', 'x', 'y', 'z'],
 'reference_begin': ['born_reference_temperature', 'id', 'x', 'y', 'z'],
 'reference_end': ['born_reference_temperature', 'id', 'x', 'y', 'z'],
 'begin_fields': sorted([x + '_' + y for x in tensor for y in component] + ['elem_id', 'qp_id', 'x', 'y', 'z']),
 'end_fields': sorted([x + '_' + y for x in tensor for y in component] + ['elem_id', 'qp_id', 'x', 'y', 'z'])}
expected_names = {f'thermoelastic_{family}_{step:04d}.csv' for family in headers for step in range(161)}
assert {name for name in files if name.endswith('.csv')} == expected_names
csv_metadata = {}; totals = Counter(); repeats = Counter()
for family, header in headers.items():
 for step in range(161):
    name = f'thermoelastic_{family}_{step:04d}.csv'; ids = Counter(); count = 0
    with files[name].open(newline='') as stream:
        reader = csv.reader(stream); assert next(reader) == header
        for row in reader:
            assert len(row) == len(header); count += 1
            if 'id' in header: ids[row[header.index('id')]] += 1
    row = dict(rows=count, columns=len(header))
    if 'id' in header:
        row.update(distinct_ID_strings=len(ids), repeated_ID_strings=sum(v > 1 for v in ids.values()), max_ID_string_multiplicity=max(ids.values(), default=0))
        repeats[(family, count, len(ids), row['repeated_ID_strings'])] += 1
    csv_metadata[name] = row; totals[family] += count
assert totals['begin_fields'] == totals['end_fields'] == 247808
# No requirement that450 sampled rows be425 geometry rows: preserve duplicates for later oracle.
exodus = {}
for name in sorted(files):
 if name == 'thermoelastic.e' or re.fullmatch(r'thermoelastic[.]e-s[0-9]+', name):
    with files[name].open('rb') as stream: magic = stream.read(4)
    assert magic in (b'CDF\x01', b'CDF\x02')
    exodus[name] = dict(inventory[name], magic_hex=magic.hex())
assert set(exodus) == {'thermoelastic.e', 'thermoelastic.e-s002'}
log = (OUT / 'native.log').read_text(); clean = re.sub(r'\x1b\[[0-9;]*m', '', log)
steps = re.findall(r'^Time Step ([0-9]+), time = ([0-9.eE+-]+), dt = ([0-9.eE+-]+)$', clean, re.M)
assert [int(x[0]) for x in steps] == list(range(1, 161))
assert all(Decimal(time) == Decimal(step) * Decimal('0.0025') and Decimal(dt) == Decimal('0.0025') for step, time, dt in steps)
assert clean.count('Solve Converged!') == 160
assert re.search(r'Nodes:\s+425', clean) and re.search(r'Elems:\s+256', clean)
assert 'Solver Mode:             NEWTON' in clean
samples = receipt['RSS_samples'];assert len(samples) == 364 and all(x['job'] == 'native' and x['RSS_bytes'] >= 0 for x in samples)
assert [x['wall_seconds'] for x in samples] == sorted(x['wall_seconds'] for x in samples)
assert max(x['RSS_bytes'] for x in samples) == receipt['max_observed_RSS_bytes'] == 207273984
assert receipt['wall_seconds'] < 100 and closed['wall_seconds'] < 115
assert all(closed[k] is False for k in ['engineering_accepted', 'physics_qualified', 'material_qualified', 'process_calibrated', 'manufacturing_authorized'])
record_after = {k: identity(ROOT / k) for k in record_before};assert record_before == record_after
output_after = {k: identity(p) for k, p in sorted(files.items())};assert output_after == inventory
assert set(files) == {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()} and not any(p.is_symlink() for p in OUT.rglob('*'))
result = dict(schema='962-oneway-native002-stopped-byte-metadata-check/v1', saved_records_before=record_before, saved_records_after=record_after, all_saved_records_unchanged=True, current_small_actual_inputs=115, original_CSV437_input_map_scope='322 original CSV digest values joined to root before/after, bodies not freshly read by this reviewer', full990_native_output_inventory=inventory, output_after_exact=True, output_bytes=359397778, complete_receipt_map_count=989, flat_receipt_map_count=978, materialized_input_count=19, snapshot_aliases=aliases, CSV_capture_metadata=csv_metadata, CSV_row_totals=dict(totals), CSV_ID_string_multiplicity_summaries=[dict(family=k[0], rows=k[1], distinct_ID_strings=k[2], repeated_ID_strings=k[3], files=v) for k,v in sorted(repeats.items())], exodus_family_magic_and_byte_identity=exodus, native_log_steps=160, native_log_solve_converged_messages=160, intended_geometry_only_from_source_and_log=dict(nodes=425,HEX8=256), independently_decoded_Exodus_geometry_or_ID_bijection=False, tensor_or_constitutive_or_equilibrium_or_birth_reference_acceptance=False, native_receipt_passed=False, assessor_executed=False, native_PID_directly_observed_by_root=False, native_wait_reap_attributed_to_frozen_adapter_finally_and_receipt=True, universal_native_descendant_absence_claimed=False, native_RSS_samples=364, maximum_sampled_owned_leader_RSS_bytes=207273984, root_wall_seconds=closed['wall_seconds'], native_wall_seconds=receipt['wall_seconds'], warning_observations=['output_postprocessors deprecation in captured log','-skip_petscrc appears in unused database-option warning; no cause or PETSc configuration-conformance inference'], no_scientific_native_or_prepared_source_execution=True)
with (HERE / 'independent-saved-check.json').open('x') as stream:
    json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
print(json.dumps(dict(status='PASS_STOPPED_NATIVE_CAPTURE_BYTES_AND_METADATA_ONLY',files=990,bytes=359397778,CSV_files=966,Gauss_rows_per_phase=247808,geometry_ID_or_tensor_acceptance=False)))
