"""Slice the actual oriented surface at 60 um; no supports or laser paths invented."""
import csv
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh


def section(mesh, z):
    tri = mesh.triangles
    faces = np.flatnonzero((tri[:, :, 2].min(1) <= z) & (tri[:, :, 2].max(1) >= z))
    lines, ids = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, z],
                                                 local_faces=faces, return_faces=True)
    if not len(lines): return lines[:, :, :2], 0., 0.
    tangent = np.cross([0, 0, 1], mesh.face_normals[ids])
    flip = np.einsum('ij,ij->i', lines[:, 1]-lines[:, 0], tangent) < 0
    lines[flip] = lines[flip, ::-1]
    _, count = np.unique(np.round(lines[:, :, :2].reshape(-1, 2), 6), axis=0, return_counts=True)
    assert (count % 2 == 0).all(), 'Open layer contour'
    a, b = lines[:, 0, :2], lines[:, 1, :2]
    area = float(np.sum(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0])/2)
    assert area >= -1e-5
    return lines[:, :, :2], max(0., area), float(np.linalg.norm(b-a, axis=1).sum())


def run(root):
    mesh = trimesh.load_mesh(root/'v5/carrier.stl')
    assert mesh.is_watertight and mesh.is_winding_consistent
    ori = json.loads((root/'print-orientation.json').read_text())
    transform = np.eye(4); transform[:3, :3] = ori['rotation_matrix']; transform[:3, 3] = ori['translation_mm']
    mesh.apply_transform(transform)
    count = int(np.ceil((mesh.bounds[1, 2]-ori['assumed_platform_thickness_mm'])/.06))
    height = ori['assumed_platform_thickness_mm']+(np.arange(count)+.5)*.06
    rows = []; contours = []; offsets = [0]
    for i, z in enumerate(height):
        lines, area, perimeter = section(mesh, z)
        rows.append((i+1, z, len(lines), area, perimeter)); contours.extend(lines); offsets.append(len(contours))
    with (root/'slices-60um.csv').open('w') as f:
        w = csv.writer(f); w.writerow(['layer', 'height_mm', 'segments', 'area_mm2', 'perimeter_mm']); w.writerows(rows)
    np.savez_compressed(root/'slices-60um.npz', height_mm=height, offsets=offsets, segments=np.array(contours))
    volume = sum(r[3] for r in rows)*.06
    error = volume/mesh.volume-1
    refined = None
    if abs(error) >= .001:
        # Flat faces can alias the 60 um grid; finer integration audits volume only.
        dz = .006
        heights = ori['assumed_platform_thickness_mm'] + (np.arange(int(np.ceil(
            (mesh.bounds[1, 2]-ori['assumed_platform_thickness_mm'])/dz)))+.5)*dz
        fine_volume = sum(section(mesh, z)[1] for z in heights)*dz
        fine_error = fine_volume/mesh.volume-1
        assert abs(fine_error) < .001, fine_error
        refined = {'integration_interval_mm': dz, 'volume_mm3': fine_volume,
                   'relative_volume_error': fine_error, 'machine_layer_change': False}
    result = {'nominal_layer_mm': .06, 'total_layer_intervals_above_assumed_platform': count,
              'nonempty_part_layers': sum(r[2] > 0 for r in rows), 'all_part_contours_closed': True,
              'midpoint_integrated_part_volume_mm3': volume, 'STL_volume_mm3': float(mesh.volume),
              'relative_volume_error': error, 'coarse_volume_within_0_1_percent': bool(abs(error) < .001),
              'refined_volume_audit': refined, 'laser_scan_vectors_generated': False,
              'support_contours_generated': False, 'qualified_machine_file': False}
    (root/'slice-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return result


def selfcheck():
    cube = trimesh.creation.box([2., 3., 4.])
    for z in np.arange(-1.95, 2., .1):
        _, a, p = section(cube, z)
        assert abs(a-6) < 1e-10 and abs(p-10) < 1e-10
    outer = trimesh.creation.cylinder(radius=2, height=4, sections=64)
    inner = trimesh.creation.cylinder(radius=1, height=4, sections=64); inner.invert()
    _, a, p = section(trimesh.util.concatenate((outer, inner)), .03)
    assert abs(a-96*np.sin(2*np.pi/64)) < 1e-10
    assert abs(p-384*np.sin(np.pi/64)) < 1e-10
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory); (root/'v5').mkdir()
        slab = trimesh.creation.box([2, 3, .144]); slab.apply_translation([0, 0, .172])
        slab.export(root/'v5/carrier.stl')
        (root/'print-orientation.json').write_text(json.dumps({
            'rotation_matrix': np.eye(3).tolist(), 'translation_mm': [0, 0, 0],
            'assumed_platform_thickness_mm': 0}))
        result = run(root)
        assert not result['coarse_volume_within_0_1_percent']
        assert abs(result['refined_volume_audit']['relative_volume_error']) < 1e-6
    print('Closed cube slice area/perimeter and orientation checks passed.')


if __name__ == '__main__':
    if sys.argv[1] == '--selfcheck': selfcheck()
    else: run(Path(sys.argv[1]))
