#!/usr/bin/env python3
"""Local mesh-size experiments on the unchanged, hash-bound native head."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_parallel_cad_trials as batch

native = batch.native
DIAGNOSTIC_SHA = 'c6d6a2a1e242739a4c007529dcc490b9f11517fd6e7635519c79f25a5f16edfe'
HELPER_SHA = '7171d7b1da250d63086b7fac1e5e1617190ec26f45f2928e729d60582a1d1c04'
RECIPES = ('low-minimum', 'short-edges', 'short-edges-smooth')


def point_size(length):
    if not math.isfinite(length) or length <= 0:
        raise ValueError('positive_finite_curve_length_required')
    return max(.005, min(.05, .75*length))


def selected_faces(diagnostic, binding):
    if binding.get('descriptor_bijection_verified') is not True:
        raise ValueError('native_face_bijection_required')
    indices = {row['source_face_index'] for row in diagnostic['surface_quality_by_source_face_private']
               if row['minSICN_below_0p1'] > 0}
    matches = [row for row in binding['matches_private'] if row['source_face_index'] in indices]
    if (not indices or len(matches) != len(indices)
            or {row['source_face_index'] for row in matches} != indices
            or len({row['gmsh_face_tag'] for row in matches}) != len(indices)):
        raise ValueError('diagnosed_faces_must_match_once')
    return sorted(row['gmsh_face_tag'] for row in matches)


def run(args):
    import gmsh
    import OCP
    if gmsh.__version__ != '4.15.2' or OCP.__version__ != '7.9.3.1':
        raise ValueError('qualified_native_versions_required')
    paths = [args.body, args.baseline, args.diagnostic, Path(native.__file__), Path(batch.__file__), Path(__file__)]
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('regular_inputs_required')
    hashes = [native.sha256(p) for p in paths]
    if hashes[0] != batch.BODY_SHA or hashes[2] != DIAGNOSTIC_SHA or hashes[3] != HELPER_SHA:
        raise ValueError('input_binding_failed')
    if json.loads(args.baseline.read_text()).get('native_BRep_sha256') != hashes[0]:
        raise ValueError('baseline_binding_failed')
    args.output.mkdir(mode=0o700)
    mesh_dir = args.output/'mesh'
    mesh_dir.mkdir(mode=0o700)
    receipt = dict(schema='m64-native-adaptive-trial/v1', recipe=args.recipe,
        source_sha256=hashes[-1], helper_sha256=hashes[3], batch_helper_sha256=hashes[4], input_sha256=hashes[0],
        diagnostic_sha256=hashes[2], baseline_sha256=hashes[1], calls=[],
        status='incomplete', CAD_modified=False, manufacturing_authorized=False)
    report_path = args.output/'recipe.json'
    def save(): native.save(report_path, receipt)
    save()
    generate = gmsh.model.mesh.generate
    def adaptive_generate(dimension=3):
        receipt['calls'].append(dimension)
        if dimension == 1:
            gmsh.option.setNumber('Mesh.Algorithm', 1)
            if args.recipe != 'low-minimum':
                binding = json.loads((mesh_dir/'mesh-report.json').read_text())['import']['face_correspondence']
                tags = selected_faces(json.loads(args.diagnostic.read_text()), binding)
                curves = sorted({tag for dim,tag in gmsh.model.getBoundary([(2,t) for t in tags], combined=False, oriented=False) if dim == 1})
                sizes = {}; short = []
                for curve in curves:
                    length = gmsh.model.occ.getMass(1, curve)
                    if 0 < length < .25:
                        size = point_size(length)
                        short.append(dict(curve_tag=curve, length=length, target_size=size))
                        for dim,vertex in gmsh.model.getBoundary([(1,curve)], combined=False, oriented=False):
                            if dim == 0: sizes[vertex] = min(sizes.get(vertex, math.inf), size)
                if not sizes or len(sizes) > 1000: raise ValueError('bounded_short_edge_points_required')
                gmsh.option.setNumber('Mesh.MeshSizeFromPoints', 1)
                for vertex,size in sorted(sizes.items()): gmsh.model.mesh.setSize([(0,vertex)], size)
                receipt.update(target_surface_tags=tags, short_curves=short, point_sizes={str(k):v for k,v in sorted(sizes.items())})
            receipt['effective_overrides'] = {key:gmsh.option.getNumber(key) for key in (
                'Mesh.Algorithm', 'Mesh.MeshSizeMin', 'Mesh.MeshSizeMax', 'Mesh.MeshSizeFromPoints',
                'Mesh.MeshSizeFromCurvature', 'Mesh.MeshSizeExtendFromBoundary')}
        save()
        result = generate(dimension)
        if dimension == 2:
            if args.recipe == 'short-edges-smooth':
                gmsh.model.mesh.optimize('Relocate2D', niter=5)
                receipt['surface_optimizer'] = dict(method='Relocate2D', niter=5)
            _,tags,_ = gmsh.model.mesh.getElements(2)
            values = gmsh.model.mesh.getElementQualities(tags[0], 'minSICN')
            if not len(values) or not all(math.isfinite(v) for v in values):
                raise ValueError('finite_surface_qualities_required')
            receipt['surface_before_volume'] = dict(triangles=len(values), minimum=float(min(values)),
                below_0p1=int(sum(values < .1)))
            save()
        return result
    gmsh.model.mesh.generate = adaptive_generate
    signal.alarm(600)
    ns = argparse.Namespace(input=args.body, sha256=hashes[0], baseline=args.baseline,
        output=mesh_dir, minimum=.005, maximum=3., volume_algorithm=1,
        optimizer='netgen', maximum_tetrahedra=1500000, preserved_skin_meshadapt_evidence=None)
    try:
        code = native.mesh(ns)
        mesh_report = json.loads((mesh_dir/'mesh-report.json').read_text())
        receipt.update(status='completed', coarse_mesh_passed=batch.mesh_accepted(mesh_report),
                       mesh_report_sha256=native.sha256(mesh_dir/'mesh-report.json'))
        return code
    finally:
        signal.alarm(0)
        gmsh.model.mesh.generate = generate
        receipt.update(inputs_and_sources_unchanged=hashes==[native.sha256(p) for p in paths],
                       hooks_complete=receipt['calls']==[1,2,3])
        save()
        if not receipt['inputs_and_sources_unchanged'] or not receipt['hooks_complete']:
            raise ValueError('changed_source_or_incomplete_hook')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body','baseline','diagnostic','output'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--recipe', choices=RECIPES, required=True)
    os.umask(0o077)
    raise SystemExit(run(parser.parse_args()))
