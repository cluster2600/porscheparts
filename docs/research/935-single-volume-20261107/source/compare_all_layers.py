"""Compare every exact union section with the independently united composite CLI."""
import argparse
import ast
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import time

import numpy as np
import shapely


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    spec = importlib.util.spec_from_file_location('independent_sections', job['section_source'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    tree = ast.parse(Path(job['layers_source']).read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'layers')
    namespace = {'np': np}
    exec(compile(ast.Module(body=[function], type_ignores=[]), job['layers_source'], 'exec'), namespace)
    layers = namespace['layers']
    square = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.], [0., 0.]])
    control = helper.section([(1, square)], return_geometry=True)
    assert control.symmetric_difference(control).area == 0
    shifted = helper.section([(1, square+[.5, 0.])], return_geometry=True)
    assert control.symmetric_difference(shifted).area == 1
    args.output.mkdir(mode=0o700, exist_ok=False)
    rows = []
    for index, pair in enumerate(itertools.zip_longest(layers(Path(job['candidate_cli'])), layers(Path(job['reference_cli'])))):
        left, right = pair
        assert left is not None and right is not None, 'Different layer counts'
        z, previous, rings = left
        rz, rprevious, reference_rings = right
        assert abs(z-rz) < 1e-12 and abs(previous-rprevious) < 1e-12
        row = dict(index=index, z_mm=z, height_mm=z-previous)
        try:
            actual = helper.section(rings, return_geometry=True)
            expected = helper.section(reference_rings, return_geometry=True)
            difference = actual.symmetric_difference(expected).area
            # Same bound used for the frozen 10^-12 mm composite contour grid.
            limit = 4e-12*expected.length+1e-8
            row.update(candidate_area_mm2=actual.area, reference_area_mm2=expected.area,
                       symmetric_difference_mm2=difference, numerical_area_limit_mm2=limit,
                       passed=bool(difference <= limit))
        except ValueError as error:
            row.update(passed=False, invalid_section_reason=str(error))
        rows.append(row)
        if len(rows) % 100 == 0:
            print('Compared', len(rows), 'layers', flush=True)
    assert len(rows) == 2074 and rows[0]['z_mm'] == 0
    valid = [r for r in rows if 'symmetric_difference_mm2' in r]
    failed = [r for r in rows if not r['passed']]
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
                  candidate_cli_sha256=sha(job['candidate_cli']), reference_cli_sha256=sha(job['reference_cli']),
                  layers_compared=len(rows), invalid_layers=len(rows)-len(valid), failed_layers=len(failed),
                  all_layers_match_reference_within_existing_contour_grid_bound=not failed,
                  maximum_layer_symmetric_difference_mm2=max((r['symmetric_difference_mm2'] for r in valid), default=None),
                  candidate_layer_integral_mm3=sum(r['candidate_area_mm2']*r['height_mm'] for r in valid),
                  reference_layer_integral_mm3=sum(r['reference_area_mm2']*r['height_mm'] for r in valid),
                  shapely=shapely.__version__, geos=shapely.geos_version_string,
                  analytic_identical_and_shifted_controls_passed=True, geometry_repaired=False,
                  hatch_or_exposure_present=False, machine_job=False, manufacturing_qualified=False,
                  engine_qualified=False, seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'private-layer-comparisons.json').write_text(json.dumps(rows)+'\n')
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
