#!/usr/bin/env python3
"""Private V5 + exact V2 assembly checkpoint, not a complete engineered head.

Tessellation and camera approach adapted from render_ported_chamber_candidate.py
c90e8a74f0f868a01498ed196e6a5832bdd009c307db9b7de192237221835311.
No historical body-face IDs or coloured cavity assignments are reused.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

PINS = {
    'candidate.binbrep': '450ba0816bf355f350b45e1878e3327f2070cd10b405f885afb3ef2c026bff0e',
    'closed.step': 'fac380b277add2e3d265d7fa8265baeb0ce460b9f69075730d14ece555e76a76',
    'registration.json': 'ca2d8656f343f5e61d124d511e6a446190b24fb010ef484ce3c8bc5fb8bb3eb2',
    'v5-report.json': 'e88aa2b231ef2307e2ea9caf27dbdf5a173fcf2f7f59b7fd062b695b781f677a',
    'geometry-checkpoint.json': '2dc337465f6949c8620482e530b623021647cd7522d1ecab3139fb5599be09ac',
}
REGISTRATION = {'scale_scan_units_per_mm_hypothesis': 1., 'rotation_Z_deg_hypothesis': -90., 'translation_Z_hypothesis': 3.}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    path.chmod(0o600)


def preflight(root):
    for name, expected in PINS.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError('exact_input_required_' + name)
    registration = json.loads((root / 'registration.json').read_text())
    prior = json.loads((root / 'v5-report.json').read_text())
    checkpoint = json.loads((root / 'geometry-checkpoint.json').read_text())
    if registration['registration'] != REGISTRATION or registration['module_sha256'] != PINS['closed.step']:
        raise ValueError('exact_V2_registration_required')
    if prior['candidate_sha256'] != PINS['candidate.binbrep']:
        raise ValueError('V5_producer_binding_failed')
    bop = checkpoint['saved_candidate_independent_BOP']
    if bop['candidate_sha256'] != PINS['candidate.binbrep'] or bop['prior_report_sha256'] != PINS['v5-report.json'] or bop['BOP_has_faulty'] or bop['BOP_has_errors']:
        raise ValueError('latest_V5_diagnostic_binding_failed')
    rows = registration['components_imported_from_exact_STEP']
    expected = {f'{bank}_{i}_{role}' for bank in ('intake', 'exhaust') for i in (1, 2) for role in ('valve', 'seat', 'guide')}
    if len(rows) != 12 or {r['name'] for r in rows} != expected or {r['imported_module_solid_id'] for r in rows} != set(range(1, 13)):
        raise ValueError('exact_twelve_distinct_V2_parts_required')
    return rows


def run(root, out, source_sha):
    import numpy as np
    import OCP
    import pyvista as pv
    import vtk
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BinTools import BinTools, BinTools_FormatVersion_VERSION_3
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
    from OCP.TopExp import TopExp
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Compound
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('exact_OCP_runtime_required')
    start = time.monotonic()
    rows = preflight(root)
    def indexed(shape, kind):
        table = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, kind, table)
        return [table.FindKey(i) for i in range(1, table.Extent() + 1)]
    def valid(shape):
        return not shape.IsNull() and BRepCheck_Analyzer(shape, True, False, True).IsValid()
    body = TopoDS_Shape()
    if not BinTools.Read_s(body, str(root / 'candidate.binbrep')) or not valid(body) or len(indexed(body, TopAbs_SOLID)) != 1:
        raise ValueError('one_valid_V5_body_required')
    reader = STEPControl_Reader()
    if reader.ReadFile(str(root / 'closed.step')) != IFSelect_RetDone or reader.TransferRoots() <= 0:
        raise ValueError('exact_module_STEP_read_failed')
    solids = indexed(reader.OneShape(), TopAbs_SOLID)
    if len(solids) != 12 or not all(valid(s) for s in solids):
        raise ValueError('twelve_valid_module_solids_required')
    transform = gp_Trsf()
    transform.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
    transform.SetTranslationPart(gp_Vec(0, 0, 3))
    parts = [('body_v5', 'body', body, 0)]
    for row in sorted(rows, key=lambda r: r['imported_module_solid_id']):
        index = row['imported_module_solid_id']
        placed = BRepBuilderAPI_Transform(solids[index - 1], transform, True).Shape()
        if not valid(placed):
            raise ValueError('registered_component_invalid')
        parts.append((row['name'], row['name'].rsplit('_', 1)[1], placed, index))
    # New compound only: no fuse, cut, healing, material addition or master export.
    builder = BRep_Builder()
    assembly = TopoDS_Compound()
    builder.MakeCompound(assembly)
    for _, _, shape, _ in parts:
        builder.Add(assembly, shape)
    assembly_path = out / 'v5-v2-integration-checkpoint.binbrep'
    if len(indexed(assembly, TopAbs_SOLID)) != 13 or not valid(assembly):
        raise ValueError('thirteen_valid_assembly_solids_required')
    if not BinTools.Write_s(assembly, str(assembly_path), False, False, BinTools_FormatVersion_VERSION_3):
        raise ValueError('new_assembly_write_failed')
    reread = TopoDS_Shape()
    if not BinTools.Read_s(reread, str(assembly_path)) or len(indexed(reread, TopAbs_SOLID)) != 13 or not valid(reread):
        raise ValueError('new_assembly_readback_failed')
    manifest = {'schema': 'private-V5-V2-integration-checkpoint/v1', 'source_sha256': source_sha,
                'inputs_sha256': PINS, 'OCP_version': OCP.__version__, 'assembly_sha256': sha(assembly_path),
                'assembly_bytes': assembly_path.stat().st_size, 'native_format': 'BinTools_VERSION_3_no_triangulations_no_normals',
                'solid_count_before_and_after': 13, 'BRep_exact_valid_before_and_after': True,
                'global_serialization_geometry_equivalence_proven': False, 'parts': [],
                'registration_hypothesis': REGISTRATION, 'module_lifts_design_mm': {'intake': 0., 'exhaust': 0.},
                'body_transform_applied': False, 'old_pocket_and_intake_only_bodies_excluded': True,
                'Boolean_or_healing_performed': False, 'body_master_modified': False,
                'missing_integration': ['springs', 'camshafts_and_actuation', 'oil_circuits'],
                'scale_or_M64_interfaces_certified': False, 'manufacturing_authorized': False,
                'classification': 'integration_checkpoint_not_complete_head'}
    meshes = []
    for ordinal, (name, role, shape, source_id) in enumerate(parts, 1):
        job = BRepMesh_IncrementalMesh(shape, .18, False, .25, False)
        if not job.IsDone():
            raise ValueError('native_tessellation_incomplete_' + name)
        points, triangles = [], []
        faces = indexed(shape, TopAbs_FACE)
        for raw in faces:
            face = TopoDS.Face_s(raw)
            loc = TopLoc_Location()
            mesh = BRep_Tool.Triangulation_s(face, loc)
            if mesh is None or mesh.NbTriangles() == 0:
                raise ValueError('missing_native_face_mesh_' + name)
            offset = len(points)
            points.extend(mesh.Node(i).Transformed(loc.Transformation()).Coord() for i in range(1, mesh.NbNodes() + 1))
            for i in range(1, mesh.NbTriangles() + 1):
                a, b, c = mesh.Triangle(i).Get()
                if face.Orientation() == TopAbs_REVERSED:
                    b, c = c, b
                triangles.append([offset + a - 1, offset + b - 1, offset + c - 1])
        xyz = np.asarray(points, dtype=np.float64)
        tris = np.asarray(triangles, dtype=np.int64)
        if not np.isfinite(xyz).all() or len(tris) > 2000000:
            raise ValueError('render_budget_or_coordinate_failure')
        target = out / (name + '.npz')
        np.savez_compressed(target, points=xyz, triangles=tris)
        meshes.append((name, role, pv.PolyData(xyz, np.column_stack((np.full(len(tris), 3), tris)))))
        manifest['parts'].append({'name': name, 'role': role, 'assembly_solid_id': ordinal,
                                  'original_module_solid_id': source_id or None, 'module_transform_applied_once': role != 'body',
                                  'mesh_file': target.name, 'mesh_sha256': sha(target), 'native_faces': len(faces),
                                  'triangles': len(tris), 'points': len(xyz)})
    manifest['tessellation'] = {'linear_deflection_scan_units': .18, 'relative_deflection': False,
                                'angular_deflection_radians': .25, 'smoothing': False, 'decimation': False,
                                'historical_face_IDs_reused': False}
    save(out / 'assembly-and-tessellation.json', manifest)
    palette = {'body': '#aeb6be', 'valve': '#67bec5', 'seat': '#dbac54', 'guide': '#ad8ad1'}
    body_mesh = meshes[0][2]
    xyz = np.concatenate([mesh.points for _, _, mesh in meshes])
    low, high = xyz.min(axis=0), xyz.max(axis=0)
    span = float(max(high - low))
    center = (low + high) / 2
    fig = plt.figure(figsize=(16, 10), facecolor='#111c26')
    view_hashes = {}
    for panel in range(2):
        plot = pv.Plotter(off_screen=True, window_size=(1500, 1300))
        plot.background_color = '#111c26'
        for name, role, mesh in meshes:
            shown = mesh if panel == 0 else mesh.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=False)
            if shown.n_cells:
                plot.add_mesh(shown, color=palette[role], smooth_shading=False, show_edges=False, ambient=.35, diffuse=.65, specular=.15)
        if panel:
            section = body_mesh.slice(normal=(1, 0, 0), origin=(0, 0, 0))
            if section.n_cells:
                plot.add_mesh(section, color='#e8eff4', line_width=1.2)
        direction = np.array([1.5, 1.8, 1.1]) if panel == 0 else np.array([-2.3, 1.0, .55])
        focus = center if panel == 0 else center + np.array([span * .07, 0, 0])
        plot.camera_position = [tuple(focus + span * direction), tuple(focus), (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = span * .58
        plot.enable_anti_aliasing('ssaa')
        path = out / ('full.png' if panel == 0 else 'display-half-cut.png')
        pixels = plot.screenshot(str(path), return_img=True)
        plot.close()
        view_hashes[path.name] = sha(path)
        ax = fig.add_axes([.005 + panel * .5, .21, .49, .64])
        ax.imshow(pixels)
        ax.axis('off')
    fg, muted = '#eef3f6', '#b6c5d2'
    fig.text(.035, .945, 'V5 body + four-valve V2 module | integration checkpoint', fontsize=21, color=fg, weight='bold')
    fig.text(.035, .893, '01 | Whole native body + exact 12 components', fontsize=13, color=muted)
    fig.text(.535, .893, '02 | Display half-cut X = 0; retained X >= 0', fontsize=13, color=muted)
    legend = fig.legend(handles=[Patch(color=palette[r], label=l) for r, l in [('body','V5 diagnostic body'),('valve','4 valves'),('seat','4 seats'),('guide','4 guides')]],
                        loc='lower center', bbox_to_anchor=(.5,.155), ncol=4, frameon=False, fontsize=12)
    for text in legend.get_texts():
        text.set_color(fg)
    fig.text(.035,.115,'NOT A COMPLETE HEAD: springs, camshafts/actuation and oil circuits are not integrated.',fontsize=12,color='#ffb2a4')
    fig.text(.035,.08,'Closed valves | display clipping only, uncapped | unchanged V5 body | no smoothing or decimation',fontsize=11,color=muted)
    fig.text(.035,.046,'Uncalibrated 935 scan units; 1 unit/mm is an unverified hypothesis. M64 interfaces and hot retention unqualified.',fontsize=10,color=muted)
    fig.text(.035,.019,'Private geometric derivative | colours are categorical, not materials or simulation fields | no manufacturing authorization',fontsize=10,color=muted)
    image_path = out / 'v5-v2-integration-checkpoint.png'
    fig.savefig(image_path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    if any(sha(root / name) != expected for name, expected in PINS.items()) or sha(__file__) != source_sha:
        raise ValueError('input_or_source_changed')
    save(out / 'render-receipt.json', {'schema':'private-V5-V2-render/v1','source_sha256':source_sha,
         'assembly_tessellation_receipt_sha256':sha(out/'assembly-and-tessellation.json'),'inputs_sha256':PINS,
         'image_sha256':sha(image_path),'individual_views_sha256':view_hashes,'renderer':'PyVista_VTK_z_buffer',
         'PyVista_version':pv.__version__,'VTK_version':vtk.vtkVersion.GetVTKVersion(),'matplotlib_version':matplotlib.__version__,
         'geometry_modified_by_render':False,'display_cut_capped':False,'categorical_colours_only':True,
         'generative_image':False,'master_inputs_unchanged':True,'source_unchanged':True,'wall_seconds':time.monotonic()-start,
         'max_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'manufacturing_authorized':False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    if sha(__file__) != args.source_sha256:
        raise ValueError('exact_source_hash_required')
    preflight(args.root)
    os.umask(0o077)
    args.output.mkdir(mode=0o700, exist_ok=False)
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (560,570))
    signal.alarm(600)
    run(args.root,args.output,args.source_sha256)
