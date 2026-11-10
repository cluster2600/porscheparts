"""Unite the coplanar plate section; preserve every other serialized layer exactly."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
import pyclipper
from shapely.geometry import Polygon, box


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plane(path):
    rings = []
    z = None
    with Path(path).open('rb') as stream:
        for line in stream:
            if line.startswith(b'$$LAYER/'):
                z = float(line.split(b'/')[1])
                if z > 5:
                    break
            elif z == 5 and line.startswith(b'$$POLYLINE/'):
                fields = line.split(b'/')[1].strip().split(b',')
                identifier, direction, n = map(int, fields[:3])
                assert identifier == 1 and direction in (0, 1) and len(fields) == 3+2*n
                rings.append((direction, np.asarray(fields[3:], dtype=float).reshape(n, 2)))
    return rings


def unchanged_bytes(path):
    digest = hashlib.sha256()
    z = None
    with Path(path).open('rb') as stream:
        for line in stream:
            if line.startswith(b'$$LAYER/'):
                z = float(line.split(b'/')[1])
            if not (z == 5 and line.startswith(b'$$POLYLINE/')):
                digest.update(line)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    predecessor = json.loads(Path(job['readback_report']).read_text())
    comparison = json.loads(Path(job['comparison_report']).read_text())
    assert predecessor['input_sha256'] == sha(job['input_cli'])
    assert predecessor['all_layers_examined'] and predecessor['contour_controls_passed']
    assert predecessor['invalid_layers'] == 1 and len(predecessor['errors']) == 1
    assert predecessor['errors'][0]['z_mm'] == 5 and predecessor['errors'][0]['reason'].startswith('Nested shells')
    assert comparison['layers_compared'] == 2074 and comparison['invalid_layers'] == comparison['failed_layers'] == 1
    rows = json.loads(Path(job['comparison_rows']).read_text())
    assert [r['index'] for r in rows if not r['passed']] == [100] and rows[100]['z_mm'] == 5
    tree = ast.parse(Path(job['union_source']).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('signed_area', 'unite')
             or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCALE' for t in n.targets)]
    assert len(nodes) == 3
    namespace = {'np': np, 'pyclipper': pyclipper}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), job['union_source'], 'exec'), namespace)
    assert namespace['SCALE'] == 10**12
    unite = namespace['unite']
    spec = importlib.util.spec_from_file_location('independent_sections', job['section_source'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    square = np.array([[0., 0.], [2., 0.], [2., 2.], [0., 2.], [0., 0.]])
    assert helper.section(unite([(1, square), (1, square*.5+.5)]))[0] == 4
    hole = square[::-1]*.5+.5
    assert helper.section(unite([(1, square), (0, hole)]))[0] == 3
    data = dict(np.load(job['supports'], allow_pickle=False))
    assert data['resource_ids'][-2] == 1119
    a, b = data['vertex_offsets'][-3:-1]
    plate = data['vertices'][a:b]
    assert len(plate) == 8 and np.array_equal(np.unique(plate[:, 2]), [0., 5.])
    lower, upper = plate.min(axis=0), plate.max(axis=0)
    assert len(np.unique(plate, axis=0)) == 8
    for axis in range(3):
        assert np.array_equal(np.unique(plate[:, axis]), [lower[axis], upper[axis]])
    bounds = np.rint(np.r_[lower[:2], upper[:2]]*10**12)/10**12
    analytic_plate = box(*bounds)
    rings = plane(job['input_cli'])
    assert len(rings) == 564
    for direction, xy in rings:
        assert direction == 1 and np.array_equal(xy[0], xy[-1])
        polygon = Polygon(xy)
        assert polygon.is_valid and polygon.area > 0 and analytic_plate.covers(polygon)
    assert any(Polygon(xy).equals(analytic_plate) for _, xy in rings)
    canonical = unite(rings)
    actual = helper.section(canonical, return_geometry=True)
    reference = helper.section(plane(job['reference_cli']), return_geometry=True)
    limit = 4e-12*reference.length+1e-8
    assert len(canonical) == 1 and canonical[0][0] == 1
    assert actual.symmetric_difference(analytic_plate).area <= limit
    assert actual.symmetric_difference(reference).area <= limit
    args.output.mkdir(mode=0o700, exist_ok=False)
    target = args.output/'935-supported-single-volume-50um-united.cli'
    replaced = False
    z = None
    with Path(job['input_cli']).open('rb') as source, target.open('xb') as output:
        for line in source:
            if line.startswith(b'$$LAYER/'):
                z = float(line.split(b'/')[1])
            if z == 5 and line.startswith(b'$$POLYLINE/'):
                if not replaced:
                    for direction, xy in canonical:
                        output.write((f'$$POLYLINE/1,{direction},{len(xy)},'+','.join(f'{x:.12f}' for x in xy.ravel())+'\n').encode())
                    replaced = True
            else:
                output.write(line)
    assert replaced
    before, after = unchanged_bytes(job['input_cli']), unchanged_bytes(target)
    assert before == after, 'An unselected serialized byte changed'
    readback = helper.section(plane(target), return_geometry=True)
    assert readback.symmetric_difference(reference).area <= limit
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), input_cli_sha256=sha(job['input_cli']),
                  output_cli_sha256=sha(target), selected_plane_mm=5., input_rings=len(rings), output_rings=len(canonical),
                  every_input_ring_positive_simple_and_inside_actual_plate=True,
                  actual_plate_outer_ring_present=True, exact_other_layer_bytes_sha256=before,
                  all_other_serialized_bytes_unchanged=True,
                  independent_reference_symmetric_difference_mm2=readback.symmetric_difference(reference).area,
                  actual_plate_symmetric_difference_mm2=readback.symmetric_difference(analytic_plate).area,
                  numerical_area_limit_mm2=limit, nested_positive_and_hole_controls_passed=True,
                  mesh_modified=False, layer_height_changed=False, tolerance_relaxed=False,
                  full_final_layer_comparison_pending=True, machine_job=False,
                  manufacturing_qualified=False, engine_qualified=False, seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
