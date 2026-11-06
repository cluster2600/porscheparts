"""Exercise real native predicates on a literal folded annulus and disk."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    constructor = module(job['constructor_source'], 'controlled_disk_constructor')
    inspector = module(job['candidate_inspector'], 'independent_disk_inspector')
    scalar = module(job['necessary_checker'], 'independent_control_triangle_checker')
    detector = module(job['intersection_helper'], 'native_control_intersections')
    fan_helper = module(job['fan_helper'], 'native_control_vertex_fans')
    outcomes = []
    args.output.mkdir(mode=0o700, exist_ok=False)
    for folded in (False, True):
        points = np.array([[0., 0, 0], [1.5, 0, 0], [1.5, 1.5, 1.5], [0, 1.5, 0],
                           [-.125, -.125, -.125], [1.625, -.125, -.125],
                           [1.625, 1.625, 1.625], [-.125, 1.625, -.125]])
        if not folded:
            points[:, 2] = 0
        faces = []
        for i in range(4):
            j = (i+1) % 4
            faces.extend(((i, j, j+4), (i, j+4, i+4)))
        faces = np.asarray(faces)
        legal, _ = scalar.triangle_replay(points[:4], points[faces[::2]])
        assert scalar.recursive_count(4, legal) == (1 if folded else 2)
        patch = constructor.first_disk(4, legal)
        inspector.check_disk(np.arange(4), patch)
        combined = np.r_[faces, patch]
        for current, expected_edges in ((faces, 8), (combined, 4)):
            pairs, _, zero = detector.detect(points, current)
            assert not len(pairs) and not len(zero)
            fans, boundary = fan_helper.vertex_fans(current, len(points))
            assert np.all(fans == 1) and len(boundary) == expected_edges
        assert set(map(tuple, boundary)) == {(5, 4), (6, 5), (7, 6), (4, 7)}
        try:
            inspector.check_disk(np.arange(4), patch[:, [0, 2, 1]])
        except AssertionError:
            pass
        else:
            raise AssertionError('Reversed disk accepted')
        try:
            inspector.check_disk(np.arange(4), patch[:1])
        except AssertionError:
            pass
        else:
            raise AssertionError('Incomplete disk accepted')
        assert not scalar.recursive_count(4, scalar.triangle_replay(points[:4], points[faces[::2, ::-1]])[0])
        name = 'folded' if folded else 'flat'
        np.savez_compressed(args.output/(name+'-fixture.npz'), points=points, original_faces=faces, added_faces=patch)
        outcomes.append(dict(name=name, vertices=8, old_faces=8, new_faces=10,
                             old_boundary_edges=8, new_boundary_edges=4,
                             unselected_outer_perimeter_exact=True, native_intersections_and_fans_passed=True,
                             reversed_incomplete_and_wrong_owner_side_refused=True))
    legacy = detector.controls()
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), fixtures=outcomes,
                  frozen_native_predicate_controls=legacy, native_nonplanar_controls_passed=True,
                  scan_used=False, physical_acceptance=False, manufacturing_authorized=False)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
