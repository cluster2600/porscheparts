#!/usr/bin/env python3
"""Cross-patch mesh experiment on unchanged native CAD; not CAD reconstruction.

Compounds use a discrete approximation. Quality alone cannot certify shape,
boundary conditions, functional interfaces or manufacturing readiness.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import signal
import time

import numpy as np
from run_parallel_cad_trials import BODY_SHA, native
from trial_constrained_patch import PATCHES


def surface_edges(triangles):
    if (triangles.ndim != 2 or triangles.shape[1] != 3 or not len(triangles)
            or not np.issubdtype(triangles.dtype, np.integer)
            or (np.diff(np.sort(triangles, axis=1), axis=1) == 0).any()):
        raise ValueError('nondegenerate_indexed_triangles_required')
    edges = np.concatenate([triangles[:, p] for p in ((0, 1), (1, 2), (2, 0))])
    _, counts = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    return dict(edges=len(counts), not_incident_twice=int((counts != 2).sum()),
                duplicate_triangles=len(triangles)-len(np.unique(np.sort(triangles, axis=1), axis=0)),
                vertex_links_checked=False, geometric_intersections_checked=False)


def restrict_patch_size(gmsh, surfaces, size):
    if not surfaces or not math.isfinite(size) or not 0 < size <= .2:
        raise ValueError('bounded_patch_sizing_required')
    constant = gmsh.model.mesh.field.add('MathEval')
    gmsh.model.mesh.field.setString(constant, 'F', str(size))
    restricted = gmsh.model.mesh.field.add('Restrict')
    gmsh.model.mesh.field.setNumber(restricted, 'InField', constant)
    gmsh.model.mesh.field.setNumbers(restricted, 'SurfacesList', surfaces)
    gmsh.model.mesh.field.setNumber(restricted, 'IncludeBoundary', 1)
    return restricted


def run(args):
    import gmsh
    if (args.output.exists() or args.output.is_symlink() or args.body.is_symlink()
            or native.sha256(args.body) != BODY_SHA or gmsh.__version__ != '4.15.2'):
        raise ValueError('pinned_body_runtime_and_fresh_output_required')
    pins = {args.body: BODY_SHA, Path(__file__): native.sha256(__file__)}
    helper = Path(__file__).with_name('trial_constrained_patch.py'); pins[helper] = native.sha256(helper)
    args.output.mkdir(mode=0o700); start = time.monotonic()
    report = dict(schema='m64-compound-junction-screen/v1', status='incomplete', input_sha256=BODY_SHA,
        source_sha256=pins[Path(__file__)], helper_sha256=pins[helper], groups=PATCHES,
        compound_size_factor=args.factor, compound_classify=args.classify, volume_requested=args.volume,
        junction_size=args.junction_size, curvature_points=args.curvature,
        wall_seconds=args.wall_seconds, patch_size=args.patch_size,
        geometry_modified=False, master_replaced=False, native_shape_conformance_certified=False,
        CAE_authorized=False, manufacturing_authorized=False)
    def save(): native.save(args.output/'report.json', report)
    save()
    native.baseline(argparse.Namespace(input=args.body, sha256=BODY_SHA, output=args.output))
    baseline = json.loads((args.output/'native-baseline.json').read_text())
    gmsh.initialize(['compound-screen', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.logger.start()
    try:
        for key in ('OCCFixDegenerated', 'OCCFixSmallEdges', 'OCCFixSmallFaces', 'OCCSewFaces', 'OCCMakeSolids', 'OCCAutoFix'):
            gmsh.option.setNumber('Geometry.'+key, 0)
        gmsh.option.setNumber('Geometry.OCCScaling', 1)
        gmsh.model.occ.importShapes(str(args.body), highestDimOnly=False); gmsh.model.occ.synchronize()
        rows = [dict(tag=t, area=gmsh.model.occ.getMass(2, t), centre=list(gmsh.model.occ.getCenterOfMass(2, t)))
                for _, t in gmsh.model.getEntities(2)]
        binding = native.match_faces(baseline['face_descriptors_private'], rows)
        if not binding['descriptor_bijection_verified'] or len(gmsh.model.getEntities(3)) != 1:
            raise ValueError('one_solid_and_native_face_bijection_required')
        tags = {r['source_face_index']: r['gmsh_face_tag'] for r in binding['matches_private']}
        report['native_face_binding_private'] = binding
        for name, group in PATCHES.items(): gmsh.model.mesh.setCompound(2, [tags[i] for i in group])
        for key, value in {'Mesh.Algorithm': 1, 'Mesh.MeshSizeMin': .00002, 'Mesh.MeshSizeMax': 3.,
                          'Mesh.MeshSizeFromPoints': 1, 'Mesh.MeshSizeFromCurvature': args.curvature,
                          'Mesh.MeshSizeExtendFromBoundary': 1, 'General.NumThreads': 2,
                          'Mesh.MaxNumThreads1D': 2, 'Mesh.MaxNumThreads2D': 2, 'Mesh.RandomSeed': 1,
                          'Mesh.ElementOrder': 1, 'Mesh.CompoundClassify': args.classify,
                          'Mesh.CompoundMeshSizeFactor': args.factor}.items():
            gmsh.option.setNumber(key, value)
        sizes = {}
        for _, curve in gmsh.model.getEntities(1):
            length = gmsh.model.occ.getMass(1, curve)
            if 0 < length < .25:
                size = max(.00002, min(.05, .75*length))
                for d, v in gmsh.model.getBoundary([(1, curve)], oriented=False):
                    if d == 0: sizes[v] = min(sizes.get(v, math.inf), size)
        for tag, size in sizes.items(): gmsh.model.mesh.setSize([(0, tag)], size)
        fields = []
        if args.junction_size:
            curves = []
            for group in PATCHES.values():
                uses = Counter(abs(t) for i in group for d, t in gmsh.model.getBoundary([(2, tags[i])], oriented=False) if d == 1)
                curves.extend(t for t, count in uses.items() if count == 2)
            if not curves: raise ValueError('measured_internal_junction_curves_required')
            distance = gmsh.model.mesh.field.add('Distance')
            gmsh.model.mesh.field.setNumbers(distance, 'CurvesList', sorted(set(curves)))
            gmsh.model.mesh.field.setNumber(distance, 'Sampling', 1000)
            threshold = gmsh.model.mesh.field.add('Threshold')
            for key, value in dict(InField=distance, SizeMin=args.junction_size, SizeMax=3., DistMin=.2, DistMax=.8).items():
                gmsh.model.mesh.field.setNumber(threshold, key, value)
            fields.append(threshold)
            report['junction_field'] = dict(curves_private=sorted(set(curves)), sampling=1000, min_distance=.2, max_distance=.8)
        if args.patch_size:
            fields.append(restrict_patch_size(gmsh, [tags[i] for group in PATCHES.values() for i in group], args.patch_size))
        if fields:
            combined = gmsh.model.mesh.field.add('Min')
            gmsh.model.mesh.field.setNumbers(combined, 'FieldsList', fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(combined)
        report.update(sized_points=len(sizes), stage='meshing_compounds'); save()
        gmsh.model.mesh.generate(2)
        types, elements, nodes = gmsh.model.mesh.getElements(2)
        if list(types) != [2]: raise ValueError('linear_surface_required')
        q = np.asarray(gmsh.model.mesh.getElementQualities(elements[0], 'minSICN'))
        if not len(q) or not np.isfinite(q).all() or len(q) > 2000000:
            raise ValueError('bounded_finite_surface_required')
        report.update(triangles=len(q), minimum=float(q.min()),
            incompatible_triangles=int((q < 2*.1/(3-.1)).sum()),
            edge_audit=surface_edges(np.asarray(nodes[0]).reshape(-1, 3)))
        report['affected_faces'] = []
        for _, tag in gmsh.model.getEntities(2):
            t, e, _ = gmsh.model.mesh.getElements(2, tag)
            if not len(t): continue
            qualities = np.asarray(gmsh.model.mesh.getElementQualities(e[0], 'minSICN'))
            if (qualities < 2*.1/(3-.1)).any():
                report['affected_faces'].append(dict(tag=tag, minimum=float(qualities.min()),
                    count=int((qualities < 2*.1/(3-.1)).sum())))
        gmsh.option.setNumber('Mesh.Binary', 1); gmsh.option.setNumber('Mesh.SaveAll', 1)
        path = args.output/'surface-private.msh'; gmsh.write(str(path)); path.chmod(0o600)
        report.update(status='completed_diagnostic_only', surface_sha256=native.sha256(path))
        save()
        if args.volume:
            if (report['incompatible_triangles'] or report['edge_audit']['not_incident_twice']
                    or report['edge_audit']['duplicate_triangles'] or args.classify != 1):
                raise ValueError('closed_quality_screen_and_classified_surface_required_before_volume')
            report.update(status='incomplete', stage='meshing_volume'); save()
            gmsh.option.setNumber('Mesh.Algorithm3D', 1)
            gmsh.option.setNumber('Mesh.MaxNumThreads3D', 2)
            gmsh.model.mesh.generate(3); gmsh.model.mesh.optimize('Netgen')
            types, elements, _ = gmsh.model.mesh.getElements(3)
            if list(types) != [4] or not 0 < len(elements[0]) <= 2000000:
                raise ValueError('bounded_linear_volume_required')
            q3 = np.asarray(gmsh.model.mesh.getElementQualities(elements[0], 'minSICN'))
            report.update(tetrahedra=len(q3), rejected_tetrahedra=int((q3 < .1).sum()),
                          tetra_minimum=float(q3.min()), stage='auditing_volume'); save()
            volume_path = args.output/'classified-volume-private.msh'
            gmsh.write(str(volume_path)); volume_path.chmod(0o600)
            from trial_meshers_2026 import read_gmsh, audit_output
            from audit_envelope_regions import audit
            points, cells, faces, _ = read_gmsh(volume_path)
            report['classified_volume_sha256'] = native.sha256(volume_path)
            report['volume_audit'] = audit_output(points, cells, faces, args.output/'audited-volume-private.msh')
            regions, _ = audit(points, cells); report['region_audit'] = regions
            report['native_relative_volume_error'] = abs(report['volume_audit']['tetra_volume']/baseline['volume']-1)
            report.update(status='completed_volume_diagnostic_only', stage='finished')
    except Exception as error:
        report.update(status='failed', error=type(error).__name__+': '+str(error))
    finally:
        report['mesher_warnings_errors'] = [s for s in gmsh.logger.get() if s.startswith(('Warning', 'Error'))]
        gmsh.logger.stop(); gmsh.finalize()
        report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items())); save()
    print(json.dumps({k: report.get(k) for k in ('status', 'error', 'triangles', 'incompatible_triangles', 'minimum', 'edge_audit', 'tetrahedra', 'rejected_tetrahedra', 'tetra_minimum', 'seconds')}))
    return 0 if report['status'] in ('completed_diagnostic_only', 'completed_volume_diagnostic_only') and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--factor', type=float, choices=(.5, 1.), default=1.)
    parser.add_argument('--classify', type=int, choices=(0, 1), default=0)
    parser.add_argument('--volume', action='store_true', help='Run a diagnostic volume only after the surface screen passes.')
    parser.add_argument('--junction-size', type=float, choices=(.02, .05), help='Refine near native internal junction curves.')
    parser.add_argument('--patch-size', type=float, choices=(.1, .2), help='Limit size across both original compound patches and their boundaries.')
    parser.add_argument('--curvature', type=int, choices=(12, 64), default=12)
    parser.add_argument('--wall-seconds', type=int, choices=(540, 1800), default=540)
    args = parser.parse_args()
    signal.alarm(args.wall_seconds)
    raise SystemExit(run(args))
