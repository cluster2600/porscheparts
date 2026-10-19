"""Locate retained linear C3D10 stress maxima; no solve, remesh or CAD import."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise ValueError(message)


def gauss_point(points, ip):
    """Same affine four-point location/order as retained audit_root_resolution.py."""
    require(type(ip) is int and 1 <= ip <= 4, 'Invalid one-based Gauss index')
    require(len(points) == 10 and all(len(p) == 3 for p in points), 'Expected ten XYZ nodes')
    require(all(math.isfinite(v) for p in points for v in p), 'Nonfinite element coordinate')
    pairs = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    require(all(abs(points[k + 4][d] - (points[i][d] + points[j][d]) / 2) <= 1e-10
                for k, (i, j) in enumerate(pairs) for d in range(3)),
            'Curved T10 midsides require a different location map')
    a, b = (5 + 3 * math.sqrt(5)) / 20, (5 - math.sqrt(5)) / 20
    bary = [a if k == ip - 1 else b for k in range(4)]
    return [sum(bary[k] * points[k][d] for k in range(4)) for d in range(3)]


def corner_measure(points):
    corners = points[:4]
    lengths = sorted(math.dist(corners[i], corners[j]) for i in range(4) for j in range(i))
    require(len(lengths) == 6 and lengths[0] > 0, 'Degenerate tetrahedron edges')
    return dict(bounds_mm=[[min(p[d] for p in corners) for d in range(3)],
                           [max(p[d] for p in corners) for d in range(3)]],
                six_corner_edge_lengths_mm=lengths,
                measured_h_mm=lengths[-1], proposed_half_h_mm=lengths[-1] / 2,
                h_definition='Maximum of the six actual corner edges of this peak element; not global mesh label')


def verified_plan(plan):
    require(plan['schema'] == 'bounded-webs-retained-peak-IP-plan-1', 'Unexpected plan schema')
    require(all(type(plan[k]) is int for k in ('outer_wall_seconds', 'inner_wall_seconds', 'CPU_seconds',
                                             'CPU_hard_seconds', 'actual_workers', 'threads')), 'Integer bounds required')
    require((plan['outer_wall_seconds'], plan['inner_wall_seconds'], plan['CPU_seconds'],
             plan['CPU_hard_seconds'], plan['actual_workers'], plan['threads']) == (120, 90, 80, 81, 0, 1),
            'Unexpected resource bounds')
    require(plan['cases'] == [dict(mesh=m, case=c) for m in (9, 7)
                             for c in ('combined-rigid-static', 'combined-spring-1000-static')],
            'Only four retained linear cases are authorized')
    for name in plan['files_sha256']:
        path = ROOT / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and path.is_file(), 'Invalid input path')
        require(not any(p.is_symlink() for p in [path, *path.parents]), 'Symlink input refused')
    actual = {name: sha(ROOT / name) for name in plan['files_sha256']}
    require(actual == plan['files_sha256'], 'A retained input or source changed')
    checkpoint = json.loads((ROOT / plan['runtime_checkpoint']).read_text())
    require(checkpoint['runtime_unchanged'] and checkpoint['runtime_before'] == checkpoint['runtime_after'],
            'Expected unchanged runtime authority')
    encoded = json.dumps(checkpoint['runtime_before'], sort_keys=True, separators=(',', ':')).encode()
    require(hashlib.sha256(encoded).hexdigest() == plan['runtime_expected_sha256'], 'Runtime authority differs')
    output = HERE / 'output-001'
    require(not output.exists() and not any(p.is_symlink() for p in [output, *output.parents]), 'Output must be fresh')
    return actual, checkpoint['runtime_before']


def preflight():
    plan_hash = sha(HERE / 'plan.json')
    plan = json.loads((HERE / 'plan.json').read_text())
    before, _ = verified_plan(plan)
    require(sha(HERE / 'plan.json') == plan_hash, 'Plan changed during preflight')
    result = dict(status='prepared_pending_root_GO_no_result_fields_loaded', plan_sha256=plan_hash,
                  files_sha256=before, scientific_imports=False, result_fields_loaded=False,
                  FEA_started=False, mesh_generated=False)
    write(HERE / 'preflight.json', result)
    return result


def locate_case(folder, case, energy, simulation, np):
    receipt = json.loads((folder / (case + '.json')).read_text())
    meta = json.loads((folder / 'mesh.json').read_text())
    require(meta['element_order'] == 2 and meta['straight_midsides'], 'Only affine C3D10 is authorized')
    cad_source = _verify_BREP_binding(folder, meta)
    require(receipt['name'] == case and receipt['procedure'] == 'static', 'Wrong retained case')
    require(receipt['input_sha256'] == sha(folder / (case + '.inp')) and
            receipt['mesh_sha256'] == sha(folder / 'mesh.inp'), 'Deck/mesh receipt differs')
    tags, xyz, eids, conn = energy.read_mesh(folder / 'mesh.inp')
    with np.load(folder / 'mesh.npz', allow_pickle=False) as mesh:
        require(np.array_equal(tags, mesh['tags']) and np.allclose(xyz, mesh['xyz'], rtol=0, atol=1e-10), 'Mesh NPZ differs')
        ends = np.unique(np.concatenate([mesh['end0'], mesh['end1']]))
    fields = energy.dat_fields(folder / (case + '.dat'))
    stress = fields['stresses']
    expected = np.column_stack([np.repeat(eids, 4), np.tile(np.arange(1, 5), len(eids))])
    require(stress.shape == (len(eids) * 4, 8) and np.array_equal(stress[:, :2], expected), 'Missing/reordered DAT Gauss rows')
    require(np.isfinite(stress).all(), 'Nonfinite DAT stresses')
    vm = simulation.von_mises(stress[:, 2:])
    with np.load(folder / (case + '.npz'), allow_pickle=False) as result:
        require(np.array_equal(result['tags'], tags) and np.allclose(result['xyz'], xyz, rtol=0, atol=1e-10), 'Result mesh differs')
        require(np.array_equal(result['element_ids'], expected[:, 0]) and np.array_equal(result['stress'], stress[:, 2:]), 'Result stress differs from DAT')
        require(np.array_equal(result['VM'], vm), 'Retained/recomputed VM differs')
        require(np.array_equal(fields['displacements'][:, 0], tags) and
                np.array_equal(fields['displacements'][:, 1:], result['displacement']), 'Displacement DAT/NPZ differs')
        require(np.isfinite(result['force']).all() and result['force'].shape == xyz.shape, 'Invalid force array')
        force = result['force'].copy()
        require(np.array_equal(np.sort(result['fixed']), ends), 'Retained end-node roster differs')
    require(float(vm.max()) == receipt['integration_point_VM_max_MPa'], 'Retained maximum differs')
    require(int(expected[int(vm.argmax()), 0]) == receipt['VM_peak_element'], 'Retained first maximum element differs')
    deck = energy.blocks(folder / (case + '.inp'))
    require(sum(k.startswith('*STEP') for k, _ in deck) == 1 and not any('NLGEOM' in k for k, _ in deck), 'Wrong procedure')
    boundaries = [rows for key, rows in deck if key == '*BOUNDARY']
    rigid = case == 'combined-rigid-static'
    require(boundaries == ([['FIXED,1,3']] if rigid else []), 'Unexpected displacement BC')
    spring_nodes = np.array([int(row.split(',')[1]) for key, rows in deck
                             if key.startswith('*ELEMENT,TYPE=SPRING1,') for row in rows], dtype=np.int64)
    require((not len(spring_nodes)) if rigid else np.array_equal(np.unique(spring_nodes), ends), 'Spring node identity differs')
    cload = np.zeros_like(force)
    for key, rows in deck:
        if key == '*CLOAD':
            for row in rows:
                node, dof, value = row.split(','); index = int(np.searchsorted(tags, int(node)))
                require(index < len(tags) and tags[index] == int(node) and int(dof) in (1, 2, 3), 'Unknown load node/dof')
                cload[index, int(dof) - 1] += float(value)
    require(np.allclose(force, cload, rtol=1e-10, atol=1e-9), 'CLOAD/force differs')
    load_ids = tags[np.any(cload != 0, axis=1)]
    require(len(load_ids) > 0, 'No loaded nodes')
    def nearest(point, ids):
        if not len(ids):
            return None
        ids = np.unique(ids); positions = xyz[np.searchsorted(tags, ids)]
        distances = np.linalg.norm(positions - point, axis=1); index = int(np.argmin(distances))
        return dict(node_id=int(ids[index]), undeformed_xyz_mm=positions[index].tolist(), distance_mm=float(distances[index]),
                    scope='Euclidean distance to the retained discrete node set only; not distance to a BC/load surface')
    peaks = []
    for row in np.flatnonzero(vm == vm.max()):
        element_index, ip = divmod(int(row), 4); points = xyz[conn[element_index]].tolist()
        require(np.linalg.det(np.asarray(points[1:4]) - points[0]) > 0, 'Nonpositive peak-element Jacobian')
        point = gauss_point(points, ip + 1)
        peaks.append(dict(DAT_row_zero_based=int(row), element_index_zero_based=element_index,
            element_id=int(eids[element_index]), IP_one_based=ip + 1,
            reference_undeformed_IP_xyz_mm=point, VM_MPa=float(vm[row]),
            element_corner_centroid_mm=np.mean(points[:4], axis=0).tolist(),
            nearest_prescribed_displacement_node=nearest(point, ends if rigid else []),
            nearest_grounded_spring_node=nearest(point, [] if rigid else spring_nodes),
            nearest_applied_load_node=nearest(point, load_ids), corner_measure=corner_measure(points)))
    return dict(mesh=folder.name, case=case, CAD_source=cad_source, C3D10_elements=len(eids), nodes=len(tags),
        maximum_VM_MPa=float(vm.max()), all_global_maximum_ties=peaks, maximum_ties=len(peaks),
        constrained_node_count=len(ends) if rigid else 0, grounded_spring_node_count=0 if rigid else len(ends),
        loaded_node_count=len(load_ids), no_peak_excluded=True, coordinate_scope='Reference coordinates from solver mesh INP',
        quadrature='Official CCX2.21 gauss3d5 / straight-midside C3D10; IP1..4 have barycentric a at corners1..4')


def run(expected_preflight):
    started = time.monotonic(); plan_hash = sha(HERE / 'plan.json')
    plan = json.loads((HERE / 'plan.json').read_text()); before, expected_runtime = verified_plan(plan)
    require(sha(HERE / 'preflight.json') == expected_preflight, 'Preflight identity differs')
    prior = json.loads((HERE / 'preflight.json').read_text())
    require(prior['plan_sha256'] == plan_hash and prior['files_sha256'] == before, 'Preflight bindings differ')
    require(os.getpriority(os.PRIO_PROCESS, 0) == 10 and all(os.environ.get(k) == '1' for k in
            ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')), 'nice10 / one thread required')
    output = HERE / 'output-001'; output.mkdir()
    result = dict(status='incomplete', FEA_started=False, mesh_generated=False, cases=[], plan_sha256=plan_hash,
                  files_sha256_before=before, no_strength_allowable_added=True, global_admission=False)
    old = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('90s postprocess budget')))
    signal.setitimer(signal.ITIMER_REAL, 90); resource.setrlimit(resource.RLIMIT_CPU, (80, 81))
    code = 1; runtime = None
    try:
        identity = load('_peak_runtime_identity', ROOT / plan['runtime_source'])
        runtime = identity.runtime_identity(); write(output / 'runtime-before.json', runtime)
        require(runtime == expected_runtime, 'Scientific runtime differs from C22')
        import numpy as np
        energy = load('_peak_energy_reader', ROOT / plan['energy_source'])
        simulation = load('_peak_retained_simulation', ROOT / plan['simulation_source'])
        for case in plan['cases']:
            row = locate_case(ROOT / plan['CAD_directory'] / ('mesh-' + str(case['mesh'])), case['case'], energy, simulation, np)
            result['cases'].append(row); write(output / (row['mesh'] + '-' + row['case'] + '.json'), row)
        result['status'] = 'four_retained_linear_cases_located_no_new_solve'; code = 0
    except BaseException as error:
        result['error'] = dict(type=type(error).__name__, message=str(error))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)
        if runtime is not None:
            try:
                after_runtime = identity.runtime_identity(); write(output / 'runtime-after.json', after_runtime)
                result['runtime_unchanged'] = after_runtime == runtime == expected_runtime
            except BaseException as error:
                result['runtime_error'] = dict(type=type(error).__name__, message=str(error)); code = 1
        result['files_sha256_after'] = {name: sha(ROOT / name) for name in before}
        result['inputs_unchanged'] = before == result['files_sha256_after'] and sha(HERE / 'plan.json') == plan_hash
        if not result.get('runtime_unchanged') or not result['inputs_unchanged']:
            result['status'] = 'refused'; code = 1
        result['wall_seconds'] = time.monotonic() - started
        result['returncode'] = code; write(output / 'assessment.json', result)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'run']); parser.add_argument('preflight_sha256', nargs='?')
    args = parser.parse_args()
    if args.mode == 'preflight':
        preflight()
    else:
        raise SystemExit(run(args.preflight_sha256))
