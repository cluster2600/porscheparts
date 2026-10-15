"""Flat placement and contour integration of the corrected surface, without supports."""
import csv
import json
from pathlib import Path
import sys

import numpy as np

from corrected_cad import BASE, precise_volume, sha
from inspect_candidate import normalized_mesh
sys.path.insert(0, str(BASE))
from flat_build import validate_orientation
from slice_print import section


def run(source, output):
    from build123d import Axis, Vector, import_step, export_step
    import pyvista as pv
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    mesh, surface = normalized_mesh(source/'carrier.stl')
    c = np.sqrt(.5)
    rotation = np.array([[c, -c, 0], [c, c, 0], [0, 0, 1]])
    points = mesh.vertices @ rotation.T
    translation = np.r_[300-(points[:, :2].min(0)+points[:, :2].max(0))/2, 30-points[:, 2].min()]
    mesh.vertices = points+translation
    orientation = {
        'machine_volume_mm': [600, 600, 600], 'machine_supplier_confirmed': False,
        'assumed_platform_thickness_mm': 20, 'assumed_min_support_height_mm': 10,
        'assumed_XY_margin_mm': 10, 'rotation_degrees_xyz': [0, 0, 45],
        'rotation_matrix': rotation.tolist(), 'translation_mm': translation.tolist(),
        'placed_bounds_mm': mesh.bounds.tolist(), 'flat_build_required': True,
        'metal': 'Ti-6Al-4V Grade 5 proposal', 'qualified_job_file': False,
    }
    validate_orientation(orientation)
    (output/'print-orientation.json').write_text(json.dumps(orientation, indent=2)+'\n')
    body = import_step(source/'carrier.step').solids()[0]
    flat = body.rotate(Axis.Z, 45).translate(Vector(*map(float, translation)))
    export_step(flat, output/'carrier-flat.step')
    reread = import_step(output/'carrier-flat.step')
    v0, _ = precise_volume(body); v1, _ = precise_volume(reread)
    assert reread.is_valid and len(reread.solids()) == 1 and abs(v1/v0-1)<1e-8
    mesh.export(output/'carrier-flat.stl')
    mesh.export(output/'carrier-flat.glb')
    rows = []
    for i in range(int(np.ceil((mesh.bounds[1, 2]-20)/.06))):
        z = 20+(i+.5)*.06
        lines, area, perimeter = section(mesh, z)
        rows.append([i+1, z, len(lines), area, perimeter])
    with (output/'slices-60um.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['layer', 'z_mm', 'segments', 'area_mm2', 'perimeter_mm'])
        writer.writerows(rows)
    integrated = sum(row[3] for row in rows)*.06
    refined = None
    if abs(integrated/mesh.volume-1) >= .001:
        fine = sum(section(mesh, z)[1] for z in np.arange(20+.003, mesh.bounds[1, 2], .006))*.006
        assert abs(fine/mesh.volume-1)<.001
        refined = {'interval_mm': .006, 'volume_mm3': fine, 'relative_error': fine/mesh.volume-1,
                   'machine_layer_change': False}
    plot = pv.Plotter(off_screen=True, window_size=(1600, 1050))
    plot.set_background('#f5f5f2')
    plot.add_mesh(pv.Box(bounds=(0, 600, 0, 600, 0, 20)), color='#354957')
    plot.add_mesh(pv.PolyData(mesh.vertices, np.c_[np.full(len(mesh.faces), 3), mesh.faces]),
                  color='#a4afb7', smooth_shading=True, split_sharp_edges=True, specular=.25)
    plot.add_text('993 TURBO / CORRECTED PROVISIONAL CAD\nTi-6Al-4V Grade 5 proposal / flat metal build', font_size=19, color='#10242e')
    plot.add_text('1.188 kg nominal CAD mass; 52 mm part height\nZero tilt; 45 degrees within the bed plane\nAssumed 600 mm bed and 10 mm support gap\nSupports, fit and manufacturing remain unqualified',
                  position='lower_left', font_size=14, color='#822b22')
    plot.camera_position = [(980, -620, 660), (300, 300, 30), (0, 0, 1)]
    plot.enable_parallel_projection(); plot.camera.parallel_scale = 465
    plot.screenshot(output/'flat-build.png'); plot.close()
    r = {'orientation': orientation, 'source_STEP_sha256': sha(source/'carrier.step'),
         'flat_STEP_sha256': sha(output/'carrier-flat.step'), 'source_surface': surface,
         'source_volume_mm3': v0, 'flat_STEP_volume_mm3': v1, 'rigid_transform_only': True,
         'part_height_mm': float(np.ptp(mesh.vertices[:, 2])),
         'minimum_square_bed_with_assumed_margins_mm': float(np.ptp(mesh.vertices[:, :2], axis=0).max()+20),
         'nominal_layer_mm': .06, 'nonempty_layers': sum(row[2]>0 for row in rows),
         'all_contours_closed': True, 'integrated_volume_mm3': integrated,
         'surface_volume_mm3': float(mesh.volume), 'relative_volume_error': integrated/mesh.volume-1,
         'refined_volume_audit': refined, 'slice_csv_sha256': sha(output/'slices-60um.csv'),
         'support_or_laser_paths_generated': False, 'print_distortion_qualified': False,
         'manufacturing_authorized': False}
    (output/'flat-summary.json').write_text(json.dumps(r, indent=2)+'\n')
    print(json.dumps({k: r[k] for k in ('part_height_mm','nonempty_layers','relative_volume_error','refined_volume_audit')}))


if __name__ == '__main__':
    run(*sys.argv[1:])
