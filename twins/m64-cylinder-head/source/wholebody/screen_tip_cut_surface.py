#!/usr/bin/env python3
"""Cheap native-boundary feasibility screen before any volume meshing."""
import argparse
import json
import math
from pathlib import Path
import resource
import signal
import time

import numpy as np
from run_parallel_cad_trials import native, BODY_SHA
from audit_fixed_face_quality import tetra_ceiling


def run(args):
    import gmsh
    pins = {Path(__file__): native.sha256(__file__)}
    if args.reference_body:
        body = args.reference_body; sha = native.sha256(body)
        if sha != BODY_SHA: raise ValueError('original_control_required')
    else:
        report_path = args.candidate/'report.json'; body = args.candidate/'candidate-private.brep'
        producer = json.loads(report_path.read_text()); sha = native.sha256(body)
        if (producer.get('candidate_sha256') != sha or producer.get('inputs_unchanged') is not True
                or producer.get('status') != 'candidate_pending_BOP_distance_and_mesh'):
            raise ValueError('bound_candidate_required')
        pins[report_path] = native.sha256(report_path)
    if (args.output.exists() or args.output.is_symlink() or body.is_symlink() or gmsh.__version__ != '4.15.2'):
        raise ValueError('fresh_output_and_native_candidate_required')
    pins[body] = sha
    args.output.mkdir(mode=0o700); start = time.monotonic()
    report = dict(schema='m64-tip-cut-surface-screen/v1', status='incomplete', input_sha256=sha,
        producer_sha256=None if args.reference_body else pins[report_path], source_sha256=pins[Path(__file__)],
        unchanged_reference_control=bool(args.reference_body),
        minimum_size=args.minimum, cpu_seconds=args.cpu_seconds,
        surface_algorithm=args.surface_algorithm,
        mesh_gate_closed=False, manufacturing_authorized=False)
    def save(): native.save(args.output/'report.json', report)
    ns = argparse.Namespace(input=body, sha256=sha, output=args.output)
    native.baseline(ns)
    baseline = json.loads((args.output/'native-baseline.json').read_text())
    gmsh.initialize(['tip-cut-screen', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        for key in ('OCCFixDegenerated', 'OCCFixSmallEdges', 'OCCFixSmallFaces', 'OCCSewFaces', 'OCCMakeSolids', 'OCCAutoFix'):
            gmsh.option.setNumber('Geometry.'+key, 0)
        gmsh.option.setNumber('Geometry.OCCScaling', 1)
        gmsh.model.occ.importShapes(str(body), highestDimOnly=False); gmsh.model.occ.synchronize()
        rows = [dict(tag=t, area=gmsh.model.occ.getMass(2, t), centre=list(gmsh.model.occ.getCenterOfMass(2, t)))
                for _, t in gmsh.model.getEntities(2)]
        binding = native.match_faces(baseline['face_descriptors_private'], rows)
        if not binding['descriptor_bijection_verified']: raise ValueError('native_face_mapping_required')
        mass = sum(gmsh.model.occ.getMass(3, t) for _, t in gmsh.model.getEntities(3))
        if len(gmsh.model.getEntities(3)) != 1 or abs(mass/baseline['volume']-1) > 1e-6:
            raise ValueError('one_mass_consistent_import_required')
        report['native_face_binding_private'] = binding; save()
        for key, value in {'Mesh.Algorithm': args.surface_algorithm, 'Mesh.MeshSizeMin': args.minimum,
                          'Mesh.MeshSizeMax': 3., 'Mesh.MeshSizeFromPoints': 1,
                          'Mesh.MeshSizeFromCurvature': 12, 'Mesh.MeshSizeExtendFromBoundary': 1,
                          'General.NumThreads': 2, 'Mesh.MaxNumThreads1D': 2, 'Mesh.MaxNumThreads2D': 2,
                          'Mesh.RandomSeed': 1, 'Mesh.ElementOrder': 1}.items():
            gmsh.option.setNumber(key, value)
        sizes = {}
        for _, curve in gmsh.model.getEntities(1):
            length = gmsh.model.occ.getMass(1, curve)
            if 0 < length < .25:
                size = max(args.minimum, min(.05, .75*length))
                for d, v in gmsh.model.getBoundary([(1, curve)], oriented=False):
                    if d == 0: sizes[v] = min(sizes.get(v, math.inf), size)
        for tag, size in sizes.items(): gmsh.model.mesh.setSize([(0, tag)], size)
        report.update(sized_points=len(sizes), stage='meshing_surface'); save()
        gmsh.model.mesh.generate(2)
        types, elements, _ = gmsh.model.mesh.getElements(2)
        if list(types) != [2]: raise ValueError('linear_triangles_required')
        q = gmsh.model.mesh.getElementQualities(elements[0], 'minSICN')
        necessary = 2*.1/(3-.1); finite = np.isfinite(q)
        report.update(triangles=len(q), nonfinite_qualities=int((~finite).sum()),
            minimum=float(q[finite].min()) if finite.any() else None,
            incompatible_triangles=int((q[finite] < necessary).sum()),
            surface_triangle_resource_limit=2000000); save()
        if not len(q) or not finite.all(): raise ValueError('nonempty_finite_surface_required')
        if len(q) > 2000000: raise ValueError('surface_triangle_resource_limit_exceeded')
        bad = []
        for _, tag in gmsh.model.getEntities(2):
            _, e, _ = gmsh.model.mesh.getElements(2, tag)
            qualities = gmsh.model.mesh.getElementQualities(e[0], 'minSICN')
            if (qualities < necessary).any():
                bad.append(dict(gmsh_face_tag=tag, count=int((qualities < necessary).sum()),
                                minimum=float(qualities.min()), tetra_ceiling=tetra_ceiling(float(qualities.min()))))
        gmsh.option.setNumber('Mesh.Binary', 1); gmsh.option.setNumber('Mesh.SaveAll', 1)
        mesh = args.output/'surface-private.msh'; gmsh.write(str(mesh)); mesh.chmod(0o600)
        report.update(status='completed_screen_only', triangles=len(q), minimum=float(q.min()),
            incompatible_triangles=int((q < necessary).sum()), affected_faces_private=bad,
            surface_sha256=native.sha256(mesh), volume_mesh_run=False)
    except Exception as error:
        report.update(status='failed', error=type(error).__name__+': '+str(error))
    finally:
        gmsh.finalize()
        report.update(seconds=time.monotonic()-start, inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items())); save()
    print(json.dumps({k: report.get(k) for k in ('status', 'error', 'triangles', 'incompatible_triangles', 'minimum', 'seconds')}))
    return 0 if report['status'] == 'completed_screen_only' and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--candidate', type=Path)
    group.add_argument('--reference-body', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--minimum', type=float, choices=(.005, .00002), default=.00002)
    parser.add_argument('--cpu-seconds', type=int, choices=(270, 540), default=270)
    parser.add_argument('--surface-algorithm', type=int, choices=(1, 6), default=1)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (args.cpu_seconds, args.cpu_seconds+5))
    signal.alarm(args.cpu_seconds+60)
    raise SystemExit(run(args))
