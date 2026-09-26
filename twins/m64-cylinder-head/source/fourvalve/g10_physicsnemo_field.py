#!/usr/bin/env python3
"""PhysicsNeMo field pilot on frozen G9 CAD, with held-out mesh and CG correction.

This is supervised coordinate interpolation, NOT a PINN, a geometry optimizer,
a trained hot-head twin, or a replacement for reference FEA. No new CAD is made.
"""
import argparse
import copy
import inspect
import json
from pathlib import Path
import time

import numpy as np
import g8_pilot as g8
import g8_matrix_benchmark as bench
import g9_reference_campaign as g9

CAMPAIGN_SHA = '3a731c1706524f1ce684a4274907beb3781968084de75b832beeaef31c8ac0e7'
NAMES = ('x', 'minus_z')
SEED = 2600


def checked_cases(folder, campaign):
    rows = [r for r in campaign['cases'] if r['case'] == folder.name]
    if len(rows) != 2 or {r['direction'] for r in rows} != set(NAMES):
        raise ValueError('requires the two fresh G9 load cases')
    for row in rows:
        if not row['numerical_crosscheck_passed']:
            raise ValueError('reference algebraic audit failed')
        for name, digest in row['hashes'].items():
            if g8.sha256(folder / name) != digest:
                raise ValueError('reference hash mismatch: ' + name)
    text = (folder / 'x.inp').read_text()
    points, _, support = g9.deck(text)
    for name in NAMES:
        if (folder / (name + '.inp')).read_text().split('*STEP\n')[0] != text.split('*STEP\n')[0]:
            raise ValueError('load cases must share the same geometry and material')
    ids = sorted(points)
    xyz = np.array([points[n] for n in ids])
    fields = [g8.vectors(folder / (name + '.dat'), 'displacements (') for name in NAMES]
    if any(set(u) != set(points) for u in fields):
        raise ValueError('incomplete reference field')
    target = np.concatenate([np.array([u[n] for n in ids]) for u in fields], axis=1)
    return ids, xyz, target, points, support, fields


def field_errors(prediction, reference):
    if prediction.shape != reference.shape or not np.isfinite(prediction).all():
        raise ValueError('invalid predicted field')
    norm = np.linalg.norm(reference)
    maximum = np.max(np.linalg.norm(reference, axis=1))
    if norm <= 0 or maximum <= 0:
        raise ValueError('nonzero reference required')
    return {'relative_nodal_L2': float(np.linalg.norm(prediction-reference)/norm),
            'max_nodal_error_over_max_reference': float(np.max(np.linalg.norm(prediction-reference, axis=1))/maximum)}


