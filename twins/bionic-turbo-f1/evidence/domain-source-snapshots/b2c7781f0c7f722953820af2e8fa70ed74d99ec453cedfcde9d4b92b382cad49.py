"""Read-only nearest-surface review of the exported rotor boundary label."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pyvista as pv
import vtk

BASE = Path(__file__).resolve().parent
FLUID = BASE / 'baseline-fluid-006'
SURFACE = BASE / 'baseline-surface-008'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = BASE / 'rotor-label-diagnostic-008.json'
    if target.exists():
        raise ValueError('Refusing to overwrite diagnostic')
    report = json.loads((SURFACE / 'surface-report.json').read_text())
    paths = [SURFACE / 'fluid-regions.stl', SURFACE / 'surface-report.json', FLUID / 'rotor-union.stl', FLUID / 'housing-final.stl']
    hashes = {str(p.relative_to(BASE)): sha(p) for p in paths}
    if sha(paths[0]) != report['surface_sha256']:
        raise ValueError('Surface hash mismatch')
    for name in ['rotor-union.stl', 'housing-final.stl']:
        if sha(FLUID / name) != report['sources'][name]:
            raise ValueError('Source hash mismatch')
    count = report['classification']['face_counts']['rotor']
    triangles = np.empty((count * 3, 3), dtype=np.float64)
    active = False
    cursor = 0
    with paths[0].open() as stream:
        for line in stream:
            if line.strip() == 'solid rotor':
                active = True
                continue
            if active and line.strip() == 'endsolid rotor':
                break
            if active and line.startswith('vertex '):
                triangles[cursor] = np.fromstring(line[7:], sep=' ') * 1000
                cursor += 1
    if cursor != count * 3:
        raise ValueError('Rotor facet count mismatch')
    triangles = triangles.reshape(count, 3, 3)
    centers = triangles.mean(axis=1)
    rotor = pv.read(FLUID / 'rotor-union.stl')
    rotor_distance = np.abs(pv.PolyData(centers).compute_implicit_distance(rotor)['implicit_distance'])
    highest = np.argsort(rotor_distance)[-10:][::-1]
    selected = centers[highest]
    housing = pv.read(FLUID / 'housing-final.stl')
    housing_distance = np.abs(pv.PolyData(selected).compute_implicit_distance(housing)['implicit_distance'])
    locator = vtk.vtkStaticCellLocator(); locator.SetDataSet(rotor); locator.BuildLocator()
    rows = []
    for rank, (index, hd) in enumerate(zip(highest, housing_distance), 1):
        closest = [0., 0., 0.]
        cell_id = vtk.reference(0); sub_id = vtk.reference(0); distance2 = vtk.reference(0.)
        locator.FindClosestPoint(centers[index], closest, cell_id, sub_id, distance2)
        tri = triangles[index]
        normal = np.cross(tri[1] - tri[0], tri[2] - tri[0]); normal /= np.linalg.norm(normal)
        center = centers[index]
        rows.append({'rank': rank, 'rotor_patch_face_index': int(index), 'center_mm': center.tolist(),
                     'radius_mm': float(np.linalg.norm(center[:2])), 'vertices_mm': tri.tolist(),
                     'fluid_outward_normal': normal.tolist(), 'rotor_distance_mm': float(rotor_distance[index]),
                     'housing_distance_mm': float(hd), 'closest_rotor_point_mm': closest,
                     'closest_rotor_face_id': int(cell_id), 'locator_distance_mm': float(distance2)**.5,
                     'distance_to_ideal_rear_plane_mm': float(abs(center[2] + 3.75))})
    near_floor = (np.max(np.abs(triangles[:, :, 2] + 3.75), axis=1) < .25) & (np.max(np.linalg.norm(triangles[:, :, :2], axis=2), axis=1) < 35.5)
    result = {'status': 'diagnostic_only', 'mesh_modified': False, 'labels_modified': False,
              'input_sha256': hashes, 'script_sha256': sha(Path(__file__)), 'units': 'mm',
              'method': 'Stream existing ASCII rotor region; convert m to mm; VTK exact triangle implicit distance for every rotor-labelled face centroid, then closest-point locator cross-check for ten farthest faces.',
              'rotor_label_face_count': count,
              'computed_maximum_rotor_distance_mm': float(rotor_distance.max()),
              'declared_maximum_rotor_distance_mm': report['classification']['maximum_rotor_distance_mm'],
              'rotor_distance_percentiles_mm': {str(q): float(np.percentile(rotor_distance, q)) for q in [0, 50, 90, 99, 99.9, 100]},
              'rotor_label_faces_all_vertices_within_0_25_mm_of_rear_plane': int(np.count_nonzero(near_floor)),
              'farther_than_0_3_mm_count': int(np.count_nonzero(rotor_distance > .3)),
              'farther_than_0_3_mm_and_near_rear_plane_count': int(np.count_nonzero((rotor_distance > .3) & near_floor)),
              'ten_farthest': rows, 'limitations': ['Diagnostic classifications near the rear plane are geometric witnesses, not automatic relabelling.', 'Centroid distances do not bound every point of a triangle.']}
    for path in paths:
        if sha(path) != hashes[str(path.relative_to(BASE))]:
            raise ValueError('Input changed during diagnostic')
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','ten_farthest')}, indent=2))
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
