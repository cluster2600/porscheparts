"""Complete saved assembled-head array census using unchanged retained helpers."""
import ast
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def definitions(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(selected) != len(names) or {n.name for n in selected} != set(names):
        raise ValueError('Complete unchanged retained definitions required')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)


def main():
    path = OUT / 'frozen-contract.json'
    c = json.loads(path.read_text()); initial = sha(path)
    if c['readback_launch_authorized'] is not True or OUT != (ROOT / c['expected_fresh_output']).resolve():
        raise ValueError('Separate reviewed fresh census authority required')
    if (OUT / 'readback-report.json').exists():
        raise ValueError('Existing census preserved')
    if any(c[role] not in c['input_hashes'] for role in ['candidate', 'quality_helper', 'statistics_helper']):
        raise ValueError('Every consumed array/helper role must be explicitly bound')
    def verify():
        for name, digest in c['input_hashes'].items():
            p = Path(name); f = ROOT / p
            if p.is_absolute() or '..' in p.parts or f.is_symlink() or not f.is_file() or sha(f) != digest:
                raise ValueError('Bound census input changed: ' + name)
        if sha(sys.executable) != c['runtime']['python_executable_sha256'] or sha(__file__) != c['reader_sha256'] or sha(OUT / 'run_readback.py') != c['runner_sha256']:
            raise ValueError('Bound reader/runtime changed')
    verify()
    if platform.machine() != 'arm64' or np.__version__ != c['runtime']['numpy_version']:
        raise ValueError('Retained ARM/NumPy identity required')
    namespace = {'np': np, 'struct': struct, 'math': math, 'hashlib': hashlib, 'CHUNK': 65536}
    definitions(ROOT / c['quality_helper'], ['read', 'qualities'], namespace)
    definitions(ROOT / c['statistics_helper'], ['array_sha', 'plane_classes', 'surface_stats'], namespace)
    started = time.monotonic(); p, f = namespace['read'](ROOT / c['candidate'])
    if (len(p), len(f)) != (871731, 1743878):
        raise ValueError('Exact stopped assembly counts required')
    stats = namespace['surface_stats'](p, f, namespace['qualities'](p, f))
    result = dict(status='complete_assembled_array_census_only', candidate=stats,
                  necessary_quality_gate_passed=stats['faces_below_2_over_29'] == 0,
                  full_array_sha256={'candidate_points': namespace['array_sha'](p), 'candidate_faces': namespace['array_sha'](f)},
                  input_hashes=c['input_hashes'], contract_sha256=initial,
                  reader_sha256=sha(__file__), unchanged_AST_helpers=True,
                  seed_patch_fixed_masks_are_quality_diagnostics_not_feature_contracts=True,
                  global_topology_intersections_neighbors_distance_features_checked=False,
                  head_surface_or_solver_admitted=False, manufacturing_authorized=False,
                  native_generate_optimize_meshwrite_solve_calls=0,
                  numpy_version=np.__version__, readback_wall_seconds=time.monotonic() - started)
    verify()
    if sha(path) != initial:
        raise ValueError('Census contract changed')
    result['all_bound_inputs_unchanged'] = True
    with (OUT / 'readback-report.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')


if __name__ == '__main__':
    main()
