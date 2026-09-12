#!/usr/bin/env python3
"""Index a pinned existing STL without moving/repairing any triangle."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

STL_PIN = 'e006e1484da1352538fdaf7c23ed66f53ebcee7346d8ce94608b6c4f52a29ce1'
REPORT_PIN = '60804e33d35176bb35b83a1367a5d8a83210f4282eec7184c155632049638ce0'
HELPER_PIN = '34bb2dcd591e92b1ae6f0e8a75f2f858448319b4db4dada6eb364f3c0a1242be'
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_index(xyz):
    flat = np.ascontiguousarray(xyz.reshape(-1, 3), dtype=np.float64)
    # Byte equality also preserves signed zero, unlike tolerance-based welding.
    keys = flat.view(np.dtype((np.void, 24))).reshape(-1)
    _, first, inverse = np.unique(keys, return_index=True, return_inverse=True)
    points = flat[first].copy()
    triangles = inverse.reshape(-1, 3).astype(np.int64)
    if points[triangles].tobytes() != xyz.tobytes():
        raise ValueError('triangle_reconstruction_not_byte_exact')
    return points, triangles


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--export-report', type=Path, required=True)
    p.add_argument('--helper', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    pins = {a.source: STL_PIN, a.export_report: REPORT_PIN, a.helper: HELPER_PIN}
    if any(sha(path) != pin for path, pin in pins.items()):
        raise ValueError('pinned_input_mismatch')
    spec = importlib.util.spec_from_file_location('pinned_export_master', a.helper)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    original = helper.load_binary_stl(a.source)
    points, triangles = exact_index(original)
    summary = helper.mesh_summary(original)
    historical = json.loads(a.export_report.read_text())
    for key in ('triangles', 'exact_welded_vertices', 'exact_welded_edges',
                'boundary_edges', 'nonmanifold_edges', 'zero_area_triangles',
                'duplicate_triangles_ignoring_winding', 'connected_vertex_components',
                'winding_consistent_on_two_face_edges', 'euler_characteristic'):
        if summary[key] != historical['mesh'][key]:
            raise ValueError('topology_differs_from_receipt_' + key)
    a.output.mkdir(mode=0o700, exist_ok=False)
    target = a.output / 'head-surface.npz'
    np.savez(target, points=points, triangles=triangles)
    with np.load(target, allow_pickle=False) as saved:
        exact = saved['points'][saved['triangles']].tobytes() == original.tobytes()
    unchanged = all(sha(path) == pin for path, pin in pins.items())
    report = dict(schema='m64-private-exact-surface-npz/v1',
                  inputs_private={str(path): pin for path, pin in pins.items()},
                  producer_sha256=sha(__file__), numpy_version=np.__version__,
                  output_sha256=sha(target), points=len(points), triangles=len(triangles),
                  dtypes={'points': str(points.dtype), 'triangles': str(triangles.dtype)},
                  oriented_triangles_reconstructed_byte_exact=exact, inputs_unchanged=unchanged,
                  source_STEP_sha256=historical['source_STEP_sha256'],
                  provenance='existing_private_935_scan_derived_four_seat_STEP_body_tessellation',
                  source_coordinate_representation='STL_float32_promoted_exactly_to_float64',
                  indexing='identical_coordinate_bytes_only_preserves_triangle_order_and_winding',
                  moved_vertices=0, removed_triangles=0, repaired=False,
                  mesh_summary=summary, length_unit='scan_unit', absolute_scale_certified=False,
                  continuous_CAD_error_bound_proven=False, CFD_authorized=False,
                  manufacturing_authorized=False, private_geometry_not_for_publication=True)
    (a.output / 'conversion-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if not exact or not unchanged:
        raise ValueError('conversion_invariance_failure')
    print(json.dumps({k: report[k] for k in ('output_sha256', 'points', 'triangles',
          'oriented_triangles_reconstructed_byte_exact', 'inputs_unchanged')}))


if __name__ == '__main__':
    main()
