"""Independently reload the actual sheet STEP against original acquired faces."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from OCP.TopAbs import TopAbs_SOLID, TopAbs_VERTEX, TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'selection', 'arrays', 'verifier', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing acquired-sheet verification refused')
    for path, expected in [(args.selection/'selection.json', 'db98b963073b4e660ee842f8d799434d7a56de36da2cc15722af50cd0ef7a23c'),
                           (args.selection/'selected-source.npz', '028aaa2db09fee0e599be09abb38d7bebf5008addadbe5941bfdf9595fb9c54e'),
                           (args.arrays, 'dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a'),
                           (args.verifier, '3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658')]:
        if sha(path) != expected:
            raise SystemExit('Registered source/verifier mismatch')
    with np.load(args.selection/'selected-source.npz', allow_pickle=False) as data:
        selected = data['source_face_ids']
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    spec = importlib.util.spec_from_file_location('independent_source_chart_verifier', args.verifier)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    before = sha(args.step)
    report = helper.inspect_source(args.step, vertices, faces[selected], selected)
    shape = helper.load(args.step)
    if helper.indexed(shape, TopAbs_SOLID).Extent():
        raise ValueError('Unexpected solid in open acquired reference')
    native_faces = helper.indexed(shape, TopAbs_FACE)
    maximum_plane_distance = 0.
    for i in range(1, native_faces.Extent()+1):
        face = TopoDS.Face_s(native_faces.FindKey(i))
        plane = BRepAdaptor_Surface(face, True).Plane()
        corners = helper.indexed(face, TopAbs_VERTEX)
        for j in range(1, corners.Extent()+1):
            point = BRep_Tool.Pnt_s(TopoDS.Vertex_s(corners.FindKey(j)))
            maximum_plane_distance = max(maximum_plane_distance, plane.Distance(point))
    if maximum_plane_distance > 1e-6 or sha(args.step) != before:
        raise ValueError('STEP plane/vertex consistency or immutable-file check failed')
    report.update(actual_step_sha256=before, verifier_source_sha256=sha(__file__),
        retained_verifier_sha256=sha(args.verifier),
        native_face_plane_corner_maximum_mm=maximum_plane_distance,
        native_solids=0, original_source_geometry_modified=False,
        full_head_created=False, physical_acceptance=False, manufacturing_authorized=False)
    args.output.mkdir(parents=True)
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
