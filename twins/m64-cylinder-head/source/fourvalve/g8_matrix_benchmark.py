#!/usr/bin/env python3
"""Same G8 stiffness/RHS, CPU or CUDA FP64 CG; not a full GPU FEA solver."""
import argparse
import json
from pathlib import Path
import platform
import time

import numpy as np
import g8_pilot as g8
from g8_iterative_retry import deck_data


def inputs(case):
    receipt = json.loads((g8.REPO / 'twins/m64-cylinder-head/evidence/g8-carrier-pilot-20260925/direct.partial.json').read_text())
    fingerprint = g8.sha256(case / 'x.inp')
    records = [r for r in receipt['cases'] if r['files_sha256'].get('x.inp') == fingerprint]
    if len(records) != 1 or records[0]['files_sha256']['x.dat'] != g8.sha256(case / 'x.dat'):
        raise ValueError('requires an unchanged G8 deck and its direct reference')
    text = (case / 'x.inp').read_text()
    points, loads = deck_data(text)
    ref = g8.vectors(case / 'x.dat', 'displacements (')
    support = g8.vectors(case / 'x.dat', 'forces (')
    if set(ref) != set(points) or set(support).intersection(loads):
        raise ValueError('reference node mismatch or load on support')
    if text.count('*BOUNDARY\nSUPPORT,1,3\n') != 1:
        raise ValueError('only the G8 homogeneous fixed support is supported')
    return text, points, loads, ref, support


def export_deck(case, output):
    text, *_ = inputs(case)
    # Density is required for the frequency exporter; its mass matrix is unused.
    # With no preload/PERTURBATION, density does not change elastic stiffness.
    head = text.split('*STEP\n')[0]
    head = head.replace('*SOLID SECTION', '*DENSITY\n2.7e-9\n*SOLID SECTION')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'matrix.inp').write_text(head + '*BOUNDARY\nSUPPORT,1,3\n*STEP\n'
                                     '*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')


def read_matrix(stiffness, dofs, points, support):
    from scipy.sparse import coo_matrix, diags
    mapping = [tuple(map(int, line.strip().split('.'))) for line in dofs.read_text().splitlines()]
    expected = {(n, d) for n in points if n not in support for d in (1, 2, 3)}
    if len(mapping) != len(expected) or set(mapping) != expected:
        raise ValueError('DOF map must contain every free translation exactly once')
    data = np.loadtxt(stiffness, dtype=[('r', np.int64), ('c', np.int64), ('v', np.float64)], ndmin=1)
    r, c, v = data['r'] - 1, data['c'] - 1, data['v']
    size = len(mapping)
    if (not len(data) or not np.isfinite(v).all() or min(r.min(), c.min()) < 0
            or max(r.max(), c.max()) >= size or not (np.all(r <= c) or np.all(c <= r))):
        raise ValueError('invalid triangular stiffness entries')
    half = coo_matrix((v, (r, c)), shape=(size, size)).tocsr()
    if half.nnz != len(v) or np.count_nonzero(r == c) != size or np.any(half.diagonal() <= 0):
        raise ValueError('duplicate entries or missing/nonpositive diagonal')
    return half + half.T - diags(half.diagonal()), mapping


def solve(matrix, rhs, backend, max_seconds=300):
    start = time.monotonic()
    if backend == 'cpu':
        import scipy
        from scipy.sparse import diags
        from scipy.sparse.linalg import cg
        xp, sparse_diags = np, diags
        versions = {'numpy': np.__version__, 'scipy': scipy.__version__}
        tolerance = {'rtol': 1e-10}
        sync = lambda: None
    else:
        import cupy as xp
        from cupyx.scipy.sparse import csr_matrix, diags as sparse_diags
        from cupyx.scipy.sparse.linalg import cg
        device = xp.cuda.runtime.getDeviceProperties(0)
        versions = {'cupy': xp.__version__, 'cuda_runtime': xp.cuda.runtime.runtimeGetVersion(),
                    'gpu': device['name'].decode(), 'gpu_total_memory_bytes': device['totalGlobalMem']}
        if xp.__version__ != '13.6.0':
            raise ValueError('CUDA benchmark requires pinned CuPy 13.6.0')
        tolerance = {'tol': 1e-10}
        matrix, rhs = csr_matrix(matrix), xp.asarray(rhs)
        sync = xp.cuda.Stream.null.synchronize
    # ponytail: Jacobi only; qualify a stronger preconditioner if iteration cost dominates.
    preconditioner = sparse_diags(1 / matrix.diagonal()).tocsr()
    sync()
    setup_seconds = time.monotonic() - start
    iterations = 0

    def step(_):
        nonlocal iterations
        iterations += 1
        if time.monotonic() - start > max_seconds:
            raise TimeoutError('bounded CG runtime exceeded')

    begin = time.monotonic()
    u, info = cg(matrix, rhs, **tolerance, atol=0., maxiter=20000, M=preconditioner, callback=step)
    sync()
    seconds = time.monotonic() - begin
    if backend != 'cpu':
        u = xp.asnumpy(u)
    return u, {'backend': backend, 'versions': versions, 'iterations': iterations, 'info': int(info),
               'setup_seconds': setup_seconds, 'solve_seconds': seconds,
               'setup_and_solve_seconds': setup_seconds + seconds, 'dtype': 'float64'}


