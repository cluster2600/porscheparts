"""HELD fixed matched-END saved-data sensitivity; no solver, CDF decode or FEM replay."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import struct

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[2]
INDEX = PREP / 'input-index.json'
INDEX_SHA256 = '224e234543a7a4c90cea7e9284cac4883986545cf3497a270cd0da1a5f906567'
OUTPUT = ROOT / 'work/962-engineering/cp1-oneway-thermoelastic-time-sensitivity-001/report.json'
DISP = ('disp_x', 'disp_y', 'disp_z')
FORCE = ('rx', 'ry', 'rz')
TENSORS = ('stress', 'elastic_strain', 'mechanical_strain', 'total_strain', 'thermal_eigenstrain')
COMP = ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2))
SUFFIX = ('xx', 'yy', 'zz', 'xy', 'xz', 'yz')
QP_FIELDS = tuple(t + '_' + s for t in TENSORS for s in SUFFIX)
SUPPORT = ((0, 'rx'), (0, 'ry'), (0, 'rz'), (32, 'ry'), (32, 'rz'), (137, 'rz'))
FALSE_FIELDS = ('mechanical_space_time_convergence', 'head_execution_authorized',
                'engineering_accepted', 'physics_qualified', 'material_qualified',
                'process_calibrated', 'manufacturing_authorized')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()


def bits(xyz):
    return struct.pack('<3d', *xyz)


def number(value):
    need(type(value) in (str, float, int), 'Explicit finite numeric scalar required')
    out = float(value)
    need(math.isfinite(out), 'Nonfinite scalar refused')
    return out


def integer(value):
    need(type(value) in (str, float, int), 'Explicit ID scalar required')
    x = Decimal(str(value))
    need(x.is_finite() and x >= 0 and x == x.to_integral_value(), 'Nonnegative integral ID required')
    return int(x)


def rows(path, columns, allow_empty=False):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
             and set(reader.fieldnames) == set(columns), 'Exact unique CSV field set required: ' + str(path))
        data = list(reader)
    need((data or allow_empty) and all(set(r) == set(columns) and all(v is not None and v != '' for v in r.values()) for r in data),
         'Complete CSV row required: ' + str(path))
    return data


def tensor(row, name):
    a = [[0.] * 3 for _ in range(3)]
    for (i, j), suffix in zip(COMP, SUFFIX):
        a[i][j] = a[j][i] = number(row[name + '_' + suffix])
    return a


def node_sample(path, geometry, active, columns, shared_doublets=()):
    # Only the native postbirth caller supplies the exact frozen shared25 IDs.
    expected = set(shared_doublets)
    need(len(expected) == len(shared_doublets) and expected <= set(active)
         and (not expected or len(expected) == 25)
         and all(type(tag) is int and geometry[tag][0] == 1. for tag in expected),
         'Only the explicit shared25 native doublet set is supported')
    fields = ('id', 'x', 'y', 'z', *columns)
    saved = rows(path, fields)
    data = {}; tokens = {}; positions = {}
    for line, row in enumerate(saved, 2):
        tag = integer(row['id'])
        xyz = tuple(number(row[k]) for k in 'xyz')
        need(tag in active and bits(xyz) == bits(geometry[tag]), 'Observed source ID/coordinate words must join native Exodus map')
        original = tuple(row[name] for name in fields)
        values = {name: number(row[name]) for name in columns}
        if tag in data:
            need(tag in expected and len(positions[tag]) == 1 and original == tokens[tag],
                 'Only two complete lexically identical rows per expected shared source ID are supported')
        else:
            data[tag] = values; tokens[tag] = original; positions[tag] = []
        positions[tag].append(line)
    need(set(data) == set(active), 'Complete active nodal sample required')
    need(len(saved) == len(active) + len(expected)
         and all(len(positions[tag]) == (2 if tag in expected else 1) for tag in active),
         'Exact expected shared doublets and all other singletons required')
    storage = dict(filename=Path(path).name, raw_csv_sha256=sha(path), comparison_field_order=list(fields),
                   raw_row_count=len(saved), unique_source_ID_count=len(data), expected_shared_doublet_IDs=sorted(expected),
                   verified_doublets=[dict(source_node_id=tag, csv_line_numbers_1_based=positions[tag],
                       complete_field_token_sha256=hashlib.sha256(json.dumps(tokens[tag], separators=(',', ':')).encode('utf-8')).hexdigest())
                       for tag in sorted(expected)],
                   token_hash_encoding='UTF8 compact JSON array of original CSV string tokens in comparison_field_order',
                   all_duplicate_complete_field_tokens_identical=True, all_other_multiplicities_one=True,
                   raw_rows_rewritten_or_averaged=False)
    return data, storage


def schedule():
    return [dict(coarse_step=k, fine_step=2*k,
                 nominal_common_time_decimal_s=str(Decimal(k)*Decimal('0.005')),
                 regime='pre_birth' if k < 40 else 'post_birth') for k in range(81)]


def saved_maps(report):
    geometry = {integer(r['id']): tuple(number(v) for v in r['coordinates_m']) for r in report['native_nodes']}
    cells = {integer(r['id']): [integer(n) for n in r['nodes']] for r in report['native_ordered_cells']}
    qcoords = {(integer(r['elem_id']), integer(r['qp_id'])): tuple(number(v) for v in r['coordinates_m'])
               for r in report['observed_QP_ID_coordinate_map']}
    need(len(geometry) == len(report['native_nodes']) == 425
         and len(cells) == len(report['native_ordered_cells']) == 256
         and all(len(p) == 3 for p in geometry.values())
         and all(len(conn) == len(set(conn)) == 8 and set(conn) <= set(geometry) for conn in cells.values())
         and len(qcoords) == len(report['observed_QP_ID_coordinate_map']) == 2048
         and set(qcoords) == {(tag, q) for tag in cells for q in range(8)}
         and all(len(p) == 3 for p in qcoords.values()), 'Complete accepted 425/256/2048 maps required')
    return geometry, cells, qcoords


def require_same_maps(left, right):
    lg, lc, lq = left; rg, rc, rq = right
    need(set(lg) == set(rg) and all(bits(lg[t]) == bits(rg[t]) for t in lg), 'Exact shared source ID/node-coordinate words required')
    need(lc == rc, 'Exact native cell IDs and ordered corners required')
    need(set(lq) == set(rq) and all(bits(lq[t]) == bits(rq[t]) for t in lq), 'Exact observed QP ID/coordinate maps required; no assumed QP order')


def qp_rows(path, active, qcoords):
    data = {}
    for row in rows(path, ('elem_id', 'qp_id', 'x', 'y', 'z', *QP_FIELDS)):
        key = (integer(row['elem_id']), integer(row['qp_id']))
        need(key[0] in active and key in qcoords and key not in data
             and bits(tuple(number(row[c]) for c in 'xyz')) == bits(qcoords[key]), 'Exact unique accepted QP ID/coordinate association required')
        tensors = {name: tensor(row, name) for name in TENSORS}
        data[key] = {name+'_'+suffix: tensors[name][i][j] for name in TENSORS for (i, j), suffix in zip(COMP, SUFFIX)}
    need(set(data) == {(tag, q) for tag in active for q in range(8)}, 'Complete all-eight-QP rows required')
    return data


def add_difference(metrics, field, coarse, fine, where):
    coarse = number(coarse); fine = number(fine); signed = coarse-fine; absolute = abs(signed)
    need(math.isfinite(signed) and math.isfinite(absolute), 'Finite absolute SI difference required')
    row = metrics.setdefault(field, dict(count=0, maximum_absolute_difference=None, witness=None))
    row['count'] += 1
    if row['maximum_absolute_difference'] is None or absolute > row['maximum_absolute_difference']:
        row['maximum_absolute_difference'] = absolute
        row['witness'] = dict(where, coarse=coarse, fine=fine,
                              coarse_binary64_hex=coarse.hex(), fine_binary64_hex=fine.hex(),
                              signed_coarse_minus_fine=signed, absolute_difference=absolute)


def reference_pairs(coarse, fine, geometry, born, shared):
    need(set(coarse) == set(fine) == set(born) and set(shared) <= set(born), 'Both complete own-birth reference sets required')
    pairs = []
    for tag in sorted(born):
        fields = {}
        for name in (*DISP, 'temperature', 'born_reference_temperature'):
            values = {}; add_difference(values, name, coarse[tag][name], fine[tag][name], dict(source_node_id=tag))
            fields[name] = values[name]['witness']
        pairs.append(dict(source_node_id=tag, coordinates_m=list(geometry[tag]),
                          coordinate_binary64_hex=[v.hex() for v in geometry[tag]], shared=tag in shared,
                          fields=fields))
    return pairs


def load_case(index, label):
    spec = index['cases'][label]
    report = json.loads((ROOT/spec['result']).read_text())
    accepted = json.loads((ROOT/spec['root_acceptance']).read_text())
    policy = json.loads((ROOT/spec['policy']).read_text())
    physics = json.loads((ROOT/spec['physics_contract']).read_text())
    receipt = json.loads((ROOT/spec['native_receipt']).read_text())
    closed = json.loads((ROOT/spec['native_closed']).read_text())
    pins = index['inputs']
    accepted_sha = accepted['result']['sha256'] if label == 'coarse' else accepted['result_sha256']
    need(accepted['decision'] == 'ACCEPT_FIXED_SYNTHETIC_SINGLE_LEVEL_SOFTWARE_VERIFICATION_ONLY'
         and accepted_sha == pins[spec['result']]['sha256'] and report['passed'] is True
         and report['source_physics_contract_sha256'] == pins[spec['physics_contract']]['sha256']
         and report['policy_sha256'] == pins[spec['policy']]['sha256']
         and receipt['passed'] is False and report['native_original_receipt_passed_field'] is False
         and all(report[k] is False and accepted[k] is False for k in FALSE_FIELDS), 'Exact accepted single-level source/result and false qualification fields required')
    need(policy['absolute_SI_limits'] == index['unchanged_single_case_limits']
         and physics['capture']['times_s'] == dict(dt=float(spec['nominal_dt_decimal_s']), last_step=spec['last_step'], birth_step=spec['birth_step']), 'Own time/reference case and unchanged seven single-case limits required')
    inventory = closed[spec['inventory_field']]
    for name in spec['selected_CSV_filenames']:
        path = str(Path(spec['native_directory'])/name); entry = inventory[name]
        need(pins[path]['sha256'] == entry['sha256'] == report['input_sha256'][path]
             and pins[path]['bytes'] == entry['bytes'], 'Every selected raw CSV must retain accepted native/result identity')
    summaries = {(r['step'], r['phase']): r for r in report['phase_summaries']}
    need(len(summaries) == len(report['phase_summaries']) == 2*(spec['last_step']+1)
         and set(summaries) == {(k, phase) for k in range(spec['last_step']+1) for phase in ('begin', 'end')}, 'Complete accepted single-case phase summaries required')
    # Native binary64 timestamps retain their existing accepted step association; no new tolerance is applied.
    times = {}
    for member in report['exodus_family']:
        for value in member['times']:
            time = number(value); step = round(time*spec['steps_per_second'])
            need(step not in times and 0 <= step <= spec['last_step'], 'Unique previously accepted END step/time association required')
            times[step] = time
    need(set(times) == set(range(spec['last_step']+1)), 'Complete accepted native ending timestamps required')
    return dict(spec=spec, report=report, policy=policy, summaries=summaries, times=times, maps=saved_maps(report))


def checked_inputs(index, digest):
    need(digest == INDEX_SHA256 and sha(INDEX) == digest, 'Exact held input index required')
    need(index['input_count'] == len(index['inputs']) == 342
         and sum(r['role'] == 'native-CSV' for r in index['inputs'].values()) == 328, 'Fixed finite metadata and 328 raw CSV input set required')
    for name, record in index['inputs'].items():
        relative = Path(name); path = ROOT/relative
        need(not relative.is_absolute() and '..' not in relative.parts and path.is_file()
             and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
             and path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], 'Bound sensitivity input drift: '+name)


def compare(index):
    cases = {label: load_case(index, label) for label in ('coarse', 'fine')}
    require_same_maps(cases['coarse']['maps'], cases['fine']['maps'])
    geometry, cells, qcoords = cases['coarse']['maps']
    old = {t for t, p in geometry.items() if p[0] <= 1.}; born = {t for t, p in geometry.items() if p[0] >= 1.}; shared = old & born
    old_cells = {t for t, conn in cells.items() if max(geometry[n][0] for n in conn) <= 1.}; born_cells = set(cells)-old_cells
    need((len(old), len(born), len(shared), len(old_cells), len(born_cells)) == (225, 225, 25, 128, 128), 'Accepted fixed old/born/shared partition required')
    birth = {}; birth_storage = {}
    for label, case in cases.items():
        spec = case['spec']; directory = ROOT/spec['native_directory']; step = spec['birth_step']
        nodes, storage = node_sample(directory/f'thermoelastic_begin_{step:04d}.csv', geometry, set(geometry), (*DISP, 'temperature'), sorted(shared))
        refs, rstorage = node_sample(directory/f'thermoelastic_reference_begin_{step:04d}.csv', geometry, born, ('born_reference_temperature',))
        summary = case['summaries'][(step, 'begin')]
        need(storage == summary['native_nodal_storage'] and rstorage == summary['born_reference_storage'], 'Own birth CSV lexical/ordinal provenance must match accepted result')
        birth[label] = {tag: dict(nodes[tag], **refs[tag]) for tag in born}
        birth_storage[label] = dict(own_label=spec['birth_reference_label'], native_nodal_storage=storage, born_reference_storage=rstorage,
                                    nominal_birth_step_time_decimal_s=str(Decimal(step)*Decimal(spec['nominal_dt_decimal_s'])),
                                    accepted_previous_END_time_s=case['times'][step-1], accepted_current_END_time_s=case['times'][step],
                                    BEGIN_CSV_has_no_timestamp_column=True, BEGIN_timestamp_is_not_relabelled_as_END=True)
    by_regime = {r: dict(node_regions={n: {} for n in ('old_only', 'shared', 'born_only')},
                          tensor_material_regions={n: {} for n in ('old2', 'born3')}, support_reactions={}, saved_energy={})
                 for r in ('pre_birth', 'post_birth')}
    results = []
    for pair in schedule():
        k = pair['coarse_step']; active_nodes = old if k < 40 else set(geometry); active_cells = old_cells if k < 40 else set(cells)
        loaded = {}; storage_rows = {}
        for label, case in cases.items():
            step = pair[label+'_step']; directory = ROOT/case['spec']['native_directory']
            nodes, storage = node_sample(directory/f'thermoelastic_end_{step:04d}.csv', geometry, active_nodes, (*DISP, 'temperature', *FORCE), sorted(shared) if k >= 40 else ())
            summary = case['summaries'][(step, 'end')]
            need(storage == summary['native_nodal_storage'] and summary['active_nodes'] == len(active_nodes)
                 and summary['active_cells'] == len(active_cells), 'Complete matched END nodal/count/provenance association required')
            qp = qp_rows(directory/f'thermoelastic_end_fields_{step:04d}.csv', active_cells, qcoords)
            need(summary['quadrature_rows'] == len(qp), 'Matched complete accepted QP count required')
            loaded[label] = (nodes, qp); storage_rows[label] = storage
        step_result = dict(pair, accepted_native_END_times_s={label: cases[label]['times'][pair[label+'_step']] for label in cases},
                           active_nodes=len(active_nodes), active_cells=len(active_cells), quadrature_rows=8*len(active_cells),
                           node_regions={n: {} for n in ('old_only', 'shared', 'born_only')}, tensor_material_regions={n: {} for n in ('old2', 'born3')},
                           support_reactions={}, saved_energy={}, native_nodal_storage=storage_rows)
        aggregate = by_regime[pair['regime']]
        for tag in sorted(active_nodes):
            region = 'shared' if tag in shared else 'old_only' if tag in old else 'born_only'
            for field in ('temperature', *DISP):
                where = dict(coarse_step=k, fine_step=2*k, source_node_id=tag)
                for target in (step_result, aggregate):
                    add_difference(target['node_regions'][region], field, loaded['coarse'][0][tag][field], loaded['fine'][0][tag][field], where)
        for tag, field in SUPPORT:
            for target in (step_result, aggregate):
                add_difference(target['support_reactions'], field, loaded['coarse'][0][tag][field], loaded['fine'][0][tag][field], dict(coarse_step=k, fine_step=2*k, source_node_id=tag, component=field))
        for key in sorted(loaded['coarse'][1]):
            region = 'old2' if key[0] in old_cells else 'born3'
            for field in QP_FIELDS:
                where = dict(coarse_step=k, fine_step=2*k, elem_id=key[0], qp_id=key[1])
                for target in (step_result, aggregate):
                    add_difference(target['tensor_material_regions'][region], field, loaded['coarse'][1][key][field], loaded['fine'][1][key][field], where)
        coarse_energy = cases['coarse']['summaries'][(k, 'end')]['elastic_strain_energy_J_diagnostic']
        fine_energy = cases['fine']['summaries'][(2*k, 'end')]['elastic_strain_energy_J_diagnostic']
        for target in (step_result, aggregate):
            add_difference(target['saved_energy'], 'elastic_strain_energy_J_diagnostic', coarse_energy, fine_energy, dict(coarse_step=k, fine_step=2*k))
        results.append(step_result)
    return dict(schema='962-fixed-matched-END-thermoelastic-sensitivity/v1', status='completed_saved_sensitivity_no_cross_level_acceptance_gate',
                matched_END_pairs=results, aggregate_by_pre_post_birth=by_regime,
                own_birth_reference_pairs=reference_pairs(birth['coarse'], birth['fine'], geometry, born, shared), own_birth_storage=birth_storage,
                maps=dict(nodes=425, ordered_HEX8_cells=256, observed_QPs=2048, exact_node_cell_QP_maps_equal=True),
                field_units=dict(temperature='K', displacement='m', support_reaction='N', stress='Pa', strains='dimensionless', saved_energy='J'),
                difference_retention='Every selected scalar scanned. Complete per-time and pre/post-birth counts/maxima/witnesses; all225 birth-reference pairs retained. No per-scalar field-difference archive, sampling or averaging.',
                maximum_ties='First in fixed step, sorted source-ID/QP and declared field order.',
                single_case_limits=index['unchanged_single_case_limits'], single_case_limits_are_not_cross_level_thresholds=True,
                source_original_boolean_fields={label: {k: v for k, v in case['report'].items() if type(v) is bool} for label, case in cases.items()},
                source_accepted_results={label: index['inputs'][case['spec']['result']] for label, case in cases.items()},
                cross_level_pass=None, cross_level_tolerance=None, convergence_order=None,
                caveats=['Same fixed mesh and two thermal histories only; not mechanical time/space convergence or independent ML train/test cases.',
                         'Paired integer END steps share prescribed nominal decimal time; both accepted saved binary64 timestamps are retained, never forced equal.',
                         'Born3 uses own BEGIN40 versus BEGIN80 u/T/reference on225 DOFs including25shared. Differences include reference/history and thermal-discretization sensitivity, not a pure mechanical integration error.',
                         'Saved scalar elastic energy remains accepted-assessor-attributed diagnostic; no reintegration, work=2U, CDF or constitutive/FEM replay.',
                         'CP1-like E/nu/alpha and thermal properties remain unmeasured assumptions; no material/strength/LPBF/head qualification.'],
                **{name: False for name in FALSE_FIELDS}, native_execution_authorized=False, automatic_retry=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-index-sha256', required=True)
    args = parser.parse_args()
    need(INDEX.is_file() and not INDEX.is_symlink(), 'Regular nonsymlink held input index required')
    index = json.loads(INDEX.read_text()); checked_inputs(index, args.input_index_sha256)
    need(not OUTPUT.parent.exists() and not OUTPUT.parent.is_symlink() and not OUTPUT.exists(), 'Fresh fixed diagnostic output directory required')
    result = compare(index)
    checked_inputs(index, args.input_index_sha256)
    result.update(input_index_sha256=args.input_index_sha256, source_sha256=sha(Path(__file__).resolve()), bound_inputs_unchanged=True)
    OUTPUT.parent.mkdir()
    with OUTPUT.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
