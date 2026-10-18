"""Final-field Kirchhoff witness checks; no native/scientific dependency."""
import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import sys

REFERENCE_SHA = '390f3263f47aaf6458c73df4ccb6448a9a461a64fcbe530905848761fa9e60ff'
H = 10.0/16
AREA = 2.0
OFFSETS = tuple(itertools.product((0, 1), repeat=3))
GAUSS = tuple(itertools.product((-1/math.sqrt(3), 1/math.sqrt(3)), repeat=3))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference():
    path = Path(__file__).with_name('kirchhoff_reference.py')
    need(sha(path) == REFERENCE_SHA, 'Frozen independent oracle changed')
    spec = importlib.util.spec_from_file_location('frozen_Kirchhoff_oracle', path)
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def csv_rows(path, required):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames is not None and len(reader.fieldnames) == len(set(reader.fieldnames))
             and set(required) <= set(reader.fieldnames), 'Missing/duplicate CSV columns')
        rows = []
        for row in reader:
            need(None not in row and all(v is not None and v.strip() for v in row.values()), 'Partial CSV row')
            values = {k: float(v) for k, v in row.items()}
            need(all(math.isfinite(v) for v in values.values()), 'Nonfinite CSV value')
            rows.append(values)
    need(rows, 'Empty CSV export')
    return rows


def associated(rows, expected, value_name):
    need(len(rows) == len(expected), 'Incomplete spatial field')
    observed = {}
    ids = set()
    for row in rows:
        need(set(('id', 'x', 'y', 'z', value_name)) <= set(row), 'Missing spatial field columns')
        need(all(type(v) in (int, float) and math.isfinite(v) for v in row.values()), 'Nonfinite spatial field')
        identifier = row['id']
        point = tuple(row[k] for k in ('x', 'y', 'z'))
        need(identifier == int(identifier) and 0 <= identifier < len(expected) and identifier not in ids, 'Duplicate/noninteger/out-of-range sampler ID')
        need(point in expected and point not in observed, 'Unexpected/duplicate spatial coordinate')
        ids.add(identifier)
        observed[point] = row[value_name]
    need(set(observed) == expected and ids == set(range(len(expected))), 'Incomplete coordinate/ID coverage')
    return observed


def quadrature(corners):
    for point in GAUSS:
        yield math.fsum(t*math.prod((1+(2*o-1)*p)/2 for o, p in zip(offset, point))
                        for offset, t in zip(OFFSETS, corners))


def boundary_power(oracle, direction, field, hot):
    cell = 15 if hot else 0
    total = []
    for gx, gy in itertools.product((-1/math.sqrt(3), 1/math.sqrt(3)), repeat=2):
        section = []
        for z in (cell*H, (cell+1)*H):
            base = field[(0.0, 0.0, z)]
            section.append(base + math.fsum((field[(float(x), 2.0*y, z)]-base)*(1+(2*x-1)*gx)*(1+(2*y-1)*gy)/4
                                            for x, y in itertools.product((0, 1), repeat=2)))
        temperature = section[1 if hot else 0]
        gradient = (section[1]-section[0])/H
        total.append((-1 if hot else 1)*AREA/4*float(oracle.conductivity(direction, temperature))*gradient)
    return math.fsum(total)