def comparison(matrix, rhs, mapping, u, reference):
    printed = np.array([reference[n][d-1] for n, d in mapping])
    errors = {n: np.zeros(3) for n in reference}
    for (n, d), value in zip(mapping, u - printed):
        errors[n][d-1] = value
    error = max(np.linalg.norm(v) for v in errors.values()) / max(np.linalg.norm(v) for v in reference.values())
    residual = np.linalg.norm(matrix @ printed - rhs) / np.linalg.norm(rhs)
    # DAT prints seven significant digits. This deliberately conservative bound
    # prevents confusing text-output rounding with algebraic-solver error.
    bound = np.linalg.norm(abs(matrix) @ (abs(printed) * 1e-6)) / np.linalg.norm(rhs)
    return {'max_nodal_difference_over_max_reference_U': float(error),
            'printed_dat_relative_residual': float(residual),
            'printed_dat_rounding_residual_bound': float(bound)}


def run(case, matrix_dir, backend, output, comparisons=()):
    _, points, loads, ref, support = inputs(case)
    matrix, mapping = read_matrix(matrix_dir / 'matrix.sti', matrix_dir / 'matrix.dof', points, support)
    rhs = np.array([loads.get(n, 0.) if d == 1 else 0. for n, d in mapping], dtype=np.float64)
    if not np.isclose(rhs.sum(), sum(loads.values()), rtol=1e-12):
        raise ValueError('load mapping lost force')
    u, result = solve(matrix, rhs, backend)
    relative_residual = float(np.linalg.norm(matrix @ u - rhs) / np.linalg.norm(rhs))
    original = comparison(matrix, rhs, mapping, u, ref)
    error = original['max_nodal_difference_over_max_reference_U']
    accepted = bool(result['info'] == 0 and np.isfinite(u).all() and np.isfinite(error)
                    and relative_residual <= 1e-8 and error <= 1e-4)
    result.update(classification='G8_reduced_stiffness_linear_solver_benchmark_only',
                  accepted=accepted, manufacturing_authorized=False, engine_start_authorized=False,
                  reactions_and_stresses_recomputed=False, nodes=len(points), free_dofs=len(mapping),
                  matrix_nnz=matrix.nnz, relative_residual=relative_residual,
                  max_nodal_difference_over_max_reference_U=float(error), host=platform.machine(),
                  original_reference=original, additional_comparisons=[],
                  thresholds={'relative_residual': 1e-8, 'max_nodal_difference_over_max_reference_U': 1e-4},
                  hashes={'source': g8.sha256(Path(__file__)), 'deck': g8.sha256(case / 'x.inp'),
                          'reference_dat': g8.sha256(case / 'x.dat'),
                          'matrix_deck': g8.sha256(matrix_dir / 'matrix.inp'),
                          'stiffness': g8.sha256(matrix_dir / 'matrix.sti'),
                          'dof_map': g8.sha256(matrix_dir / 'matrix.dof')})
    # Additional observations NEVER replace the original gate or authorize GPU spend.
    for path in comparisons:
        other = g8.vectors(path, 'displacements (')
        if set(other) != set(points):
            raise ValueError('additional comparison node mismatch')
        result['additional_comparisons'].append({'file': path.name, 'sha256': g8.sha256(path),
                                                **comparison(matrix, rhs, mapping, u, other)})
    # Raw geometry/results stay in ignored work/, never the public evidence directory.
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result, allow_nan=False), flush=True)
    return 0 if accepted else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('matrix_dir', type=Path)
    parser.add_argument('--backend', choices=('cpu', 'cuda'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--comparison-dat', action='append', type=Path, default=[])
    args = parser.parse_args()
    if args.backend:
        if args.output is None or args.output.exists():
            parser.error('--output must be a new file')
        raise SystemExit(run(args.case, args.matrix_dir, args.backend, args.output, args.comparison_dat))
    export_deck(args.case, args.matrix_dir)
