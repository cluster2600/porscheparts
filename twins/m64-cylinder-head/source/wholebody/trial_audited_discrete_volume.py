#!/usr/bin/env python3
"""Bounded faceted-volume diagnostic; native sharp edges remain unqualified.

No CAD import, boundary movement, 1D feature recovery or physics release.
"""
import argparse
import json
from pathlib import Path
import resource
import signal
import sys
import time

import numpy as np
from run_bounded_chamfer import surface_arrays
from trial_meshers_2026 import native, read_gmsh, audit_output

ARRAY_SHA = 'a599cb6c317f2559a458331444b211267d12eb77b899bbbb9b02d9d5566c3c8d'
TOPOLOGY_SHA = '89dc417de042d0bca0ab0588b0e42d563b79284a6c6cc03b4d55322b9eb69a7b'
CGAL_SHA = 'c4fd77b8e758adaa7dd7e4a5d619d477e52148fb242a2afab6087bdf272434ed'
RAW_SHA = '742d8a3610b2abe766e9c4b476b1110ad69cdb72ecdee718ab1d2d18be55aeb5'
OPTIMIZERS = {'default':'', 'netgen':'Netgen'}


def optimize_volume(gmsh, method):
    gmsh.model.mesh.optimize(OPTIMIZERS[method],force=True)
    # Gmsh 4.15.2 can leave old lookup entries after replacing tetrahedra.
    gmsh.model.mesh.rebuildElementCache(False)


def check_boundary(gmsh, points, faces):
    """Exact coordinates and oriented triangles; permit element-order changes."""
    tags, xyz, _ = gmsh.model.mesh.getNodes(); order = np.argsort(tags)
    tags = np.asarray(tags)[order]; xyz = np.asarray(xyz).reshape(-1,3)[order]
    selected = np.searchsorted(tags, np.arange(1,len(points)+1))
    types, _, nodes = gmsh.model.mesh.getElements(2)
    if (selected.max() >= len(tags) or not np.array_equal(tags[selected],np.arange(1,len(points)+1))
            or not np.array_equal(xyz[selected],points) or list(types) != [2]):
        raise ValueError('exact_boundary_nodes_and_linear_triangles_required')
    actual = np.asarray(nodes[0]).reshape(-1,3)-1
    def canonical(triangles):
        rotated = np.take_along_axis(triangles,(triangles.argmin(axis=1)[:,None]+np.arange(3))%3,axis=1)
        return rotated[np.lexsort(rotated.T[::-1])]
    if actual.shape != faces.shape or not np.array_equal(canonical(actual),canonical(faces)):
        raise ValueError('exact_oriented_boundary_triangles_required')
    return True


def generate(gmsh, points, faces, extend_size=True):
    gmsh.model.add('faceted_diagnostic_not_native_CAD')
    gmsh.model.addDiscreteEntity(2,1)
    gmsh.model.mesh.addNodes(2,1,np.arange(1,len(points)+1),points.ravel())
    gmsh.model.mesh.addElementsByType(1,2,[],(faces+1).ravel())
    gmsh.model.geo.addSurfaceLoop([1],1); gmsh.model.geo.addVolume([1],1)
    gmsh.model.geo.synchronize()
    for key, value in {'Mesh.Algorithm3D':1, 'General.NumThreads':2,
            'Mesh.MaxNumThreads3D':2, 'Mesh.MeshOnlyEmpty':1, 'Mesh.Renumber':0,
            'Mesh.Optimize':0, 'Mesh.OptimizeNetgen':0, 'Mesh.ElementOrder':1,
            'Mesh.MeshSizeMin':.00002, 'Mesh.MeshSizeMax':3., 'Mesh.RandomSeed':1,
            'Mesh.MeshSizeExtendFromBoundary':int(extend_size)}.items():
        gmsh.option.setNumber(key,value)
    gmsh.model.mesh.generate(3)
    check_boundary(gmsh,points,faces)


