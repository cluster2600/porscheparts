"""HELD fixed native005 END181 calculation; no CLI, launch, or result authority."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types

ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
NATIVE = ROOT / 'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001'
OUTPUT = ROOT / 'work/962-engineering/rich3-END181-equilibrium-execution-001'
RUNTIME = {'path': 'work/962-engineering/native005-raw-displacement-decoder-runtime-root-001/acceptance.json', 'sha256': '5dbf28e11b6fcd7c4770bb40a042a58735ab98485a592b857e3293eb5dab8376', 'bytes': 9673}
ASSESSOR = {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-assessor-prep-001/assess.py', 'sha256': 'aa7ee403a0a3078df58410815f2b613aaeb9634bd14bc9c90517ce00cec7f2d5', 'bytes': 46645}
POLICY = {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-assessor-prep-001/POLICY.json', 'sha256': 'a87df89f84706b36c0b665c0e9eac928e3c9b2b45f5a2921442b2d6403f4a638', 'bytes': 5013}
LIMITS = {'temperature_K': 1e-10, 'displacement_m': 1e-12, 'QP_coordinate_m': 2e-13, 'strain': 1e-10, 'stress_Pa': .1, 'force_N': 1e-7, 'moment_Nm': 1e-7}
RAW = {
    'thermoelastic.e-s002': {'path': str(NATIVE.relative_to(ROOT) / 'thermoelastic.e-s002'), 'sha256': '8730b734dbbe8553ef1e47526ba8eafd3989323649fa564a4fa571e21dae3a83', 'bytes': 3189268},
    'thermoelastic_end_0181.csv': {'path': str(NATIVE.relative_to(ROOT) / 'thermoelastic_end_0181.csv'), 'sha256': '05d32ff636750d00a4a776c3749ccbe980caae21acd4d5e65952edf2acc2d7f9', 'bytes': 71939},
    'thermoelastic_end_fields_0181.csv': {'path': str(NATIVE.relative_to(ROOT) / 'thermoelastic_end_fields_0181.csv'), 'sha256': '80fcb0e6ea6e6f6f6bf259c29a7c4c205d5f4c337925ff547f9e7b48c52807c0', 'bytes': 1370125},
    'thermoelastic_begin_0080.csv': {'path': str(NATIVE.relative_to(ROOT) / 'thermoelastic_begin_0080.csv'), 'sha256': 'f54de6aafef6e8c418fcc8887f3b0ac359e3bb22d8a5de88b35be1e15bbef405', 'bytes': 28087},
    'thermoelastic_reference_begin_0080.csv': {'path': str(NATIVE.relative_to(ROOT) / 'thermoelastic_reference_begin_0080.csv'), 'sha256': 'ea69e318eca4878c7f857a18864cc5ec96206dfc60bdea99cde25b98e0624ea5', 'bytes': 4816},
    'transfer-manifest.json': {'path': str(NATIVE.relative_to(ROOT) / 'transfer-manifest.json'), 'sha256': 'c774e62c67e16c29dc024b8cc8e6641570e316265960e58cd7170827f8cecd06', 'bytes': 130095},
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def bits(xyz):
    return struct.pack('<3d', *xyz)


def number(value):
    need(type(value) in (str, float, int), 'Explicit finite numeric scalar required')
    out = float(value)
    need(math.isfinite(out), 'Nonfinite scalar refused')
    return out


class DiagnosticAudit:
    """Record unchanged scalar gates; exceeding one never means field acceptance."""
    def __init__(self, policy):
        self.policy = policy
        self.counts = {}
        self.maximum = {}
        self.exceedances = []
        self.context = None

    def close(self, a, b, unit):
        a, b = number(a), number(b)
        error = abs(a - b)
        self.counts[unit] = self.counts.get(unit, 0) + 1
        observation = dict(unit=unit, value=a, reference=b, absolute_error=error,
                           unchanged_limit=self.policy[unit], context=self.context)
        if unit not in self.maximum or error > self.maximum[unit]['absolute_error']:
            self.maximum[unit] = observation
        if not error <= self.policy[unit]:
            self.exceedances.append(observation)


def vector_rows(values, active, constraints, rowset):
    return [[values[tag][j] if rowset == 'all' or ((tag, j) in constraints) == (rowset == 'constrained') else 0.
             for j in range(3)] for tag in sorted(active)]


def resultants(values, geometry, active, constraints):
    out = {}
    for rowset in ('constrained', 'free', 'all'):
        force_rows = vector_rows(values, active, constraints, rowset)
        components = []
        for j in range(3):
            force_sum = math.fsum(v[j] for v in force_rows)
            moment_sum = math.fsum(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3] for n, v in zip(sorted(active), force_rows))
            components.append(dict(component=j, force_N=force_sum, force_binary64_hex=force_sum.hex(),
                moment_Nm=moment_sum, moment_binary64_hex=moment_sum.hex(),
                force_L1_N=math.fsum(abs(v[j]) for v in force_rows),
                force_max_abs_term_N=max(abs(v[j]) for v in force_rows),
                moment_L1_Nm=math.fsum(abs(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3]) for n, v in zip(sorted(active), force_rows)),
                original_force_limit_N=1e-7, original_moment_limit_Nm=1e-7,
                force_exceeds_original_gate=not (abs(force_sum - 0.) <= 1e-7),
                moment_exceeds_original_gate=not (abs(moment_sum - 0.) <= 1e-7)))
        out[rowset] = components
    return out


def checked_bytes(pin):
    path = ROOT / pin['path']
    need(path.is_file() and not path.is_symlink() and path.resolve() == path, 'Fixed regular canonical input required')
    need(path.stat().st_size == pin['bytes'], 'Fixed input byte count changed')
    raw = path.read_bytes()
    need(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'], 'Fixed input identity changed')
    return raw


def calculate_current_end181(assessor):
    """Called once only by a separately reviewed/admitted fixed offline caller.

    Caller must load exact ASSESSOR bytes in a fresh ordinary module namespace,
    bind this source and manifest externally, supervise one process, retain
    complete output/traceback, and independently verify final input/runtime pins.
    This callable creates no directory/file, subprocess, runtime query, or solver.
    """
    source_before = checked_bytes(ASSESSOR)
    need(Path(assessor.__file__).resolve() == ROOT / ASSESSOR['path'], 'Fixed assessor module path required')
    need(all(callable(getattr(assessor, name, None)) for name in ('read_exodus', 'rows', 'integer', 'node_sample',
         'ordered_hex', 'hex_rule', 'quadrature_sample', 'support_masks', 'field_phase')), 'Existing assessor functions required')
    policy_before = checked_bytes(POLICY)
    policy = json.loads(policy_before)['absolute_SI_limits']
    need(policy == LIMITS, 'All seven original absolute SI thresholds must be unchanged')
    payloads = {name: checked_bytes(pin) for name, pin in RAW.items()}
    transfer = json.loads(payloads['transfer-manifest.json'])
    geometry = {row['source_node_id']: tuple(row['coordinates_m']) for row in transfer['node_rows']}
    need(len(geometry) == len(transfer['node_rows']) == 425 and set(geometry) == set(range(425)) and all(type(n) is int for n in geometry)
         and all(len(p) == 3 and all(type(x) is float and math.isfinite(x) for x in p) for p in geometry.values())
         and len(set(map(bits, geometry.values()))) == 425, 'Complete typed425 independent source coordinate rows required')
    mesh = assessor.read_exodus(NATIVE / 'thermoelastic.e-s002')
    need(set(mesh['nodes']) == set(geometry) and all(bits(mesh['nodes'][n]) == bits(geometry[n]) for n in geometry),
         'Complete same-run source ID and coordinate-word join required')
    cells = mesh['cells']
    need(len(cells) == 256, 'All256 ordered native HEX8 cells required')
    boxes = set()
    for tag, conn in cells.items():
        assessor.ordered_hex([geometry[n] for n in conn])
        assessor.hex_rule([geometry[n] for n in conn])
        box = tuple(min(geometry[n][j] for n in conn) for j in range(3))
        need(box not in boxes, 'Duplicate native HEX8 grid cell refused')
        boxes.add(box)
    need(boxes == {(i / 8, j / 4, k / 4) for i in range(16) for j in range(4) for k in range(4)},
         'Complete original256 Cartesian HEX8 grid bijection required')
    matches = [index for index, value in enumerate(mesh['times']) if round(value * 400) == 181 and abs(value - 181 / 400) <= 5e-13]
    need(len(matches) == 1, 'Exactly one original END181 selected-member time association required')
    ti = matches[0]
    old_nodes = {tag for tag, point in geometry.items() if point[0] <= 1.}
    born_nodes = {tag for tag, point in geometry.items() if point[0] >= 1.}
    shared = old_nodes & born_nodes
    old_cells = {tag for tag, conn in cells.items() if max(geometry[n][0] for n in conn) <= 1.}
    need((len(old_nodes), len(born_nodes), len(shared), len(old_cells)) == (225, 225, 25, 128), 'Original old/born/shared partition required')
    need(shared == {r['source_node_id'] for r in transfer['node_rows'] if r['shared'] is True}, 'Exact declared shared25 IDs required')
    statuses = dict(zip(mesh['block_ids'], mesh['block_status']))
    need(all(mesh['blocks'][tag] == (2 if tag in old_cells else 3) and statuses[mesh['blocks'][tag]] == 1 for tag in cells),
         'All256 active END181 old2/born3 block memberships required')
    audit = DiagnosticAudit(policy)
    born_begin, born_storage = assessor.node_sample(NATIVE / 'thermoelastic_begin_0080.csv', geometry, set(geometry), (*assessor.DISP, 'temperature'), shared)
    reference, reference_storage = assessor.node_sample(NATIVE / 'thermoelastic_reference_begin_0080.csv', geometry, born_nodes, ('born_reference_temperature',))
    born_u = {tag: [born_begin[tag][key] for key in assessor.DISP] for tag in born_nodes}
    birth_T = {tag: reference[tag]['born_reference_temperature'] for tag in born_nodes}
    audit.context = 'own_BEGIN80_born_reference_temperature_vs_own_nodal_temperature'
    for tag in born_nodes:
        audit.close(birth_T[tag], born_begin[tag]['temperature'], 'temperature_K')
    audit.context = 'own_BEGIN80_newborn_displacement_reference'
    for tag in born_nodes - old_nodes:
        for value in born_u[tag]:
            audit.close(value, 0., 'displacement_m')
    nodal, nodal_storage = assessor.node_sample(NATIVE / 'thermoelastic_end_0181.csv', geometry, set(geometry), (*assessor.DISP, 'temperature', *assessor.FORCE), shared)
    constraints, free, released = assessor.support_masks(geometry, set(geometry), 181, 'end')
    need(len(constraints) == 6 and len(free) == 1269 and not released, 'Original END181 six-point expected constraints required')
    audit.context = 'END181_prescribed300K_and_six_constrained_displacements'
    for tag, row in nodal.items():
        audit.close(row['temperature'], 300., 'temperature_K')
        for j in range(3):
            if (tag, j) in constraints:
                audit.close(row[assessor.DISP[j]], 0., 'displacement_m')
    qcoords = {}
    qp = assessor.quadrature_sample(NATIVE / 'thermoelastic_end_fields_0181.csv', geometry, cells, set(cells), qcoords, policy['QP_coordinate_m'])
    need(len(qp) == len(qcoords) == 2048, 'All2048 physical QP associations required')
    forces = {tag: [0.] * 3 for tag in set(geometry)}
    energy = 0.
    computed = {}
    assembly_order = []
    for label, subset, ru, rt in [('old2', old_cells, {n: assessor.ZERO[0] for n in old_nodes}, {n: 400. for n in old_nodes}),
                                  ('born3', set(cells) - old_cells, born_u, birth_T)]:
        subset_nodes = {n for tag in subset for n in cells[tag]}
        ns = {n: nodal[n] for n in subset_nodes}
        all_constrained = {(n, k) for n in subset_nodes for k in range(3)}
        audit.context = 'END181_' + label + '_exact_field_phase'
        f, en, state = assessor.field_phase(audit, geometry, cells, subset, ns, ru, rt, qp, all_constrained)
        for n, values in f.items():
            for k in range(3):
                forces[n][k] += values[k]
        energy += en
        computed.update(state)
        assembly_order.append(dict(region=label, cell_iteration_order=list(subset), node_iteration_order=list(subset_nodes)))
    native_lines = {tag: [] for tag in geometry}
    for line, row in enumerate(assessor.rows(NATIVE / 'thermoelastic_end_0181.csv', ('id', 'x', 'y', 'z', *assessor.DISP, 'temperature', *assessor.FORCE)), 2):
        native_lines[assessor.integer(row['id'])].append(line)
    components = []
    maxima = {}
    native = {tag: [nodal[tag][name] for name in assessor.FORCE] for tag in geometry}
    for tag in sorted(geometry):
        for j in range(3):
            error = abs(native[tag][j] - forces[tag][j])
            constrained = (tag, j) in constraints
            row = dict(source_ID=tag, component=j, constrained=constrained,
                       coordinate_binary64_LE_hex=bits(geometry[tag]).hex(),
                       native_force_N=native[tag][j], native_binary64_hex=native[tag][j].hex(),
                       assembled_force_N=forces[tag][j], assembled_binary64_hex=forces[tag][j].hex(),
                       native_minus_assembled_N=native[tag][j] - forces[tag][j], absolute_error_N=error,
                       original_force_limit_N=policy['force_N'], exceeds_original_force_limit=not error <= policy['force_N'],
                       native_original_CSV_lines=native_lines[tag])
            components.append(row)
            for metric, value in [('native_vs_assembled_' + ('constrained' if constrained else 'free'), error),
                                  ('native_' + ('constrained' if constrained else 'free') + '_absolute_residual', abs(native[tag][j])),
                                  ('assembled_' + ('constrained' if constrained else 'free') + '_absolute_residual', abs(forces[tag][j]))]:
                key = metric + '_component' + str(j)
                if key not in maxima or value > maxima[key]['magnitude_N']:
                    maxima[key] = dict(magnitude_N=value, witness=row)
            audit.context = 'END181_native_vs_assembled_force'
            audit.close(native[tag][j], forces[tag][j], 'force_N')
            if not constrained:
                audit.context = 'END181_independent_free_DOF_residual'
                audit.close(forces[tag][j], 0., 'force_N')
    need(len(components) == 1275, 'All1275 force-component witnesses required')
    native_sums = resultants(native, geometry, set(geometry), constraints)
    assembled_sums = resultants(forces, geometry, set(geometry), constraints)
    aggregate = []
    for field, sums in [('native', native_sums), ('assembled', assembled_sums)]:
        for rowset, axis_rows in sums.items():
            for row in axis_rows:
                for unit, value_key, flag_key in [('force_N', 'force_N', 'force_exceeds_original_gate'), ('moment_Nm', 'moment_Nm', 'moment_exceeds_original_gate')]:
                    aggregate.append(dict(field=field, rowset=rowset, component=row['component'], unit=unit,
                                          value=row[value_key], binary64_hex=row[value_key].hex(),
                                          unchanged_limit=policy[unit], exceeds_original_gate=row[flag_key]))
    native12 = [r for r in aggregate if r['field'] == 'native' and r['rowset'] in ('constrained', 'all')]
    need(len(aggregate) == 36 and len(native12) == 12, 'Complete36 diagnostic and12 native aggregate criteria required')
    need(checked_bytes(ASSESSOR) == source_before and checked_bytes(POLICY) == policy_before, 'Final unchanged source/POLICY required')
    for name, pin in RAW.items():
        need(checked_bytes(pin) == payloads[name], 'Current captured input changed during calculation')
    return dict(schema='962-native005-END181-unchanged-kernel-equilibrium-diagnostic/v1',
                status='COMPLETE_SINGLE_PHASE_DIAGNOSTIC_ONLY', step=181, phase='end', raw_inputs=RAW,
                assessor_source=ASSESSOR, unchanged_POLICY=POLICY, unchanged_seven_absolute_SI_limits=policy,
                selected_geometry_member='thermoelastic.e-s002', selected_END181_time=mesh['times'][ti], selected_END181_time_index=ti,
                selected_END181_time_word_LE=struct.pack('<d', mesh['times'][ti]).hex(),
                geometry_scope='Selected same-run member geometry/block/source IDs only; exported nodal field values are not used for assembly.',
                complete_source_ID_coordinate_binary64_LE_hex={str(tag): bits(geometry[tag]).hex() for tag in sorted(geometry)},
                complete_ordered_HEX8_cells=[dict(source_cell_ID=tag, nodes=conn, block=mesh['blocks'][tag]) for tag, conn in sorted(cells.items())],
                QP_map_count=len(qp), QP_coordinate_tolerance_m=policy['QP_coordinate_m'],
                own_BEGIN80_reference=dict(node_storage=born_storage, reference_storage=reference_storage,
                    born_u_and_Tref=[dict(source_ID=tag, u=born_u[tag], u_hex=[x.hex() for x in born_u[tag]], Tref_K=birth_T[tag], Tref_hex=birth_T[tag].hex()) for tag in sorted(born_nodes)]),
                END181_nodal_storage=nodal_storage, constrained_DOFs=sorted(map(list, constraints)), free_DOF_count=len(free),
                native_resultants=native_sums, independently_assembled_resultants=assembled_sums,
                all36_aggregate_checks=aggregate, original12_native_aggregate_checks=native12,
                aggregate_exceedances=[r for r in aggregate if r['exceeds_original_gate']],
                all1275_native_vs_assembled_component_observations=components, per_component_maxima_and_witnesses=maxima,
                exact_region_assembly_iteration_order=assembly_order, elastic_strain_energy_J=energy,
                unchanged_scalar_gate_observations=dict(counts=audit.counts, maximum=audit.maximum, exceedances=audit.exceedances),
                dt_scaling_role='Ancillary source/build/load-bound instrument observations; not field_phase arguments or invented independent nominal words.',
                native_csv_values_used=True, exported_nodal_fields_used_for_assembly=False,
                F1_SI_force_or_unscaling_inferred=False, live_BC_observed=False,
                original36_checks_and12_historical_failures_preserved=True,
                full_trajectory_or_assessor_main_executed=False, strict_collector_pass_claimed=False,
                convergence_or_cause_established=False, physics_material_LPBF_manufacturing_qualified=False,
                new_simulation_or_native_execution=False, automatic_retry=False)


def main():
    need(len(sys.argv) == 1 and sys.version_info[:3] == (3, 12, 11)
         and sys.flags.isolated == 1 and sys.dont_write_bytecode, 'Fixed no-argument Python3.12.11 -B -I invocation required')
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'Fixed fresh complete-report output required')
    source_before = Path(__file__).read_bytes()
    runtime_before = checked_bytes(RUNTIME)
    selection = json.loads(runtime_before)
    modules = selection['selected_module_records']
    need(len(modules) == 22 and len({r['path'] for r in modules}) == 22
         and sum(r['bytes'] for r in modules) == 11299366, 'Exact existing selected22 decoder runtime required')
    module_bytes = {r['path']: checked_bytes(r) for r in modules}
    import numpy
    import scipy
    from scipy.io import _netcdf
    need(numpy.__version__ == '2.2.6' and scipy.__version__ == '1.17.1'
         and all(str(Path(m.__file__).resolve()) in module_bytes for m in (numpy, scipy, _netcdf)),
         'Selected decoder version/origin mismatch')
    assessor_bytes = checked_bytes(ASSESSOR)
    assessor = types.ModuleType('fixed_native005_END181_assessor')
    assessor.__file__ = str(ROOT / ASSESSOR['path'])
    exec(compile(assessor_bytes, assessor.__file__, 'exec'), assessor.__dict__)
    result = calculate_current_end181(assessor)
    need(checked_bytes(ASSESSOR) == assessor_bytes and checked_bytes(RUNTIME) == runtime_before
         and Path(__file__).read_bytes() == source_before, 'Final source/runtime selection preservation failed')
    for pin in modules:
        need(checked_bytes(pin) == module_bytes[pin['path']], 'Selected runtime module changed')
    result['source'] = dict(path=str(Path(__file__)), sha256=hashlib.sha256(source_before).hexdigest(), bytes=len(source_before))
    result['selected_runtime'] = RUNTIME
    result['selected22_module_records'] = modules
    result['selected_versions'] = dict(python=list(sys.version_info[:3]), numpy=numpy.__version__, scipy=scipy.__version__)
    result['final_source_input_POLICY_and_selected22_pins_exact'] = True
    result['all_scalar_checks_passed'] = not result['unchanged_scalar_gate_observations']['exceedances']
    result['all36_aggregate_checks_passed'] = not result['aggregate_exceedances']
    result['all12_native_aggregate_checks_passed'] = not any(r['exceeds_original_gate'] for r in result['original12_native_aggregate_checks'])
    encoded = (json.dumps(result, indent=2, allow_nan=False) + '\n').encode()
    need(len(encoded) <= 33554432, 'Complete report exceeds unchanged32MiB; refuse without truncation')
    OUTPUT.mkdir()
    with (OUTPUT / 'diagnostic.json').open('xb') as stream:
        stream.write(encoded)
    print(json.dumps(dict(status=result['status'], scalar_counts=result['unchanged_scalar_gate_observations']['counts'],
                          scalar_exceedances=len(result['unchanged_scalar_gate_observations']['exceedances']),
                          diagnostic_aggregate_checks=36, diagnostic_aggregate_exceedances=len(result['aggregate_exceedances']),
                          native_aggregate_checks=12, native_aggregate_exceedances=sum(r['exceeds_original_gate'] for r in result['original12_native_aggregate_checks']),
                          report=dict(path=str(OUTPUT / 'diagnostic.json'), sha256=hashlib.sha256(encoded).hexdigest(), bytes=len(encoded))), allow_nan=False))
    # Completion returns0 even when numerical gates fail; an incomplete operation raises/nonzero.


if __name__ == '__main__':
    main()
