#!/usr/bin/env python3
"""Render private native port-routing CAD; categorical colours are not CAE fields.

Two stages permit OCP and PyVista to run in separate existing environments.
Every B-Rep face is tessellated, without decimation, smoothing or coordinate
transformation. Mesh clipping is display-only and is not a new solid model.
All generated meshes, coordinates, receipts and images must remain private.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
    Path(path).chmod(0o600)


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

    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    started = time.monotonic()
    report = {'schema': 'private-scan-seeded-ports-tessellation/v1',
              'source_script_sha256': sha(__file__), 'OCP_version': OCP.__version__,
              'linear_deflection_scan_units': args.deflection,
              'angular_deflection_radians': 0.3, 'relative_deflection': False,
              'coordinate_transform_applied': False, 'smoothing_applied': False,
              'decimation_applied': False, 'all_faces_required': True,
              'length_unit': 'scan_unit; absolute_mm_scale_unverified',
              'parts': {}, 'manufacturing_authorized': False}
    for role, filename in [('body', 'ported-candidate.brep'),
                           ('intake', 'intake-negative.brep'),
                           ('exhaust', 'exhaust-negative.brep')]:
        path = args.trial / filename
        before = sha(path)
        shape = TopoDS_Shape()
        if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
            raise ValueError('native BRep read failed: ' + role)
        if not BRepCheck_Analyzer(shape, True).IsValid():
            raise ValueError('BRepCheck invalid: ' + role)
        solids = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, TopAbs_SOLID, solids)
        if solids.Extent() != 1:
            raise ValueError('expected one solid: ' + role)
        job = BRepMesh_IncrementalMesh(shape, args.deflection, False, 0.3, False)
        job.Perform()
        if not job.IsDone():
            raise ValueError('tessellation incomplete: ' + role)
        faces = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
        points, triangles, face_ids = [], [], []
        counts = []
        for index in range(1, faces.Extent() + 1):
            face = TopoDS.Face_s(faces.FindKey(index))
            loc = TopLoc_Location()
            mesh = BRep_Tool.Triangulation_s(face, loc)
            if mesh is None or mesh.NbTriangles() == 0:
                raise ValueError('face has no triangles: %s %s' % (role, index))
            offset = len(points)
            points.extend(mesh.Node(i).Transformed(loc.Transformation()).Coord()
                          for i in range(1, mesh.NbNodes() + 1))
            for i in range(1, mesh.NbTriangles() + 1):
                a, b, c = mesh.Triangle(i).Get()
                if face.Orientation() == TopAbs_REVERSED:
                    b, c = c, b
                triangles.append([offset+a-1, offset+b-1, offset+c-1])
                face_ids.append(index)
            counts.append(mesh.NbTriangles())
        vertices = np.asarray(points, dtype=np.float64)
        indices = np.asarray(triangles, dtype=np.int64)
        if not np.isfinite(vertices).all():
            raise ValueError('nonfinite mesh point')
        output = args.output / (role + '.npz')
        np.savez_compressed(output, points=vertices, triangles=indices,
                            original_face_id=np.asarray(face_ids, dtype=np.int32))
        output.chmod(0o600)
        if sha(path) != before:
            raise ValueError('input changed while tessellating')
        report['parts'][role] = {'native_BRep_sha256': before,
                                'mesh_sha256': sha(output), 'face_count': faces.Extent(),
                                'faces_tessellated': len(counts),
                                'point_count': len(points), 'triangle_count': len(triangles),
                                'minimum_triangles_per_face': min(counts),
                                'maximum_triangles_per_face': max(counts),
                                'native_BRepCheck_valid': True, 'native_solid_count': 1,
                                'mesh_bbox_private': [*vertices.min(axis=0), *vertices.max(axis=0)]}
    report['wall_seconds'] = time.monotonic() - started
    write_json(args.output / 'tessellation-receipt.json', report)
    print(json.dumps({k: v['triangle_count'] for k, v in report['parts'].items()}))


def routing_status(trial, tessellation):
    path = trial / 'routing-report.json'
    if not path.exists():
        return 'Controles finaux en cours - prototype non qualifie', None, None
    report = json.loads(path.read_text())
    exported = report['candidate_exports']
    if exported['native_BRep_sha256'] != tessellation['parts']['body']['native_BRep_sha256']:
        raise ValueError('routing report does not describe displayed native body')
    for row in report['bank_records']:
        role = row['kind']
        if row['exports']['native_BRep_sha256'] != tessellation['parts'][role]['native_BRep_sha256']:
            raise ValueError('routing report does not describe displayed port')
    native = exported['native_BOP']['fault_counts']
    step = exported['STEP_BOP']['fault_counts']
    if native:
        line = 'BOP natif : REJET (%d defaut(s))' % sum(native.values())
    else:
        line = 'BOP natif : 0 defaut signale'
    if step:
        line += '; STEP : REJETE (%d defaut(s))' % sum(step.values())
    else:
        line += '; STEP : controles BOP sans defaut signale'
    return line, sha(path), report


def render(args):
    import numpy as np
    import pyvista as pv
    import vtk

    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    receipt = json.loads((args.meshes / 'tessellation-receipt.json').read_text())
    status, routing_sha, routing = routing_status(args.trial, receipt)
    meshes = {}
    for role in ('body', 'intake', 'exhaust'):
        path = args.meshes / (role + '.npz')
        if sha(path) != receipt['parts'][role]['mesh_sha256']:
            raise ValueError('mesh hash mismatch')
        with np.load(path) as source:
            triangles = source['triangles']
            faces = np.column_stack((np.full(len(triangles), 3), triangles))
            meshes[role] = pv.PolyData(source['points'], faces)
        if meshes[role].n_cells != receipt['parts'][role]['triangle_count']:
            raise ValueError('not all extracted triangles were retained')
    body = meshes['body']
    center = np.asarray(body.center)
    span = np.asarray(body.bounds)[1::2] - np.asarray(body.bounds)[::2]
    radius = float(max(span))
    colors = {'body': '#b6bec5', 'intake': '#238ccd', 'exhaust': '#ec8c32'}
    background, text_color = '#111c26', '#edf3f8'

    def add_mesh(plot, mesh, role, **kw):
        return plot.add_mesh(mesh, color=colors[role], smooth_shading=False,
                             show_edges=False, ambient=0.28, diffuse=0.7,
                             specular=0.12, specular_power=20, **kw)

    def setup(plot, position):
        plot.background_color = background
        plot.camera_position = [tuple(center + np.asarray(position)*radius),
                                tuple(center), (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = 0.64*radius

    plot = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2400, 1250),
                      border=False)
    plot.subplot(0, 0)
    add_mesh(plot, body, 'body')
    setup(plot, (-1.8, -2.4, 1.8))
    plot.add_text('EXTERIEUR REEL DU CORPS DECOUPE\nReference 935 + logements 4V exploratoires',
                  position='upper_left', color=text_color, font_size=17)
    plot.add_text('Ailettes conservees ; passages nouvellement decoupes\nNi echelle M64 certifiee, ni validation moteur',
                  position='lower_left', color=text_color, font_size=15)

    plot.subplot(0, 1)
    clipped = body.clip(normal=(1, 0, 0), origin=(args.clip_x, 0, 0), invert=False)
    if not 0 < clipped.n_cells < body.n_cells * 2:
        raise ValueError('empty or unexpected display clip')
    add_mesh(plot, clipped, 'body')
    visible_ports = {}
    for role in ('intake', 'exhaust'):
        # The removed half contains the displayed negatives; no coincident
        # surfaces compete with the retained body in the depth buffer.
        visible_ports[role] = meshes[role].clip(normal=(1, 0, 0),
                                               origin=(args.clip_x, 0, 0), invert=True)
        add_mesh(plot, visible_ports[role], role)
    setup(plot, (-2.4, -1.1, 1.6))
    plot.add_text('DEMI-VUE + VOLUMES NEGATIFS DES CONDUITS\nBleu : admission ; orange : echappement',
                  position='upper_left', color=text_color, font_size=17)
    plot.add_text('Corps conserve X >= %.3g ; noyaux visibles X < %.3g\nCoupe ouverte de visualisation ; aucun changement de CAO' % (args.clip_x, args.clip_x),
                  position='lower_left', color=text_color, font_size=15)
    for column in (0, 1):
        plot.subplot(0, column)
        plot.add_text(status.replace('; ', '\n'), position=(0.02, 0.14), viewport=True,
                      color='#f2c986', font_size=12)
        plot.add_text('Couleurs de reperage, pas un calcul thermique\nNON AUTORISE A IMPRIMER\nConduits, chambre et distribution non qualifies',
                      position=(0.02, 0.075), viewport=True, color='#f2c986', font_size=12)
    image = args.output / 'ported-body-and-passages.png'
    plot.show(screenshot=str(image), auto_close=True)
    image.chmod(0o600)

    # A separate true intersection of the displayed tessellation with a plane.
    # It is not a remeshed solid, an exact analytic section, or a flow solution.
    section = pv.Plotter(off_screen=True, window_size=(1800, 900))
    section.background_color = background
    sections = {}
    for role, mesh in meshes.items():
        sliced = mesh.slice(normal=(1, 0, 0), origin=(args.section_x, 0, 0))
        if sliced.n_cells == 0:
            raise ValueError('section misses required body or port')
        sections[role] = int(sliced.n_cells)
        section.add_mesh(sliced, color=colors[role], line_width=2.5 if role=='body' else 4,
                         lighting=False, label={'body':'Corps', 'intake':'Admission',
                                                'exhaust':'Echappement'}[role])
    section.camera_position = [(args.section_x-radius, center[1], center[2]),
                               (args.section_x, center[1], center[2]), (0, 0, 1)]
    section.enable_parallel_projection()
    section.camera.parallel_scale = 0.30*radius
    section.add_text('COUPE YZ DE LA GEOMETRIE REELLE - X = %.3g unites du scan\nIntersection de tous les triangles, sans lissage ni forme ajoutee' % args.section_x,
                     position='upper_left', font_size=19, color=text_color)
    section.add_text('Gris : corps ; bleu : admission ; orange : echappement\nCourbes colorees : outils de soustraction, pas un fluide calcule.\n%s\nEchelle non certifiee ; ni CFD validee, ni autorisation de fabrication' % status,
                     position='lower_left', font_size=16, color='#f2c986')
    section_image = args.output / 'ported-body-YZ-section.png'
    section.show(screenshot=str(section_image), auto_close=True)
    section_image.chmod(0o600)
    write_json(args.output / 'render-receipt.json', {
        'schema': 'private-native-ported-head-visualization/v1',
        'script_sha256': sha(__file__), 'tessellation_receipt_sha256': sha(args.meshes/'tessellation-receipt.json'),
        'routing_report_sha256': routing_sha, 'routing_status': routing['status'] if routing else 'pending',
        'displayed_status': status, 'native_BRep_hashes': {k:v['native_BRep_sha256'] for k,v in receipt['parts'].items()},
        'input_mesh_hashes': {k:v['mesh_sha256'] for k,v in receipt['parts'].items()},
        'PyVista_version': pv.__version__, 'VTK_version': vtk.vtkVersion.GetVTKVersion(),
        'all_input_triangles_retained': True, 'triangle_counts': {k:int(v.n_cells) for k,v in meshes.items()},
        'display_clip_X_private': args.clip_x, 'section_X_private': args.section_x,
        'clip_body_output_cells': int(clipped.n_cells),
        'negative_clip_output_cells': {k: int(v.n_cells) for k, v in visible_ports.items()},
        'coincident_surfaces_suppressed_by_complementary_display_clips': True,
        'section_cell_counts': sections, 'clipping_changes_model': False,
        'section_is_tessellated_not_analytic': True, 'mesh_smoothing_or_decimation': False,
        'image_sha256': sha(image), 'section_image_sha256': sha(section_image),
        'colours_are_thermal_or_flow_results': False, 'manufacturing_authorized': False,
        'M64_fitment_validated': False})
    print(json.dumps({'image': str(image), 'section': str(section_image), 'status': status}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    first = modes.add_parser('extract')
    first.add_argument('--trial', type=Path, required=True)
    first.add_argument('--output', type=Path, required=True)
    first.add_argument('--deflection', type=float, default=0.18)
    second = modes.add_parser('render')
    second.add_argument('--trial', type=Path, required=True)
    second.add_argument('--meshes', type=Path, required=True)
    second.add_argument('--output', type=Path, required=True)
    second.add_argument('--section-x', type=float, required=True)
    second.add_argument('--clip-x', type=float, required=True)
    args = parser.parse_args()
    if args.mode == 'extract':
        if not math.isfinite(args.deflection) or args.deflection <= 0:
            raise ValueError('positive finite deflection required')
        extract(args)
    else:
        if not math.isfinite(args.section_x) or not math.isfinite(args.clip_x):
            raise ValueError('finite explicit section plane required')
        render(args)


if __name__ == '__main__':
    main()
