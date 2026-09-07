#!/usr/bin/env python3
"""Private before/after CAD view of one rejected local port-fillet experiment."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_new_face_ids(identities):
    """Do not let a stale/mutated colour list relabel an original carrier."""
    before = identities['records']['before']['BSpline_carrier_signatures']
    after = identities['records']['after']['BSpline_carrier_signatures']
    old_signatures = set(before.values())
    expected = {int(key) for key, value in after.items() if value not in old_signatures}
    selected = identities['new_BSpline_carrier_face_ids_after']
    if (not expected or not all(isinstance(i, int) and not isinstance(i, bool) and i > 0
                               for i in selected)
            or len(selected) != len(set(selected)) or set(selected) != expected
            or len(selected) != identities['expected_generated_faces_from_builder_history']
            or identities['identified_by_full_degree_poles_weights_knots_mults_not_index_transfer'] is not True):
        raise ValueError('New face list disagrees with carrier comparison or builder history')
    return selected


def render(args):
    import numpy as np
    import pyvista as pv
    import vtk

    receipt = json.loads(args.receipt.read_text())
    identities = json.loads(args.face_ids.read_text())
    report = json.loads(args.report.read_text())
    if report['status'] != 'rejected_native_or_tolerance_audit':
        raise ValueError('This view labels only the tolerance-rejected prototype')
    if args.output.exists():
        raise FileExistsError(args.output)
    if (identities['records']['before']['BRep_sha256'] != receipt['inputs_sha256']['source']
            or identities['records']['after']['BRep_sha256'] != receipt['inputs_sha256']['prototype']
            or report['candidate_BRep_sha256'] != receipt['inputs_sha256']['prototype']):
        raise ValueError('CAD identity mismatch')
    meshes = {}
    for name in ('before', 'after'):
        row = receipt['meshes'][name]
        path = args.receipt.parent / (name + '.npz')
        if sha(path) != row['sha256']:
            raise ValueError('Mesh identity mismatch')
        with np.load(path, allow_pickle=False) as data:
            points = data['points']
            triangles = data['triangles']
            ids = data['original_face_id']
            if (not np.isfinite(points).all() or len(triangles) != row['triangles']
                    or len(ids) != len(triangles)
                    or len(np.unique(ids)) != row['faces']):
                raise ValueError('Incomplete tessellation')
            mesh = pv.PolyData(points, np.column_stack((np.full(len(triangles), 3), triangles)))
            mesh.cell_data['native_face_id'] = ids
            meshes[name] = mesh
    new_face_ids = checked_new_face_ids(identities)
    if not set(new_face_ids) <= set(meshes['after'].cell_data['native_face_id']):
        raise ValueError('An identified new face is missing from the displayed mesh')
    selected = np.isin(meshes['after'].cell_data['native_face_id'], new_face_ids)
    generated = meshes['after'].extract_cells(selected)
    if generated.n_cells == 0:
        raise ValueError('No new face available for focus')
    focus = np.array(generated.center)
    span = np.array(generated.bounds)[1::2] - np.array(generated.bounds)[::2]
    display_radius = max(span)
    section_x = float(focus[0] - .35 * span[0])
    changed_section = generated.slice(normal=(1, 0, 0), origin=(section_x, 0, 0))
    if not changed_section.n_cells:
        raise ValueError('Chosen display section misses local fillet')
    points = changed_section.points
    # Tight camera around the lower changed section, not a geometric crop or refit.
    lower = points[points[:, 2] <= points[:, 2].min() + 1.5]
    section_focus = np.mean(lower, axis=0)
    plot = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(2700, 1100), border=False)
    grey, orange, white, bg = '#aebdca', '#f5ac47', '#e8f0f5', '#111d29'

    def label(text, **kwargs):
        actor = plot.add_text(text, **kwargs)
        # Opaque text backing preserves legibility over the unaltered CAD view.
        prop = actor.GetTextProperty()
        prop.SetBackgroundColor(17/255, 29/255, 41/255)
        prop.SetBackgroundOpacity(.95)

    for column, name in enumerate(('before', 'after')):
        plot.subplot(0, column)
        plot.background_color = bg
        if name == 'before':
            plot.add_mesh(meshes[name], color=grey, smooth_shading=False, ambient=.3,
                          specular=.1, show_edges=False)
        else:
            plot.add_mesh(meshes[name].extract_cells(~selected), color=grey,
                          smooth_shading=False, ambient=.3, specular=.1)
            plot.add_mesh(generated, color=orange, smooth_shading=False, ambient=.4,
                          specular=.1)
        plot.camera_position = [tuple(focus + display_radius * np.array([-.75, -2., .45])),
                                tuple(focus), (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = display_radius * .64
        label('AVANT - EPAULEMENT BRUSQUE' if name == 'before'
                      else 'APRES - CONGE LOCAL R1', position='upper_left',
                      font_size=18, color=white)
        label('Volume du passage de gaz\nCe n est pas le corps de culasse',
                      position='lower_left', font_size=14, color=white)
    plot.subplot(0, 2)
    plot.background_color = bg
    section_counts = {}
    for name, color, width in (('before', white, 4), ('after', orange, 3)):
        section = meshes[name].slice(normal=(1, 0, 0), origin=(section_x, 0, 0))
        section_counts[name] = section.n_cells
        plot.add_mesh(section, color=color, line_width=width, lighting=False,
                      label='Avant' if name == 'before' else 'Apres')
    plot.camera_position = [tuple(section_focus + np.array([-100., 0, 0])),
                            tuple(section_focus), (0, 0, 1)]
    plot.enable_parallel_projection()
    plot.camera.parallel_scale = 3.0
    label('COUPE YZ - DETAIL DU RACCORD\nBlanc : avant ; orange : apres',
                  position='upper_left', font_size=18, color=white)
    label('R = 1 unite du scan (hypothese)\nVue rapprochee, echelle absolue non certifiee',
                  position='lower_left', font_size=14, color=white)
    for column in range(3):
        plot.subplot(0, column)
        label('PROTOTYPE REJETE : tolerances natives augmentees\nAucun resultat CFD / thermique / fabrication',
                      position=(.02, .12), viewport=True, font_size=12, color=orange)
    args.output.mkdir(parents=True, mode=0o700)
    image = args.output / 'intake-local-fillet-before-after.png'
    plot.show(screenshot=str(image), auto_close=True)
    image.chmod(0o600)
    result = {
        'schema':'private-local-fillet-view/v1', 'script_sha256':sha(__file__),
        'tessellation_receipt_sha256':sha(args.receipt),
        'native_face_id_receipt_sha256':sha(args.face_ids),
        'fillet_report_sha256':sha(args.report),
        'native_BRep_hashes':{k:v['BRep_sha256'] for k,v in identities['records'].items()},
        'mesh_hashes':{k:v['sha256'] for k,v in receipt['meshes'].items()},
        'triangle_counts':{k:v.n_cells for k,v in meshes.items()},
        'new_face_ids':identities['new_BSpline_carrier_face_ids_after'],
        'section_X_private':section_x, 'section_focus_private':section_focus.tolist(),
        'section_cell_counts':section_counts, 'section_is_tessellated_not_analytic':True,
        'all_input_triangles_used':True, 'coordinate_transform_or_smoothing':False,
        'camera_zoom_only_not_CAD_modification':True,
        'colours_are_physics_results':False, 'tolerance_rejection_retained':True,
        'image_sha256':sha(image), 'manufacturing_authorized':False,
        'PyVista_version':pv.__version__, 'VTK_version':vtk.vtkVersion.GetVTKVersion()}
    output = args.output / 'render-receipt.json'
    with output.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    output.chmod(0o600)
    print(json.dumps({'image':str(image), 'image_sha256':result['image_sha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('receipt', 'face-ids', 'report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    render(parser.parse_args())
