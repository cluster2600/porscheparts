#!/usr/bin/env python3
"""Bounded 3D triangle-area diagnosis; never changes a mesh or prior verdict.

PhysicsNeMo 2.2.0 formula inspected at:
https://github.com/NVIDIA/physicsnemo/blob/v2.2.0/physicsnemo/mesh/geometry/_cell_areas.py
This reproduces its formula in Torch, not a new PhysicsNeMo/CUDA execution.
"""
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path
import time

from audit_surface_gpu import compare, reference, sha

SURFACE_SHA = '9660e54dc3215bbdfd2a2710fff4108e65b2447d5642a0e583c06d86492281b2'


def decimal_areas(vertices, precision):
    """Independent cross/Gram formulas, starting at exact binary64 coordinates."""
    with localcontext() as ctx:
        ctx.prec = precision
        xyz = [[Decimal.from_float(float(x)) for x in row] for row in vertices]
        u, v = ([xyz[i][j]-xyz[0][j] for j in range(3)] for i in (1, 2))
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        cross_area = sum(x*x for x in cross).sqrt()/2
        gram = sum(x*x for x in u)*sum(x*x for x in v)-sum(a*b for a,b in zip(u,v))**2
        if gram < 0:
            raise ValueError('negative_high_precision_Gram_determinant')
        return cross_area, gram.sqrt()/2


def stable_3d_areas(relative_vectors):
    """Narrow float64 cross-product alternative; no installed-library patch."""
    import torch
    if (relative_vectors.dtype != torch.float64 or relative_vectors.ndim != 3
            or tuple(relative_vectors.shape[1:]) != (2, 3)
            or not torch.isfinite(relative_vectors).all()):
        raise ValueError('finite_float64_Nx2x3_vectors_required')
    areas = torch.linalg.vector_norm(torch.linalg.cross(relative_vectors[:,0], relative_vectors[:,1]), dim=-1)/2
    if not torch.isfinite(areas).all() or not (areas > 0).all():
        raise ValueError('strictly_positive_finite_areas_required')
    return areas


def run(mesh, output):
    import numpy as np
    import torch
    if output.exists() or sha(mesh) != SURFACE_SHA:
        raise ValueError('fresh_output_and_exact_surface_required')
    source_sha = sha(__file__)
    start = time.monotonic()
    with np.load(mesh, allow_pickle=False) as data:
        points, triangles = data['points'], data['triangles']
    expected = reference(points, triangles)  # retained shape/dtype/index guards
    if len(triangles) != 94676 or len(points) != 66555:
        raise ValueError('bound_surface_counts_changed')
    torch.set_num_threads(4)
    xyz = points[triangles]
    vectors = torch.from_numpy(xyz[:,1:]-xyz[:,[0]])
    u, v = vectors[:,0], vectors[:,1]
    # Reproduce the documented Lagrange difference-of-products, without a patch.
    gram64 = ((u*u).sum(-1)*(v*v).sum(-1)-(u*v).sum(-1)**2).clamp(min=0).sqrt()/2
    stable64 = stable_3d_areas(vectors).numpy()
    areas80, areas120 = [], []
    max_formula_difference, max_precision_difference = Decimal(0), Decimal(0)
    for vertices in xyz:
        cross80, gram80 = decimal_areas(vertices, 80)
        cross120, gram120 = decimal_areas(vertices, 120)
        if cross120 <= 0:
            raise ValueError('nonpositive_high_precision_area')
        with localcontext() as ctx:
            ctx.prec = 120
            max_formula_difference = max(max_formula_difference, abs(cross80-gram80)/cross120, abs(cross120-gram120)/cross120)
            max_precision_difference = max(max_precision_difference, abs(cross80-cross120)/cross120)
        areas80.append(float(cross80)); areas120.append(float(cross120))
    high = np.array(areas120, dtype=np.float64)
    candidates = {'lagrange_torch_cpu':gram64.numpy(), 'cross_torch_cpu':stable64,
                  'cross_numpy':expected['areas']}
    comparisons = {}
    for name, values in candidates.items():
        row = compare(values, high, 0)
        relative = np.abs(values/high-1)
        row.update(max_relative_error=float(relative.max()), worst_triangle_index=int(relative.argmax()),
                   zero_areas=int((values == 0).sum()))
        comparisons[name] = row
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    arrays_path = output/'area-comparisons-private.npz'
    np.savez(arrays_path, decimal80=np.array(areas80), decimal120=high, **candidates)
    report = {'schema':'m64-triangle-area-precision/v1', 'input_sha256':SURFACE_SHA,
              'source_sha256':source_sha, 'reference_helper_sha256':sha(Path(__file__).resolve().parents[1]/'physicsnemo-mesh/cpu_reference.py'),
              'torch_version':torch.__version__, 'numpy_version':np.__version__,
              'execution':'Mac_CPU_Torch_formula_reproduction_not_PhysicsNeMo_or_CUDA',
              'triangles':len(triangles), 'decimal_precisions':[80,120],
              'decimal_input':'exact_binary64_coordinates_via_Decimal.from_float',
              'max_decimal_formula_relative_difference':str(max_formula_difference),
              'max_decimal_precision_relative_difference':str(max_precision_difference),
              'decimal_reference_agreement':max(max_formula_difference,max_precision_difference)<Decimal('1e-55'),
              'comparisons':comparisons, 'array_sha256':sha(arrays_path),
              'input_and_source_unchanged':sha(mesh)==SURFACE_SHA and sha(__file__)==source_sha,
              'geometry_modified':False, 'previous_GPU_verdict_changed':False,
              'CUDA_alternative_tested':False, 'manufacturing_authorized':False,
              'wall_seconds':time.monotonic()-start}
    report['stable_CPU_alternative_passed'] = (report['decimal_reference_agreement'] and report['input_and_source_unchanged']
                                             and comparisons['cross_torch_cpu']['passed'])
    with (output/'report.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(report, allow_nan=False))
    return 0 if report['stable_CPU_alternative_passed'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.mesh, args.output))
