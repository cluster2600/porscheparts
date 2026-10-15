"""Apply the owner's flat-build constraint to the frozen titanium V5 solid."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np


def validate_orientation(orientation):
    r = np.asarray(orientation['rotation_matrix'], dtype=float)
    assert r.shape == (3, 3) and np.isfinite(r).all()
    assert np.allclose(r.T @ r, np.eye(3), atol=1e-12)
    assert abs(np.linalg.det(r)-1) < 1e-12
    assert np.allclose(r @ [0, 0, 1], [0, 0, 1], atol=1e-12), 'Carrier must remain flat'
    bounds = np.asarray(orientation['placed_bounds_mm'])
    volume = np.asarray(orientation['machine_volume_mm'])
    margin = orientation['assumed_XY_margin_mm']
    assert (bounds[0, :2] >= margin).all() and (bounds[1, :2] <= volume[:2]-margin).all()
    assert bounds[0, 2] >= orientation['assumed_platform_thickness_mm'] + orientation['assumed_min_support_height_mm']
    assert bounds[1, 2] <= volume[2]


def prepare(source, output):
    import trimesh
    from build123d import Axis, Vector, export_step, import_step

    source, output = source.resolve(), output.resolve()
    assert not (output/'print-orientation.json').exists(), 'Preserve earlier study output'
    (output/'v5/mesh-9').mkdir(parents=True, exist_ok=True)
    for name in ('carrier.step', 'carrier.stl', 'geometry.json', 'study.json', 'constraint-check.json'):
        shutil.copy2(source/'v5'/name, output/'v5'/name)
    for name in ('mesh.inp', 'mesh.npz', 'mesh.json', 'quality.json'):
        shutil.copy2(source/'v5/mesh-9'/name, output/'v5/mesh-9'/name)
    mesh = trimesh.load_mesh(source/'v5/carrier.stl')
    c = np.sqrt(.5)
    rotation = np.array([[c, -c, 0], [c, c, 0], [0, 0, 1]])
    points = mesh.vertices @ rotation.T
    translation = np.r_[300-(points[:, :2].min(0)+points[:, :2].max(0))/2, 30-points[:, 2].min()]
    placed = points+translation
    orientation = {
        'machine': '600 mm square metal LPBF envelope; supplier/process not selected',
        'machine_volume_mm': [600, 600, 600],
        'envelope_example': 'Nikon SLM NXG XII 600; envelope reference only',
        'assumed_platform_thickness_mm': 20,
        'assumed_min_support_height_mm': 10,
        'assumed_XY_margin_mm': 10,
        'rotation_degrees_xyz': [0, 0, 45],
        'rotation_matrix': rotation.tolist(),
        'translation_mm': translation.tolist(),
        'part_rotated_size_mm': np.ptp(points, axis=0).tolist(),
        'placed_bounds_mm': [placed.min(0).tolist(), placed.max(0).tolist()],
        'flat_build_required': True,
        'screen_fit': True,
        'platform_supplier_confirmed': False,
        'qualified_job_file': False,
        'metal': 'Ti-6Al-4V Grade 5 proposal; no polymer',
        'process_parameter_transfer_qualified': False,
    }
    validate_orientation(orientation)
    (output/'print-orientation.json').write_text(json.dumps(orientation, indent=2)+'\n')
    body = import_step(source/'v5/carrier.step')
    assert len(body.solids()) == 1
    flat = body.solids()[0].rotate(Axis.Z, 45).translate(Vector(*translation))
    assert flat.is_valid and len(flat.solids()) == 1
    assert abs(flat.volume/body.volume-1) < 1e-10
    export_step(flat, output/'carrier-flat.step')
    reread = import_step(output/'carrier-flat.step')
    assert reread.is_valid and len(reread.solids()) == 1
    assert abs(reread.volume/body.volume-1) < 1e-8
    mesh.vertices = placed
    mesh.export(output/'carrier-flat.stl')
    bed_required = float(np.ptp(placed[:, :2], axis=0).max()+20)
    result = {
        'source_STEP_sha256': hashlib.sha256((source/'v5/carrier.step').read_bytes()).hexdigest(),
        'flat_STEP_sha256': hashlib.sha256((output/'carrier-flat.step').read_bytes()).hexdigest(),
        'rigid_transform_only': True, 'volume_preserved': True,
        'source_volume_mm3': body.volume, 'flat_readback_volume_mm3': reread.volume,
        'part_build_height_mm': float(np.ptp(placed[:, 2])),
        'flat_square_bed_required_with_margins_mm': bed_required,
        'fits_400_mm_square_flat': bed_required <= 400, 'fits_450_mm_square_flat': bed_required <= 450,
        'geometry_and_mass_changed': False, 'functional_acceptance': False,
        'previous_structural_rejection_still_applies': True,
    }
    (output/'flat-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


def render(output):
    import pyvista as pv
    import trimesh
    mesh = trimesh.load_mesh(output/'carrier-flat.stl')
    poly = pv.PolyData(mesh.vertices, np.c_[np.full(len(mesh.faces), 3), mesh.faces])
    plot = pv.Plotter(off_screen=True, window_size=(1600, 1050)); plot.set_background('#f5f5f2')
    plot.add_mesh(pv.Box(bounds=(0, 600, 0, 600, 0, 20)), color='#354957')
    plot.add_mesh(poly, color='#a4afb7', smooth_shading=True, split_sharp_edges=True, feature_angle=35, specular=.25)
    plot.add_text('Ti-6Al-4V METAL / FLAT BUILD\nZero tilt; 45 degrees only within the bed plane', font_size=20, color='#10242e')
    plot.add_text('Actual V5 CAD; 40 mm part height\n600 x 600 mm envelope study; 10 mm assumed support gap\nSupports and machine process remain unqualified', position='lower_left', font_size=14, color='#822b22')
    plot.camera_position = [(980, -620, 660), (300, 300, 30), (0, 0, 1)]
    plot.enable_parallel_projection(); plot.camera.parallel_scale = 465
    plot.show_axes(); plot.screenshot(output/'flat-build.png'); plot.close()


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2])); render(Path(sys.argv[2]))