def train(folder, campaign, out, steps, max_seconds):
    import torch
    import physicsnemo
    from physicsnemo.models.mlp import FullyConnected
    if physicsnemo.__version__ != '2.2.0' or not torch.cuda.is_available():
        raise ValueError('requires PhysicsNeMo 2.2.0 and a CUDA GPU')
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    ids, xyz, target, _, fixed, _ = checked_cases(folder, campaign)
    origin, length = xyz.min(axis=0), np.ptp(xyz, axis=0).max()
    if not np.allclose([q[2] for n, q in zip(ids, xyz) if n in fixed], origin[2], atol=1e-7):
        raise ValueError('hard displacement condition requires a planar fixed foot')
    scale = np.array([np.max(np.linalg.norm(target[:, j:j+3], axis=1)) for j in (0, 3)]).repeat(3)
    x = torch.tensor((xyz-origin)/length, device='cuda', dtype=torch.float32)
    y = torch.tensor(target/scale, device='cuda', dtype=torch.float32)
    order = np.random.default_rng(SEED).permutation(len(xyz))
    validation = torch.tensor(order[:len(order)//10], device='cuda')
    training = torch.tensor(order[len(order)//10:], device='cuda')
    model = FullyConnected(in_features=3, out_features=6, layer_size=128,
                           num_layers=4, activation_fn='silu').cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    best, state, history = float('inf'), None, []
    begin = time.monotonic()

    def forward(a):
        return model(a) * a[:, 2:3]  # hard u=0 at the fixed foot, not a PDE residual

    for step in range(1, steps+1):
        if time.monotonic()-begin > max_seconds:
            break
        optimizer.param_groups[0]['lr'] = .001 * (.2 ** ((step-1)//max(1, steps//3)))
        index = training[torch.randint(len(training), (4096,), device='cuda')]
        loss = torch.mean((forward(x[index])-y[index])**2)
        if not torch.isfinite(loss):
            raise ValueError('nonfinite training loss')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if step == 1 or step % 200 == 0 or step == steps:
            with torch.no_grad():
                val = torch.mean((forward(x[validation])-y[validation])**2).item()
            if val < best:
                best, state = val, copy.deepcopy(model.state_dict())
            row = {'step': step, 'validation_normalized_MSE': val, 'seconds': time.monotonic()-begin}
            history.append(row)
            print(json.dumps(row), flush=True)
    if state is None:
        raise ValueError('no trained checkpoint')
    model.load_state_dict(state)
    torch.save({'state_dict': state, 'origin_mm': origin, 'length_mm': length,
                'scale_mm': scale, 'seed': SEED}, out/'model.pt')
    torch.cuda.synchronize()
    record = {'physicsnemo': physicsnemo.__version__, 'torch': torch.__version__,
              'cuda': torch.version.cuda, 'gpu': torch.cuda.get_device_name(0),
              'gpu_total_bytes': torch.cuda.get_device_properties(0).total_memory,
              'peak_training_allocated_bytes': torch.cuda.max_memory_allocated(),
              'model_class': 'physicsnemo.models.mlp.FullyConnected', 'seed': SEED,
              'upstream_model_source_sha256': g8.sha256(Path(inspect.getfile(FullyConnected))),
              'model_sha256': g8.sha256(out/'model.pt'), 'parameters': sum(p.numel() for p in model.parameters()),
              'normalization_from_training_mesh_only': True, 'training_nodes': len(training),
              'validation_nodes_same_mesh': len(validation), 'history': history,
              'training_seconds': time.monotonic()-begin}

    def predict(points):
        pieces = []
        with torch.no_grad():
            for i in range(0, len(points), 8192):
                a = torch.tensor((points[i:i+8192]-origin)/length, device='cuda', dtype=torch.float32)
                pieces.append(forward(a).cpu().numpy()*scale)
        return np.concatenate(pieces)
    return predict, record


def run(args):
    if g8.sha256(args.campaign) != CAMPAIGN_SHA:
        raise ValueError('requires the unchanged complete G9 campaign')
    campaign = json.loads(args.campaign.read_text())
    if args.train.name != 'carrier_base_p-2.0' or args.test.name != 'carrier_base_p-1.5':
        raise ValueError('medium-mesh training and fine-mesh holdout are fixed before training')
    args.out.mkdir(exist_ok=False, parents=True)
    predict, training = train(args.train, campaign, args.out, args.steps, args.max_seconds)
    # The fine coordinates AND labels are opened only after checkpoint selection.
    ids, xyz, target, points, support, fields = checked_cases(args.test, campaign)
    begin = time.monotonic()
    prediction = predict(xyz)
    inference_seconds = time.monotonic()-begin
    np.savez_compressed(args.out/'fine-prediction.npz', ids=ids, displacement_mm=prediction)
    matrix, mapping = bench.read_matrix(args.test/'matrix.sti', args.test/'matrix.dof', points, support)
    import cupy as cp
    from cupyx.scipy.sparse import csr_matrix, diags
    from cupyx.scipy.sparse.linalg import cg
    if cp.__version__ != '13.6.0':
        raise ValueError('requires CuPy 13.6.0')
    gpu_matrix = csr_matrix(matrix)
    preconditioner = diags(1/gpu_matrix.diagonal()).tocsr()
    positions = {n: i for i, n in enumerate(ids)}
    rows = []
    for j, name in enumerate(NAMES):
        _, loads, _ = g9.deck((args.test/(name+'.inp')).read_text())
        rhs = g9.rhs_for(mapping, loads)
        pred = prediction[:, 3*j:3*j+3]
        vector = np.array([pred[positions[n], d-1] for n, d in mapping])
        errors = field_errors(pred, target[:, 3*j:3*j+3])
        journals = {}
        for side, sign in (('intake', -1), ('exhaust', 1)):
            selected = [(n, abs(f)) for (n, _), f in loads.items() if points[n][0]*sign > 0]
            total = sum(f for _, f in selected)
            actual = sum((f*np.array(fields[j][n]) for n, f in selected), np.zeros(3))/total
            neural = sum((f*pred[positions[n]] for n, f in selected), np.zeros(3))/total
            journals[side] = {'reference_mm': actual.tolist(), 'prediction_mm': neural.tolist(),
                              'relative_vector_error': float(np.linalg.norm(neural-actual)/np.linalg.norm(actual))}
        row = {'load': name, **errors, 'journals': journals,
               'neural_equation_relative_residual': float(np.linalg.norm(matrix@vector-rhs)/np.linalg.norm(rhs)),
               'raw_field_gate_passed': bool(errors['relative_nodal_L2'] <= .02
                    and errors['max_nodal_error_over_max_reference'] <= .05
                    and max(v['relative_vector_error'] for v in journals.values()) <= .01), 'CG': []}
        gpu_rhs = cp.asarray(rhs)
        # ABBA order records first-use effects rather than hiding them in a speedup.
        initial_guess = cp.asarray(vector)
        for label, initial in (('zero', None), ('physicsnemo', initial_guess),
                               ('physicsnemo', initial_guess), ('zero', None)):
            counter = [0]
            start = time.monotonic()
            def step(_):
                counter[0] += 1
                if time.monotonic()-start > 300:
                    raise TimeoutError('CG exceeds bounded runtime')
            cp.cuda.Stream.null.synchronize()
            u, info = cg(gpu_matrix, gpu_rhs, x0=initial, tol=1e-10, atol=0., maxiter=20000,
                         M=preconditioner, callback=step)
            cp.cuda.Stream.null.synchronize()
            seconds = time.monotonic()-start
            u = cp.asnumpy(u)
            residual = float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
            diff = bench.comparison(matrix, rhs, mapping, u, fields[j])
            passed = bool(info == 0 and residual <= 1e-8 and diff['max_nodal_difference_over_max_reference_U'] <= 1e-4)
            row['CG'].append({'initial_guess': label, 'iterations': counter[0], 'solve_seconds': seconds,
                              'relative_residual': residual, 'passed': passed, **diff})
        rows.append(row)
    report = {'classification': 'fixed_geometry_supervised_field_pilot_not_geometry_optimization',
              'source_sha256': g8.sha256(Path(__file__)), 'campaign_sha256': CAMPAIGN_SHA,
              'training': training, 'heldout_nodes': len(ids), 'inference_seconds': inference_seconds,
              'cases': rows, 'geometry_changed': False, 'manufacturing_authorized': False,
              'engine_start_authorized': False, 'thermal_or_strength_qualified': False,
              'geometry_surrogate_qualified': False,
              'thresholds': {'nodal_L2': .02, 'max_nodal_error': .05, 'journal_vector': .01,
                             'corrected_equation_residual': 1e-8, 'corrected_nodal_error': 1e-4},
              'all_corrected_solutions_passed': all(c['passed'] for r in rows for c in r['CG'])}
    with (args.out/'report.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(report), flush=True)
    return 0 if report['all_corrected_solutions_passed'] else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for option in ('train', 'test', 'campaign', 'out'):
        ap.add_argument('--'+option, type=Path, required=True)
    ap.add_argument('--steps', type=int, default=10000)
    ap.add_argument('--max-seconds', type=int, default=900)
    args = ap.parse_args()
    if not 1 <= args.steps <= 10000 or not 1 <= args.max_seconds <= 900:
        ap.error('training must be bounded to 10000 steps and 900 seconds')
    raise SystemExit(run(args))