def run(args):
    import gmsh
    from audit_envelope_regions import audit
    pins = {args.arrays:ARRAY_SHA, args.topology:TOPOLOGY_SHA, args.intersections:CGAL_SHA}
    if args.raw_checkpoint: pins[args.raw_checkpoint] = RAW_SHA
    for module in (__name__, surface_arrays.__module__, read_gmsh.__module__, audit.__module__, native.__name__):
        path = Path(sys.modules[module].__file__); pins[path] = native.sha256(path)
    if (args.output.exists() or args.output.is_symlink() or gmsh.__version__ != '4.15.2'
            or any(p.is_symlink() or native.sha256(p) != h for p,h in pins.items())):
        raise ValueError('fresh_output_exact_audited_surface_and_runtime_required')
    args.output.mkdir(mode=0o700); start = time.monotonic()
    report = dict(schema='m64-audited-discrete-volume/v1', status='incomplete',
        source_hashes={str(p):h for p,h in pins.items()}, gmsh_version=gmsh.__version__,
        extend_boundary_size=not args.no_extend_size, optimizer=args.optimizer,
        resumed_raw_checkpoint=bool(args.raw_checkpoint),
        native_sharp_edges_recovered=False, native_face_roles_preserved=False,
        native_CAD_conformance_certified=False, CAE_authorized=False, manufacturing_authorized=False)
    save = lambda: native.save(args.output/'report.json',report)
    save(); gmsh.initialize(['faceted-volume','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0); gmsh.logger.start()
    try:
        with np.load(args.arrays,allow_pickle=False) as data:
            points,faces = surface_arrays(data['points'],data['triangles'])
            report['unreferenced_stored_nodes_excluded'] = len(data['points'])-len(points)
        report.update(boundary_vertices=len(points), boundary_triangles=len(faces), stage='generating_volume'); save()
        if args.raw_checkpoint:
            read_gmsh(args.raw_checkpoint); check_boundary(gmsh,points,faces)
            gmsh.option.setNumber('General.NumThreads',2)
        else:
            generate(gmsh,points,faces,extend_size=not args.no_extend_size)
        def quality():
            types, elements, _ = gmsh.model.mesh.getElements(3)
            report['last_volume_element_counts'] = {int(t):len(e) for t,e in zip(types,elements)}; save()
            if list(types) != [4] or not len(elements[0]): raise ValueError('nonempty_linear_volume_required')
            if len(elements[0]) > 3_000_000: raise ValueError('three_million_tetra_audit_cap')
            q = gmsh.model.mesh.getElementQualities(elements[0],'minSICN')
            det = gmsh.model.mesh.getElementQualities(elements[0],'minDetJac')
            return native.reread_quality_gate(list(map(float,q)),list(map(float,det)),len(elements[0]))
        report.update(raw_quality=quality(),exact_boundary_after_generation=True,stage='saving_raw_checkpoint'); save()
        gmsh.option.setNumber('Mesh.Binary',1); gmsh.option.setNumber('Mesh.SaveAll',1)
        raw = args.output/'raw-private.msh'; gmsh.write(str(raw)); raw.chmod(0o600)
        report.update(raw_mesh_sha256=native.sha256(raw),stage='optimizing_volume'); save()
        optimize_volume(gmsh,args.optimizer)
        report.update(stage='reading_optimized_quality'); save()
        report.update(optimized_quality=quality(), exact_boundary_after_optimization=check_boundary(gmsh,points,faces),
                      stage='exporting'); save()
        output = args.output/'generated-private.msh'
        gmsh.write(str(output)); output.chmod(0o600)
        p,c,f,_ = read_gmsh(output)
        report.update(generated_sha256=native.sha256(output), exact_boundary_readback=check_boundary(gmsh,points,faces),
                      stage='auditing'); save()
        report['volume_audit'] = audit_output(p,c,f,args.output/'audited-private.msh'); save()
        report['region_audit'], _ = audit(p,c); save()
        report.update(status='completed_faceted_diagnostic_only',stage='finished')
    except Exception as error:
        report.update(status='failed',error=type(error).__name__+': '+str(error))
    finally:
        report['mesher_warnings_errors'] = [s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))]
        gmsh.logger.stop(); gmsh.finalize()
        report.update(seconds=time.monotonic()-start,inputs_unchanged=all(native.sha256(p)==h for p,h in pins.items())); save()
    print(json.dumps({k:report.get(k) for k in ('status','error','raw_quality','optimized_quality','seconds')}))
    return 0 if report['status']=='completed_faceted_diagnostic_only' and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('arrays','topology','intersections','output'): parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--no-extend-size',action='store_true',help='Do not propagate boundary size into the volume; keep all boundary triangles.')
    parser.add_argument('--optimizer',choices=OPTIMIZERS,default='default')
    parser.add_argument('--raw-checkpoint',type=Path,help='Reuse only the pinned Linux raw volume; never regenerate the surface.')
    if sys.platform == 'linux': resource.setrlimit(resource.RLIMIT_AS,(10*1024**3,10*1024**3))
    signal.alarm(600)
    args=parser.parse_args()
    if args.raw_checkpoint and not args.no_extend_size: parser.error('checkpoint_requires_original_no_extend_recipe')
    raise SystemExit(run(args))