def assess_fields(direction, nodes, properties, powers, oracle=None):
    """Complete fixed-grid fields; row order is irrelevant and no node=row rule is used."""
    need(direction in ('Z', 'XY'), 'Only separate Z or XY columns')
    oracle = oracle or reference()
    node_points = {(float(x), 2.0*y, i*H) for x, y, i in itertools.product((0, 1), (0, 1), range(17))}
    cell_points = {(0.5, 1.0, (i+0.5)*H) for i in range(16)}
    field = associated(nodes, node_points, 'temperature')
    material = associated(properties, cell_points, 'k_seen')
    need(len(powers) == 1 and set(('cold_outward_W', 'hot_outward_W')) <= set(powers[0]), 'Exactly one final end-power row required')
    need(all(type(v) in (int, float) and math.isfinite(v) for v in powers[0].values()), 'Nonfinite end power')
    need(23 <= min(field.values()) <= max(field.values()) <= 250, 'Final nodal field outside measured range')
    checks = []
    def check(name, error, limit):
        need(math.isfinite(error) and math.isfinite(limit) and limit >= 0, 'Invalid numerical comparison')
        checks.append(dict(name=name, absolute_error=abs(error), limit=limit, passed=abs(error) <= limit))
    sections = [[field[(float(x), 2.0*y, i*H)] for x, y in itertools.product((0, 1), repeat=2)] for i in range(17)]
    check('cold_endpoint_C', max(abs(t-23) for t in sections[0]), 1e-10)
    check('hot_endpoint_C', max(abs(t-250) for t in sections[-1]), 1e-10)
    for i, values in enumerate(sections):
        check(f'cross_section_uniformity_{i}', max(values)-min(values), 1e-10)
    for point, temperature in field.items():
        check('continuum_node_' + '_'.join(map(str, point)), (temperature-float(oracle.temperature(direction, point[2])))/227, 0.01)
    cells = []
    all_gauss = []
    for i in range(16):
        corners = [field[(float(x), 2.0*y, (i+z)*H)] for x, y, z in OFFSETS]
        temperatures = list(quadrature(corners))
        need(all(23 <= t <= 250 for t in temperatures), 'Final Gauss temperature outside measured range')
        all_gauss.extend(temperatures)
        k = math.fsum(float(oracle.conductivity(direction, t)) for t in temperatures)/8
        observed = material[(0.5, 1.0, (i+0.5)*H)]
        check(f'k_Gauss_average_cell_{i}', observed-k, 1e-9)
        flux = -AREA*k*(math.fsum(sections[i+1])/4-math.fsum(sections[i])/4)/H
        need(math.isfinite(flux) and flux != 0, 'Finite nonzero cell heat rate required')
        cells.append(dict(cell_z_index=i, center_mm=[0.5, 1.0, (i+0.5)*H],
                          actual_Gauss_temperatures_C=temperatures, independent_k_average_W_mmK=k,
                          native_k_seen_W_mmK=observed, consistent_axial_heat_rate_W=flux))
    mean = math.fsum(c['consistent_axial_heat_rate_W'] for c in cells)/16
    need(math.isfinite(mean) and mean != 0, 'Finite nonzero mean cell heat rate required')
    spread = max(abs(c['consistent_axial_heat_rate_W']-mean) for c in cells)/abs(mean)
    check('consistent_cell_flux_relative_deviation_about_mean', spread, 1e-9)
    native_cold, native_hot = powers[0]['cold_outward_W'], powers[0]['hot_outward_W']
    need(native_cold > 0 and native_hot < 0, 'Outward cold/hot power signs incorrect')
    direct_cold = boundary_power(oracle, direction, field, False)
    direct_hot = boundary_power(oracle, direction, field, True)
    check('native_cold_vs_direct_Q1_boundary_W', native_cold-direct_cold, 1e-9)
    check('native_hot_vs_direct_Q1_boundary_W', native_hot-direct_hot, 1e-9)
    exact_cold = float(-oracle.AREA_MM2*oracle.axial_flux_density(direction))
    need(math.isfinite(exact_cold) and exact_cold > 0, 'Positive continuum end-power reference required')
    check('cold_continuum_relative_power', (native_cold-exact_cold)/exact_cold, 0.01)
    check('hot_continuum_relative_power', (native_hot+exact_cold)/exact_cold, 0.01)
    check('raw_native_end_power_relative_imbalance', (native_cold+native_hot)/exact_cold, 0.01)
    failed = [c for c in checks if not c['passed']]
    return dict(passed=not failed, direction=direction, nodes=68, cells=16, free_temperature_DOFs=60,
                checks=checks, failed_checks=failed, cell_records=cells,
                final_nodal_temperature_range_C=[min(field.values()), max(field.values())],
                final_Gauss_temperature_range_C=[min(all_gauss), max(all_gauss)],
                final_fields_and_quadrature_in_measured_range=True,
                all_intermediate_nonlinear_evaluations_observed=False, universal_range_refusal_verified=False,
                consistent_axial_mean_heat_rate_W=mean, consistent_flux_relative_deviation=spread,
                consistent_flux_peak_to_peak_relative=(max(c['consistent_axial_heat_rate_W'] for c in cells)-min(c['consistent_axial_heat_rate_W'] for c in cells))/abs(mean),
                native_outward_power_W=[native_cold, native_hot], independent_Q1_outward_power_W=[direct_cold, direct_hot],
                exact_continuum_outward_power_W=[exact_cold, -exact_cold],
                mesh_convergence_established=False, head_or_process_qualified=False, manufacturing_authorized=False)


def selected(pins, prefix, kind):
    names = [n for n in pins if re.fullmatch(re.escape(prefix) + '_' + kind + r'(?:_\d+)?\.csv', n)]
    need(len(names) == 1, 'Missing/ambiguous final ' + kind + ' CSV')
    return names[0]


