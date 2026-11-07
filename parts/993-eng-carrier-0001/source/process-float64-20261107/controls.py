"""Small preparation controls; no current carrier slicing or package installation."""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main(args):
    here = Path(__file__).resolve().parent
    replay = load('prepared_replay', here / 'run_layer.py')
    call = SimpleNamespace(repository_root=args.repository_root, input_manifest=args.input_manifest,
                           source_manifest_sha256=args.source_manifest_sha256)
    expected, supplied, paths, profile, _ = replay.inputs(call)
    sys.path.insert(0, str(paths['site_packages']))
    import numpy as np
    oracle = load('prepared_oracle', here / 'strict_plane_oracle.py')
    outward = load('prepared_bounds', here / 'outward_bounds.py')
    vertices = np.array([[-5,-5,-5],[5,-5,-5],[5,5,-5],[-5,5,-5],
                         [-5,-5,5],[5,-5,5],[5,5,5],[-5,5,5]], dtype=np.float64)
    faces = [[0,2,1],[0,3,2],[4,5,6],[4,6,7]]
    for i in range(4):
        j = (i+1) % 4
        faces.extend([[i,j,j+4],[i,j+4,i+4]])
    cut = oracle.slice_rings(vertices, np.asarray(faces, dtype=np.int64), .37)
    area = outward.section_area_bounds(vertices, cut['ring_source_edges'], .37, cut['signed_area_mm2'])
    assert cut['signed_area_mm2'] == 100. and len(cut['rings']) == 1
    assert Fraction(area['area_mm2'][0]) <= 100 <= Fraction(area['area_mm2'][1])
    refused = []
    with tempfile.TemporaryDirectory(prefix='carrier-layer-preparation-') as temporary:
        for name, changes, message in [('wrong_schema', {'schema':'wrong'}, 'Explicit private input schema differs'),
                                       ('wrong_source_id', {'source_id':'foreign'}, 'Only the admitted current source and layer 517 are supported'),
                                       ('wrong_layer', {'layer':518}, 'Only the admitted current source and layer 517 are supported')]:
            target = Path(temporary) / (name+'.json')
            target.write_text(json.dumps(dict(supplied, **changes)))
            changed = SimpleNamespace(**vars(call)); changed.input_manifest = str(target)
            try:
                replay.inputs(changed)
            except ValueError as exc:
                assert str(exc) == message
                refused.append(name)
            else:
                raise AssertionError('Preflight admitted '+name)
        changed = SimpleNamespace(**vars(call)); changed.source_manifest_sha256 = '0'*64
        try:
            replay.inputs(changed)
        except ValueError as exc:
            assert str(exc) == 'Source manifest identity differs'
            refused.append('wrong_source_manifest_hash')
        else:
            raise AssertionError('Unbound source manifest admitted')
    replay.verify_profile(profile)
    print(json.dumps(dict(status='small_cube_and_prewrite_binding_controls_passed',
                          area_bounds_mm2=area['area_mm2'], refused=refused,
                          current_source_sliced=False, new_runtime_qualified=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('repository-root','input-manifest','source-manifest-sha256'):
        parser.add_argument('--'+name, required=True)
    main(parser.parse_args())
