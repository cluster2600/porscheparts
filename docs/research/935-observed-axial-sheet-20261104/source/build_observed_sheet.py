"""Build exact native source-fan charts for the registered acquired sheet."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('selection', 'arrays', 'builder', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing acquired-sheet CAD output refused')
    paths = [(args.selection/'selection.json', 'db98b963073b4e660ee842f8d799434d7a56de36da2cc15722af50cd0ef7a23c'),
             (args.selection/'selected-source.npz', '028aaa2db09fee0e599be09abb38d7bebf5008addadbe5941bfdf9595fb9c54e'),
             (args.arrays, 'dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a'),
             (args.builder, 'fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e')]
    for path, expected in paths:
        if sha(path) != expected:
            raise SystemExit('Registered acquired-sheet input changed: '+path.name)
    selection = json.loads(paths[0][0].read_text())
    if not all(selection['selected'][key] for key in ('native_chart_size_admitted', 'native_chart_defect_index_admitted')):
        raise SystemExit('Source chart admission failed; no alternative mask selected')
    with np.load(paths[1][0], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
        source_vertices, source_faces = data['source_vertex_ids'], data['source_face_ids']
    with np.load(args.arrays, allow_pickle=False) as data:
        if not np.array_equal(vertices, data['vertices'][source_vertices]):
            raise ValueError('Observed coordinates differ from original arrays')
        if not np.array_equal(source_vertices[faces], data['triangles'][source_faces]):
            raise ValueError('Observed connectivity differs from original arrays')
    spec = importlib.util.spec_from_file_location('retained_source_chart_builder', args.builder)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    args.output.mkdir(parents=True)
    helper.save(args.output/'plan.json', {'source_sha256': sha(__file__),
        'inputs_sha256': {path.name: expected for path, expected in paths},
        'construction': 'Exact acquired triangles; original edge adjacency and source vertex-fan charts',
        'coordinates_may_change_mm': 0, 'native_roundtrip_limit_mm': 1e-6,
        'welding_or_healing': False, 'plane_fit_adopted': False,
        'physical_acceptance': False, 'manufacturing_authorized': False})
    helper.save(args.output/'controls.json', helper.controls(args.output))
    v, f, mapping, groups, report = helper.atlas(vertices, faces)
    np.savez_compressed(args.output/'source-provenance.npz', vertices=v, triangles=f,
                        original_source_vertex_ids=source_vertices[mapping],
                        original_source_face_ids=source_faces, component_labels=groups)
    shape = helper.native_shape(v, f, groups)
    step = args.output/'observed-axial-sheet-source-charts.step'
    helper.export(shape, step)
    report.update(step_sha256=sha(step), acquired_geometry_changed=False,
                  plane_fit_adopted=False, charts_are_physical_components=False,
                  full_head_created=False, physical_acceptance=False, manufacturing_authorized=False)
    helper.save(args.output/'construction.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