def assess(directory, contract_path, contract_sha256, direction):
    directory, contract_path = Path(directory), Path(contract_path)
    need(direction in ('Z', 'XY') and directory.is_dir() and not directory.is_symlink(), 'Fixed case and regular output directory required')
    need(sha(contract_path) == contract_sha256 and sha(directory/'frozen-contract.json') == contract_sha256, 'Frozen contract changed')
    receipt = json.loads((directory/'native-execution.json').read_text())
    need(receipt['case'] == receipt['direction'] == direction and receipt['contract_sha256'] == contract_sha256, 'Case/contract association changed')
    need(type(receipt['returncode']) is int and receipt['returncode'] == 0 and receipt['process_reaped'] is True and receipt['controller_error'] is None
         and receipt['binary_and_runtime_unchanged'] is True and receipt['inputs_unchanged'] is True
         and receipt['native_execution_completed'] is True, 'Native execution did not complete unchanged')
    pins = receipt['artifact_sha256']
    need(isinstance(pins, dict) and pins, 'Stopped artifact manifest missing')
    paths = [p for p in directory.rglob('*') if p.is_file() or p.is_symlink()]
    need(not any(p.is_symlink() for p in paths), 'Symlink export refused')
    names = {str(p.relative_to(directory)) for p in paths if p.name not in ('native-execution.json', 'assessment.json')}
    need(names == set(pins), 'Stopped artifact inventory mismatch')
    for name, digest in pins.items():
        p = Path(name)
        need(not p.is_absolute() and '..' not in p.parts and re.fullmatch(r'[0-9a-f]{64}', str(digest))
             and sha(directory/p) == digest, 'Stopped artifact hash mismatch: ' + name)
    input_pins = receipt['input_sha256']
    need(isinstance(input_pins, dict) and input_pins and set(input_pins) <= set(pins), 'Stopped input binding missing')
    need(all(pins[n] == h for n, h in input_pins.items()) and input_pins.get('frozen-contract.json') == contract_sha256, 'Stopped input association mismatch')
    prefix = 'conductivity-' + direction.lower()
    nodal = selected(pins, prefix, 'nodes')
    cells = selected(pins, prefix, 'properties')
    required = {nodal, cells, prefix+'.csv', 'native.log', 'conductivity-z.i', 'frozen-contract.json'}
    if direction == 'XY':
        required.add('conductivity-xy.i')
    need(required <= set(pins), 'Missing stopped required export')
    contract = json.loads(contract_path.read_text())
    sources = contract['source_sha256s']
    need(sources.get('assess_material_bar.py') == sha(__file__) and sources.get('kirchhoff_reference.py') == REFERENCE_SHA, 'Assessor/oracle differs from frozen sources')
    need(all(Path(n).name == n and input_pins.get('source-snapshots/'+n) == h for n, h in sources.items()), 'Frozen source snapshot association mismatch')
    need(all(input_pins.get(n) == contract['source_sha256s'][n] for n in ('conductivity-z.i',) + (('conductivity-xy.i',) if direction == 'XY' else ())), 'Input differs from frozen case source')
    need((directory/'native.log').read_bytes().count(b'Solve Converged!') == 1, 'Exactly one converged steady solve required')
    result = assess_fields(direction, csv_rows(directory/nodal, ('id', 'x', 'y', 'z', 'temperature')),
                           csv_rows(directory/cells, ('id', 'x', 'y', 'z', 'k_seen')),
                           csv_rows(directory/(prefix+'.csv'), ('cold_outward_W', 'hot_outward_W')))
    need(all(sha(directory/n) == h for n, h in pins.items()) and sha(contract_path) == contract_sha256, 'Native files changed during assessment')
    result.update(native_receipt_sha256=sha(directory/'native-execution.json'), frozen_contract_sha256=contract_sha256,
                  assessor_sha256=sha(__file__), reference_sha256=REFERENCE_SHA,
                  consumed_exports_sha256={n: pins[n] for n in sorted(required)},
                  observed_function_behavior_outside_range='Separate controlled runtime record required; not inferred from final fields',
                  scope='Separate measured-column software interpolation witness; no head field, tensor orientation, process calibration or physical qualification.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--direction', choices=('Z', 'XY'), required=True)
    args = parser.parse_args()
    print(json.dumps(assess(args.directory, args.contract, args.contract_sha256, args.direction), indent=2, sort_keys=True, allow_nan=False))
