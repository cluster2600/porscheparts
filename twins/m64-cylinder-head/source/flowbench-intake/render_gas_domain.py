#!/usr/bin/env python3
"""Private two-stage CAD render; categorical boundary colours are not CFD fields."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
    path.chmod(0o600)


def extract(args):
    import numpy as np
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
    source = args.domain / 'gas-domain-report.json'
    report = json.loads(source.read_text())
    body = args.domain / 'domain.brep'
    expected = report['exports']['domain_brep']['sha256']
    if sha(body) != expected:
        raise ValueError('domain hash mismatch')
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(body), BRep_Builder()):
        raise ValueError('native read failed')
    solids = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_SOLID, solids)
    if solids.Extent() != 1 or not BRepCheck_Analyzer(shape, True).IsValid():
        raise ValueError('expected one valid BRep solid, independent of BOP status')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    rows = report['boundary_faces']
    points, triangles, face_ids = [], [], []
    face_hashes = {}
    for row in rows:
        path = args.domain / row['file']
        if sha(path) != row['sha256']:
            raise ValueError('boundary face hash mismatch')
        face_hashes[str(row['id'])] = row['sha256']
        item = TopoDS_Shape()
        if not BRepTools.Read_s(item, str(path), BRep_Builder()):
            raise ValueError('face read failed')
        faces = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(item, TopAbs_FACE, faces)
        if faces.Extent() != 1:
            raise ValueError('one face required per boundary file')
        mesh_job = BRepMesh_IncrementalMesh(item, .12, False, .22, False)
        if not mesh_job.IsDone():
            raise ValueError('tessellation incomplete')
        face = TopoDS.Face_s(faces.FindKey(1))
        loc = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, loc)
        if mesh is None or mesh.NbTriangles() == 0:
            raise ValueError('untessellated face')
        offset = len(points)
        points.extend(mesh.Node(i).Transformed(loc.Transformation()).Coord()
                      for i in range(1, mesh.NbNodes() + 1))
        for i in range(1, mesh.NbTriangles() + 1):
            a, b, c = mesh.Triangle(i).Get()
            if face.Orientation() == TopAbs_REVERSED:
                b, c = c, b
            triangles.append([offset + a - 1, offset + b - 1, offset + c - 1])
            face_ids.append(row['id'])
    pts = np.asarray(points, dtype=float)
    if not np.isfinite(pts).all() or len(triangles) > 2000000:
        raise ValueError('render budget or finite coordinates failed')
    output = args.output / 'domain-faces.npz'
    np.savez_compressed(output, points=pts, triangles=np.asarray(triangles, dtype=np.int64),
                        face_ids=np.asarray(face_ids, dtype=np.int32))
    output.chmod(0o600)
    if sha(body) != expected:
        raise ValueError('source changed')
    receipt = {'schema': 'private-gas-domain-tessellation/v1',
               'source_script_sha256': sha(__file__), 'domain_sha256': expected,
               'report_sha256': sha(source), 'face_sha256': face_hashes,
               'mesh_sha256': sha(output), 'all_report_faces_tessellated': len(rows),
               'triangles': len(triangles), 'points': len(points),
               'linear_deflection_scan_units': .12, 'angular_deflection_radians': .22,
               'relative': False, 'smoothing': False, 'decimation': False,
               'transform_applied': False, 'wall_seconds': time.monotonic() - start}
    save_json(args.output / 'tessellation-receipt.json', receipt)
    print(json.dumps(receipt))


def render(args):
    import numpy as np
    import pyvista as pv
    import vtk
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    report_path = args.domain / 'gas-domain-report.json'
    report = json.loads(report_path.read_text())
    receipt_path = args.meshes / 'tessellation-receipt.json'
    receipt = json.loads(receipt_path.read_text())
    path = args.meshes / 'domain-faces.npz'
    if sha(report_path) != receipt['report_sha256'] or sha(path) != receipt['mesh_sha256']:
        raise ValueError('render source binding mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    with np.load(path) as data:
        points, triangles, ids = data['points'], data['triangles'], data['face_ids']
    palette = {'walls_port': '#419ed0', 'walls_chamber': '#8ebdcf',
               'walls_receiver': '#a2adb7', 'receiver_outlet': '#778898',
               'inlet': '#244577', 'walls_valve': '#de8a36',
               'walls_seat': '#e7bf6b', 'walls_guide': '#8665ae',
               'fixture_stem_seals': '#8665ae', 'ambiguous': '#cf447e'}
    role_ids = {}
    for row in report['boundary_faces']:
        role_ids.setdefault(row['role'], []).append(row['id'])
    meshes = {}
    for role, indices in role_ids.items():
        selected = triangles[np.isin(ids, indices)]
        meshes[role] = pv.PolyData(points, np.column_stack((np.full(len(selected), 3), selected)))
    fig = plt.figure(figsize=(16, 10), facecolor='#f4f6f8')
    for panel in range(2):
        plot = pv.Plotter(off_screen=True, window_size=(1200, 1080))
        plot.background_color = '#f4f6f8'
        visible = []
        for role, mesh in meshes.items():
            if panel and role in ('walls_receiver', 'receiver_outlet'):
                continue
            plot.add_mesh(mesh, color=palette[role], smooth_shading=False,
                          opacity=1., show_edges=False, ambient=.32, diffuse=.68,
                          specular=.15)
            # Bounds of used triangles, not the shared unused point array.
            used = np.unique(triangles[np.isin(ids, role_ids[role])])
            visible.append(points[used])
        xyz = np.concatenate(visible)
        lo, hi = xyz.min(axis=0), xyz.max(axis=0)
        center = (lo + hi) / 2
        span = max(hi - lo)
        direction = np.array([1.4, 1.8, 1.0]) if panel == 0 else np.array([1.0, 1.3, -.95])
        plot.camera_position = [tuple(center + span * direction), tuple(center), (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = span * .65
        if panel:
            rows = [r for r in report['boundary_faces'] if r['role'] == 'ambiguous']
            plot.add_point_labels(np.asarray([r['center'] for r in rows]),
                                  [str(r['id']) for r in rows], font_size=15,
                                  text_color='#552038', point_color='#cf447e',
                                  point_size=5, shape_color='white', shape_opacity=.85,
                                  always_visible=True)
        plot.enable_anti_aliasing('ssaa')
        pixels = plot.screenshot(return_img=True)
        plot.close()
        ax = fig.add_axes([.01 + panel * .5, .21, .49, .65])
        ax.imshow(pixels)
        ax.axis('off')
    fig.text(.035, .945, 'Volume d’air de banc — géométrie candidate, pas de CFD',
             fontsize=21, weight='bold', color='#202b37')
    fig.text(.035, .899, '01 · Conduits, chambre et récepteur de banc', fontsize=13, color='#354554')
    fig.text(.535, .899, '02 · Vue par-dessous — récepteur masqué à l’affichage', fontsize=13, color='#354554')
    labels = [('walls_port', 'Conduits'), ('walls_chamber', 'Chambre'),
              ('walls_receiver', 'Récepteur de banc'), ('inlet', 'Entrée'),
              ('walls_valve', 'Parois soupapes'), ('walls_seat', 'Parois sièges'),
              ('walls_guide', 'Guides / bouchons de banc'), ('ambiguous', '4 faces ambiguës : 3, 6, 9, 14')]
    fig.legend(handles=[Patch(color=palette[r], label=l) for r, l in labels],
               loc='lower center', bbox_to_anchor=(.5, .12), ncol=4,
               frameon=False, fontsize=11)
    fig.text(.035, .084, 'CAO native : 1 solide BRep valide. Rejet du rapport 05 : continuité C0 et affectations en revue.',
             fontsize=11, color='#973c3b')
    fig.text(.035, .052, 'Admission ouverte de 6 mm (hypothèse). Couleurs = fonctions, jamais vitesse / pression / température.',
             fontsize=11, color='#536170')
    fig.text(.035, .021, 'Référence de scan 935 · échelle 1 unité/mm non vérifiée · récepteur ≠ piston · ni montage M64 ni fabrication validés',
             fontsize=10, color='#536170')
    fig.savefig(args.output, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    args.output.chmod(0o600)
    result = {'schema': 'private-gas-domain-render/v1', 'source_sha256': sha(__file__),
              'domain_sha256': receipt['domain_sha256'], 'report_sha256': sha(report_path),
              'tessellation_receipt_sha256': sha(receipt_path), 'mesh_sha256': sha(path),
              'image_sha256': sha(args.output), 'source_status': report['status'],
              'ambiguous_face_ids': [r['face'] for r in report['ambiguous_faces']],
              'palette': palette, 'renderer': 'PyVista/VTK z-buffer',
              'PyVista_version': pv.__version__, 'VTK_version': vtk.vtkVersion.GetVTKVersion(),
              'geometry_modified': False, 'display_only_hidden_roles_right': ['walls_receiver', 'receiver_outlet'],
              'generative_image': False, 'CFD_field': False, 'manufacturing_authorized': False}
    save_json(args.output.with_suffix('.json'), result)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ext = sub.add_parser('extract')
    ext.add_argument('--domain', required=True, type=Path)
    ext.add_argument('--output', required=True, type=Path)
    rend = sub.add_parser('render')
    for name in ('domain', 'meshes', 'output'):
        rend.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    (extract if args.command == 'extract' else render)(args)
