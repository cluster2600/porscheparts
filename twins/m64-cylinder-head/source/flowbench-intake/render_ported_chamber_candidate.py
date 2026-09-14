#!/usr/bin/env python3
"""Private native-body render; display clipping is not a production CAD cut."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    path.chmod(0o600)


def extract(args):
    import numpy as np
    import OCP
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
    from OCP.TopExp import TopExp
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS, TopoDS_Shape
    start = time.monotonic()
    report_path = args.trial / 'ported-chamber-report.json'
    report = json.loads(report_path.read_text())
    exported = report['exports']['candidate_native']
    source = args.trial / exported['file']
    if report['stage'] != 'complete' or sha(source) != exported['sha256']:
        raise ValueError('completed native source binding required')
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(source), BRep_Builder()):
        raise ValueError('native BRep read failed')
    solids = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_SOLID, solids)
    if solids.Extent() != 1 or not BRepCheck_Analyzer(shape, True).IsValid():
        raise ValueError('native BRep must be valid and one solid')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    mesh_job = BRepMesh_IncrementalMesh(shape, .18, False, .25, False)
    if not mesh_job.IsDone():
        raise ValueError('tessellation incomplete')
    faces = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    wall_ids = set(report['new_cavity_wall_face_ids_private'])
    if not wall_ids or min(wall_ids) < 1 or max(wall_ids) > faces.Extent():
        raise ValueError('new-wall IDs out of native face range')
    points, triangles, ids = [], [], []
    for index in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(index))
        loc = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, loc)
        if mesh is None or mesh.NbTriangles() == 0:
            raise ValueError('empty native face tessellation')
        offset = len(points)
        points.extend(mesh.Node(i).Transformed(loc.Transformation()).Coord()
                      for i in range(1, mesh.NbNodes() + 1))
        for i in range(1, mesh.NbTriangles() + 1):
            a, b, c = mesh.Triangle(i).Get()
            if face.Orientation() == TopAbs_REVERSED:
                b, c = c, b
            triangles.append([offset + a - 1, offset + b - 1, offset + c - 1])
            ids.append(index)
    pts = np.asarray(points, dtype=np.float64)
    if not np.isfinite(pts).all() or len(triangles) > 2000000:
        raise ValueError('finite-coordinate or render-budget guard failed')
    output = args.output / 'body-native-faces.npz'
    np.savez_compressed(output, points=pts, triangles=np.asarray(triangles, dtype=np.int64),
                        original_face_id=np.asarray(ids, dtype=np.int32))
    output.chmod(0o600)
    if sha(source) != exported['sha256']:
        raise ValueError('native master changed during extraction')
    receipt = {'schema': 'private-ported-chamber-tessellation/v1',
               'source_sha256': sha(__file__), 'report_sha256': sha(report_path),
               'native_BRep_sha256': sha(source), 'OCP_version': OCP.__version__,
               'mesh_sha256': sha(output), 'all_native_faces': faces.Extent(),
               'triangle_count': len(triangles), 'point_count': len(points),
               'linear_deflection_scan_units': .18, 'relative_deflection': False,
               'angular_deflection_radians': .25, 'transform_applied': False,
               'new_wall_face_ids_private': sorted(wall_ids),
               'smoothing': False, 'decimation': False,
               'wall_seconds': time.monotonic() - start}
    write_json(args.output / 'tessellation-receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('all_native_faces', 'triangle_count', 'wall_seconds')}))


def render(args):
    import numpy as np
    import pyvista as pv
    import vtk
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    report_path = args.trial / 'ported-chamber-report.json'
    report = json.loads(report_path.read_text())
    tess_path = args.meshes / 'tessellation-receipt.json'
    tess = json.loads(tess_path.read_text())
    path = args.meshes / 'body-native-faces.npz'
    if sha(report_path) != tess['report_sha256'] or sha(path) != tess['mesh_sha256']:
        raise ValueError('native render binding mismatch')
    manifest_path = args.components / 'tessellation-report.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['module_STEP_sha256'] != report['inputs_sha256']['module']:
        raise ValueError('exact V2 component module required')
    if manifest['module_lifts_design_mm'] != {'intake': 6., 'exhaust': 0.}:
        raise ValueError('expected intake6/exhaust0 component positions')
    if args.output.exists():
        raise FileExistsError(args.output)
    with np.load(path) as data:
        points, triangles, ids = data['points'], data['triangles'], data['original_face_id']
    def poly(selected):
        return pv.PolyData(points, np.column_stack((np.full(len(selected), 3), selected)))
    new = np.isin(ids, tess['new_wall_face_ids_private'])
    body_all = poly(triangles)
    parts = [('Corps', 'body', poly(triangles[~new])),
             ('Parois admission', 'intake', poly(triangles[new]))]
    component_hashes = {}
    for item in manifest['parts']:
        if item['name'] == 'body' or item['role'] == 'body':
            continue
        source = args.components / item['filename']
        if sha(source) != item['sha256']:
            raise ValueError('component mesh hash mismatch')
        mesh = pv.read(source)
        if not mesh.is_all_triangles or not np.isfinite(mesh.points).all():
            raise ValueError('invalid component mesh')
        parts.append((item['name'], item['role'], mesh))
        component_hashes[item['name']] = item['sha256']
    if len(component_hashes) != 12:
        raise ValueError('twelve genuine V2 components required; previous body excluded')
    palette = {'body': '#aeb6be', 'intake': '#258dcb', 'valve': '#d2d7dc',
               'seat': '#dbac54', 'guide': '#906aad'}
    xyz = body_all.points
    lo, hi = xyz.min(axis=0), xyz.max(axis=0)
    span = float(max(hi - lo))
    center = (lo + hi) / 2
    fig = plt.figure(figsize=(16, 10), facecolor='#111c26')
    for panel in range(2):
        plot = pv.Plotter(off_screen=True, window_size=(1350, 1150))
        plot.background_color = '#111c26'
        for name, role, mesh in parts:
            shown = mesh if panel == 0 else mesh.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=False)
            if shown.n_cells == 0:
                continue
            plot.add_mesh(shown, color=palette[role], smooth_shading=False,
                          show_edges=False, ambient=.35, diffuse=.65, specular=.15)
        if panel:
            cut = body_all.slice(normal=(1, 0, 0), origin=(0, 0, 0))
            if cut.n_cells:
                plot.add_mesh(cut, color='#e8eff4', line_width=1.2)
        direction = np.array([1.5, 1.8, 1.1]) if panel == 0 else np.array([-2.3, 1.0, .55])
        focus = center if panel == 0 else center + np.array([span * .07, 0, 0])
        plot.camera_position = [tuple(focus + span * direction), tuple(focus), (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = span * .58
        plot.enable_anti_aliasing('ssaa')
        pixels = plot.screenshot(return_img=True)
        plot.close()
        ax = fig.add_axes([.005 + panel * .5, .205, .49, .65])
        ax.imshow(pixels)
        ax.axis('off')
    fg, muted = '#eef3f6', '#b6c5d2'
    fig.text(.035, .945, 'Candidat CAO — admission évidée dans le corps réel',
             fontsize=23, color=fg, weight='bold')
    fig.text(.035, .897, '01 · Vue du corps et des 12 composants V2', fontsize=13, color=muted)
    fig.text(.535, .897, '02 · Demi-coupe visuelle X = 0 · moitié X ≥ 0 affichée', fontsize=13, color=muted)
    labels = [('body', 'Corps, gris illustratif'), ('intake', 'Nouvelles parois admission'),
              ('valve', 'Soupapes'), ('seat', 'Sièges'), ('guide', 'Guides')]
    legend = fig.legend(handles=[Patch(color=palette[r], label=l) for r, l in labels],
                        loc='lower center', bbox_to_anchor=(.5, .145), ncol=5,
                        frameon=False, fontsize=11)
    for text in legend.get_texts():
        text.set_color(fg)
    fig.text(.035, .112, 'Échappement non reconstruit. Export STEP invalide et maintien des guides d’admission à vérifier.',
             fontsize=12, color='#ffb2a4')
    fig.text(.035, .079, 'Admission 6 mm / échappement fermé (hypothèses) · coupe du maillage à l’affichage, pas une modification CAO.',
             fontsize=11, color=muted)
    fig.text(.035, .048, 'CAO native : 1 solide valide. Aucun résultat CFD, thermique ou résistance ; aucune autorisation de fabrication.',
             fontsize=11, color=muted)
    fig.text(.035, .019, 'Référence scan 935 · échelle 1 unité/mm non vérifiée · interfaces M64 non certifiées · gris ≠ sélection de matériau',
             fontsize=10, color=muted)
    fig.savefig(args.output, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    args.output.chmod(0o600)
    receipt = {'schema': 'private-ported-chamber-render/v1', 'source_sha256': sha(__file__),
               'native_BRep_sha256': tess['native_BRep_sha256'], 'candidate_report_sha256': sha(report_path),
               'tessellation_receipt_sha256': sha(tess_path), 'mesh_sha256': sha(path),
               'component_manifest_sha256': sha(manifest_path), 'component_STL_sha256': component_hashes,
               'old_body_excluded': True, 'module_lifts_design_mm': manifest['module_lifts_design_mm'],
               'image_sha256': sha(args.output), 'source_status': report['status'],
               'new_cavity_faces_shown': len(tess['new_wall_face_ids_private']),
               'renderer': 'PyVista/VTK_z_buffer_no_smoothing_no_decimation',
               'PyVista_version': pv.__version__, 'VTK_version': vtk.vtkVersion.GetVTKVersion(),
               'display_cut': {'origin': [0, 0, 0], 'normal': [1, 0, 0], 'retained': 'X>=0',
                               'capped': False, 'production_CAD_changed': False},
               'categorical_colours_not_scientific_fields': True,
               'invalid_STEP_used': False, 'geometry_modified': False, 'generative_image': False,
               'manufacturing_authorized': False}
    write_json(args.output.with_suffix('.json'), receipt)
    print(json.dumps({'image_sha256': receipt['image_sha256'], 'receipt_sha256': sha(args.output.with_suffix('.json'))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ext = sub.add_parser('extract')
    for name in ('trial', 'output'):
        ext.add_argument('--' + name, required=True, type=Path)
    rend = sub.add_parser('render')
    for name in ('trial', 'meshes', 'components', 'output'):
        rend.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    (extract if args.command == 'extract' else render)(args)
