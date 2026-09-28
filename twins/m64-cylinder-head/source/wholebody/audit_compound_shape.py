#!/usr/bin/env python3
"""Bidirectional sampled shape check of reclassified cross-patch triangles.

Not a Hausdorff bound: native and mesh interiors are sampled, not enclosed.
"""
import argparse
import json
from pathlib import Path
import signal

import numpy as np
from run_parallel_cad_trials import BODY_SHA, native
from trial_constrained_patch import PATCHES, read_native, indexed, compound, interior_points, sampled_distance


def points_to_triangles(points, vertices, triangles):
    import vtk
    from run_bounded_chamfer import surface_arrays
    vertices, triangles = surface_arrays(vertices, triangles)
    cloud = vtk.vtkPoints(); cloud.SetDataTypeToDouble()
    for p in vertices: cloud.InsertNextPoint(*map(float, p))
    cells = vtk.vtkCellArray()
    for row in triangles:
        cells.InsertNextCell(3)
        for i in row: cells.InsertCellPoint(int(i))
    mesh = vtk.vtkPolyData(); mesh.SetPoints(cloud); mesh.SetPolys(cells)
    locator = vtk.vtkStaticCellLocator(); locator.SetDataSet(mesh); locator.BuildLocator()
    distances = []
    for point in points:
        closest = [0., 0., 0.]; cell = vtk.reference(0); sub = vtk.reference(0); d2 = vtk.reference(0.)
        locator.FindClosestPoint(point.Coord(), closest, cell, sub, d2)
        if float(d2) < 0 or not np.isfinite(float(d2)): raise ValueError('finite_native_sample_distance_required')
        distances.append(float(d2)**.5)
    if not distances: raise ValueError('nonempty_native_samples_required')
    return dict(samples=len(distances), maximum=max(distances))


def run(args):
    import gmsh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.gp import gp_Pnt
    record = json.loads(args.receipt.read_text())
    pins = {p: native.sha256(p) for p in (args.body, args.mesh, args.receipt, Path(__file__))}
    if (args.output.exists() or any(p.is_symlink() for p in pins) or pins[args.body] != BODY_SHA
            or record.get('input_sha256') != BODY_SHA or record.get('surface_sha256') != pins[args.mesh]
            or record.get('schema') != 'm64-compound-junction-screen/v1'
            or record.get('compound_classify') != 1 or record.get('inputs_unchanged') is not True
            or record.get('status') != 'completed_diagnostic_only'):
        raise ValueError('bound_reclassified_surface_and_fresh_report_required')
    binding = record['native_face_binding_private']
    if binding.get('descriptor_bijection_verified') is not True: raise ValueError('native_face_binding_required')
    tags = {r['source_face_index']: r['gmsh_face_tag'] for r in binding['matches_private']}
    faces = indexed(read_native(args.body), TopAbs_FACE); result = {}
    gmsh.initialize(['compound-shape', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        gmsh.open(str(args.mesh)); node_tags, xyz, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(node_tags); node_tags = node_tags[order]; xyz = np.array(xyz).reshape(-1, 3)[order]
        for name, group in PATCHES.items():
            arrays, empty = [], []
            for i in group:
                types, _, nodes = gmsh.model.mesh.getElements(2, tags[i])
                if not len(types):
                    empty.append(i); continue
                if list(types) != [2]: raise ValueError('linear_patch_triangles_required')
                flat = np.asarray(nodes[0]); indices = np.searchsorted(node_tags, flat)
                if indices.max() >= len(node_tags) or not np.array_equal(node_tags[indices], flat):
                    raise ValueError('known_mesh_nodes_required')
                arrays.append(indices.reshape(-1, 3))
            if not arrays: raise ValueError('nonempty_compound_patch_required')
            triangles = np.vstack(arrays); positions = xyz[triangles]
            mesh_samples = np.unique(np.vstack([xyz[np.unique(triangles)], positions.mean(axis=1),
                (positions[:, 0]+positions[:, 1])/2, (positions[:, 1]+positions[:, 2])/2,
                (positions[:, 2]+positions[:, 0])/2]), axis=0)
            patch = [faces[i-1] for i in group]
            native_samples = [p for f in patch for p in interior_points(f, 17)]
            for face in patch:
                for edge in indexed(face, TopAbs_EDGE):
                    curve = BRepAdaptor_Curve(TopoDS.Edge_s(edge))
                    native_samples.extend(curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(), curve.LastParameter(), 65))
            result[name] = dict(triangles=len(triangles), empty_reclassified_source_faces=empty,
                facewise_boundary_conditions_preserved=False,
                mesh_to_native=sampled_distance([gp_Pnt(*map(float, p)) for p in mesh_samples], compound(patch)),
                native_to_mesh=points_to_triangles(native_samples, xyz, triangles))
    finally: gmsh.finalize()
    report = dict(schema='m64-compound-native-shape-samples/v1',
        source_hashes={p.name: h for p, h in pins.items()}, groups=result,
        native_Hausdorff_certified=False, unsampled_extrema_bounded=False,
        physical_scale_certified=False, manufacturing_authorized=False,
        inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items()))
    native.save(args.output, report); print(json.dumps(report))
    return 0 if report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'mesh', 'receipt', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
