#!/usr/bin/env python3
"""Opaque VTK preview of exact private input/output meshes and a real bore cut.

Display normals may interpolate lighting only. No decimation, remeshing,
coordinate smoothing, fabrication modification, or synthetic imagery is used.
"""
import argparse
import json
from pathlib import Path

from export_master import sha256
from compare_meshes import read_mesh


def run(args):
    import numpy as np
    import pyvista as pv
    import vtk
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    image = args.output
    receipt_path = image.with_suffix('.json')
    if image.exists() or receipt_path.exists():
        raise FileExistsError(image)
    master_report = json.loads(args.master_report.read_text())
    run_report_path = args.candidate.parent / 'run-report.json'
    run_report = json.loads(run_report_path.read_text())
    public_audit = json.loads(args.audit_receipt.read_text())
    build = json.loads(args.build_report.read_text())
    master_hash, candidate_hash = sha256(args.master), sha256(args.candidate)
    if (master_hash != master_report['mesh_sha256'] or master_hash != run_report['input_sha256']
            or candidate_hash != run_report['roundtrip']['sha256'] or run_report['transform'] != 'identity'
            or not run_report['input_unchanged']
            or sha256(args.build_report) != public_audit['artifacts_sha256']['build_report']
            or master_report['source_STEP_sha256'] != public_audit['artifacts_sha256']['four_seat_body_final']):
        raise ValueError('private_geometry_or_axis_provenance_mismatch')
    selected_axes = [item for item in build['tools_private'] if item['name'] in ('intake_1', 'exhaust_1')]
    if len(selected_axes) != 2:
        raise ValueError('two_reference_bore_axes_required')
    cut_x = selected_axes[0]['axis_origin'][0]
    if any(abs(item['axis_origin'][0] - cut_x) > 1e-12 or abs(item['axis_direction'][0]) > 1e-12
           for item in selected_axes):
        raise ValueError('chosen_X_plane_does_not_contain_both_actual_bore_axes')
    master, summary_a = read_mesh(args.master)
    candidate, summary_b = read_mesh(args.candidate)
    if len(candidate.faces) != run_report['roundtrip']['triangles']:
        raise ValueError('candidate_triangle_count_mismatch')
    bounds = np.array([np.minimum(master.bounds[0], candidate.bounds[0]),
                       np.maximum(master.bounds[1], candidate.bounds[1])])
    center = bounds.mean(axis=0)
    span = float((bounds[1] - bounds[0]).max())
    titles = ['Maître STEP triangulé — inchangé',
              f"PicoGK — voxel {run_report['voxel_mm']:g} unité du scan"]
    colors = ['#a4b8c4', '#b6976a']
    plotter = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(1800, 820), border=False)
    try:
        for index, mesh in enumerate((master, candidate)):
            plotter.subplot(0, index)
            plotter.set_background('#f3f5f6')
            faces = np.column_stack((np.full(len(mesh.faces), 3, dtype=np.int64), mesh.faces)).ravel()
            display = pv.PolyData(mesh.vertices, faces, deep=True)
            if display.n_cells != len(mesh.faces):
                raise ValueError('display_triangle_count_changed')
            plotter.add_mesh(display, color=colors[index], opacity=1.0, show_edges=False,
                             smooth_shading=False, ambient=.25, diffuse=.7, specular=.25, specular_power=25)
            plotter.camera_position = [center + span * np.array([1.3, -1.65, 1.2]), center, [0, 0, 1]]
            plotter.enable_parallel_projection()
            plotter.camera.parallel_scale = span * .56
            plotter.reset_camera_clipping_range()
        pixels = plotter.screenshot(return_img=True)
    finally:
        plotter.close()
    fig = plt.figure(figsize=(16, 12), facecolor='#f3f5f6')
    grid = fig.add_gridspec(2, 1, height_ratios=[1.1, 1], hspace=.16)
    top = fig.add_subplot(grid[0]); top.imshow(pixels); top.set_axis_off()
    top.text(.25, 1.015, titles[0], transform=top.transAxes, ha='center', fontsize=14)
    top.text(.75, 1.015, titles[1], transform=top.transAxes, ha='center', fontsize=14)
    section_ax = fig.add_subplot(grid[1])
    segment_counts = []
    for mesh, color, label, style in ((master, '#2d647f', 'Maître', '-'),
                                      (candidate, '#b47724', 'PicoGK', '--')):
        section = mesh.section(plane_origin=[cut_x, 0, 0], plane_normal=[1, 0, 0])
        if section is None:
            raise ValueError('empty_bore_section')
        lines = section.discrete
        segment_counts.append(len(lines))
        for index, line in enumerate(lines):
            section_ax.plot(line[:, 1], line[:, 2], color=color, ls=style, lw=1.2,
                            label=label if index == 0 else None)
    for axis in selected_axes:
        origin, direction = np.array(axis['axis_origin']), np.array(axis['axis_direction'])
        points = np.array([origin + parameter * direction for parameter in (-3, 78)])
        section_ax.plot(points[:, 1], points[:, 2], color='#708087', lw=.8, ls=':')
        name = 'Admission 1' if axis['name'].startswith('intake') else 'Échappement 1'
        section_ax.text(points[-1, 1], 86, name, ha='center', fontsize=10, color='#44555c')
    section_ax.set_aspect('equal'); section_ax.grid(alpha=.18); section_ax.legend(loc='lower left')
    section_ax.set_xlabel('Y — unité du scan'); section_ax.set_ylabel('Z — unité du scan')
    section_ax.set_ylim(-3, 90)
    section_ax.set_title('Coupe réelle dans les axes des logements de sièges et guides', fontsize=14)
    fig.suptitle('Culasse 4V issue du scan 935 — préparation géométrique PicoGK', fontsize=20, weight='bold', y=.985)
    fig.text(.5, .023, 'Même géométrie source, rendu opaque avec profondeur VTK ; aucune décimation.\n'
             'Échelle 1 unité/mm hypothétique. Corps incomplet : ni validation moteur ni autorisation de fabrication.',
             ha='center', fontsize=11, color='#4b5961')
    fig.subplots_adjust(top=.915, bottom=.105, left=.06, right=.985)
    fig.savefig(image, dpi=130); plt.close(fig); image.chmod(0o600)
    if sha256(args.master) != master_hash or sha256(args.candidate) != candidate_hash:
        raise ValueError('source_mesh_changed_during_render')
    report = {
        'schema': 'm64-private-picogk-depth-correct-preview/v1',
        'master_STL_sha256': master_hash, 'candidate_STL_sha256': candidate_hash,
        'run_report_sha256': sha256(run_report_path), 'source_build_report_sha256': sha256(args.build_report),
        'render_source_sha256': sha256(Path(__file__)), 'image_sha256': sha256(image),
        'pyvista_version': pv.__version__, 'VTK_version': vtk.vtkVersion.GetVTKVersion(),
        'source_triangle_counts': [len(master.faces), len(candidate.faces)],
        'all_triangles_rendered': True, 'opaque_depth_buffer_render': True,
        'geometry_decimated_or_smoothed': False, 'master_and_candidate_unchanged': True,
        'section_plane_X_scan_units_private': cut_x,
        'section_contains_reference_axes': [item['name'] for item in selected_axes],
        'section_closed_path_counts': segment_counts,
        'three_resolution_comparison_performed': False, 'thermal_field': False,
        'manufacturing_authorized': False,
    }
    receipt_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n'); receipt_path.chmod(0o600)
    print(json.dumps({'image': str(image), 'image_sha256': report['image_sha256'],
                      'source_triangle_counts': report['source_triangle_counts']}), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('master', 'master-report', 'candidate', 'build-report', 'audit-receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
