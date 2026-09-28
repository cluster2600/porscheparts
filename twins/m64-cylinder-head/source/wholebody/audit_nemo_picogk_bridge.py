#!/usr/bin/env python3
"""Audit the retained tetra mesh in actual PhysicsNeMo; export its boundary.

The float32 STL is a PicoGK diagnostic input, not a replacement BRep. All
geometry remains private; CPU geometry checks do not authorise CAE or printing.
"""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import signal
import struct
import sys
import time

import numpy as np
from audit_surface_gpu import compare, sha

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'picogk'))
from export_master import load_binary_stl, mesh_summary

MESH_SHA = '965de13aefda6f5a314c9edee295578b4f638d58c173dfe2098d77ae21e4e7af'
REPORT_SHA = '512b3efe0fd29afd33f4becad54b63ebbc14df229ba63cbc4090c86177392018'
COMPANION_SHA = '9e35966baeefdba17671e4b2050db70da7611bad74c6453916bc538d6f9f3f48'


def tetra_reference(points, cells):
    if (points.dtype != np.float64 or points.ndim != 2 or points.shape[1] != 3
            or not len(points) or not np.isfinite(points).all() or cells.dtype != np.int64
            or cells.ndim != 2 or cells.shape[1] != 4 or not len(cells)
            or cells.min() < 0 or cells.max() >= len(points)):
        raise ValueError('finite_float64_points_and_indexed_int64_tetrahedra_required')
    xyz = points[cells]
    volumes = np.linalg.det(xyz[:,1:]-xyz[:,[0]])/6
    if not np.isfinite(volumes).all() or not (volumes > 0).all():
        raise ValueError('positive_oriented_tetrahedra_required')
    edges = np.stack([np.linalg.norm(xyz[:,i]-xyz[:,j],axis=1)
                      for i,j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))],axis=1)
    areas = np.stack([np.linalg.norm(np.cross(xyz[:,j]-xyz[:,i],xyz[:,k]-xyz[:,i]),axis=1)/2
                     for i,j,k in ((0,1,2),(0,1,3),(0,2,3),(1,2,3))],axis=1)
    return {'volumes':volumes, 'edge_length_ratio':edges.max(1)/edges.min(1),
            'aspect_ratio':np.maximum(1.,edges.max(1)*areas.max(1)/(3*volumes*np.sqrt(1.5)))}


def boundary_faces(cells):
    # Outward winding for a positively oriented tetrahedron; never a mesh repair.
    faces = np.concatenate([cells[:,ids] for ids in ((1,2,3),(0,3,2),(0,1,3),(0,2,1))])
    _, indices, counts = np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
    if (counts > 2).any():
        raise ValueError('nonmanifold_tetra_faces')
    return faces[indices[counts == 1]]


def summary(values):
    finite = np.isfinite(values)
    return {'count':len(values),'nonfinite':int((~finite).sum()),
            'minimum':float(values[finite].min()) if finite.any() else None,
            'maximum':float(values[finite].max()) if finite.any() else None}


def run(args):
    import gmsh
    import torch
    import physicsnemo
    from physicsnemo.mesh import Mesh
    pins = {args.mesh:MESH_SHA,args.report:REPORT_SHA,args.companion:COMPANION_SHA,
            Path(__file__):sha(__file__)}
    if args.output.exists() or any(p.is_symlink() or sha(p)!=s for p,s in pins.items()):
        raise ValueError('fresh_output_and_exact_private_inputs_required')
    versions = {n:metadata.version(n) for n in ('torch','numpy','nvidia-physicsnemo','gmsh')}
    if versions != {'torch':'2.10.0','numpy':'2.2.6','nvidia-physicsnemo':'2.2.0','gmsh':'4.15.2'}:
        raise ValueError('exact_runtime_required')
    prior = json.loads(args.report.read_text()); companion = json.loads(args.companion.read_text())
    if not (companion['helper_report_sha256']==REPORT_SHA and companion['hook_complete'] is True
            and companion['inputs_and_sources_unchanged'] is True and prior['native_input_unchanged'] is True):
        raise ValueError('prior_mesh_provenance_failed')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    started = time.monotonic(); torch.set_num_threads(4)
    library_root = Path(physicsnemo.__file__).parent
    libraries = {p:sha(library_root/p) for p in ('mesh/mesh.py','mesh/validation/quality.py','mesh/geometry/_cell_areas.py')}
    gmsh.initialize(['bridge','-nopopup'],readConfigFiles=False,run=False)
    try:
        gmsh.option.setNumber('General.Terminal',0); gmsh.open(str(args.mesh))
        tags, coordinates, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags); tags = tags[order]
        points = np.asarray(coordinates,dtype=np.float64).reshape(-1,3)[order]
        types, element_tags, node_tags = gmsh.model.mesh.getElements(3)
        stypes, _, snodes = gmsh.model.mesh.getElements(2)
        if list(types)!=[4] or list(stypes)!=[2] or len(element_tags[0])!=241299:
            raise ValueError('exact_linear_mesh_counts_required')
        cells = np.searchsorted(tags,node_tags[0]).reshape(-1,4).astype(np.int64)
        stored_faces = np.searchsorted(tags,snodes[0]).reshape(-1,3).astype(np.int64)
        if not (np.array_equal(tags[cells.ravel()],node_tags[0]) and np.array_equal(tags[stored_faces.ravel()],snodes[0])):
            raise ValueError('node_reference_not_bijective')
        sicn = np.asarray(gmsh.model.mesh.getElementQualities(element_tags[0],'minSICN'))
    finally:
        gmsh.finalize()
    ref = tetra_reference(points,cells); boundary = boundary_faces(cells)
    if set(map(tuple,np.sort(boundary,axis=1))) != set(map(tuple,np.sort(stored_faces,axis=1))):
        raise ValueError('stored_surface_does_not_match_tetra_boundary')
    p,c = torch.from_numpy(points.copy()),torch.from_numpy(cells.copy())
    with torch.inference_mode():
        mesh = Mesh(points=p,cells=c)
        volume = mesh.cell_areas.numpy(); metrics = {k:v.numpy() for k,v in mesh.quality_metrics.items()}
    checks = {'volumes':compare(volume,ref['volumes'],0),
              **{k:compare(metrics[k],ref[k],0) for k in ('edge_length_ratio','aspect_ratio')}}
    bad = sicn < .1
    if int(bad.sum())!=160 or not (np.array_equal(p.numpy(),points) and np.array_equal(c.numpy(),cells)):
        raise ValueError('bound_mesh_changed')
    triangles = points[boundary].astype(np.float32)
    rows = np.zeros(len(triangles),dtype=[('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    rows['vertices'] = triangles
    stl = args.output/'tetra-boundary-private.stl'
    with stl.open('xb') as stream:
        stream.write(b'PRIVATE tetra boundary; not native CAD or released geometry'.ljust(80,b' '))
        stream.write(struct.pack('<I',len(rows))); rows.tofile(stream)
    topology = mesh_summary(load_binary_stl(stl))
    export_ok = (topology['edge_manifold_closed'] and topology['winding_consistent_on_two_face_edges']
                 and topology['zero_area_triangles']==0 and topology['duplicate_triangles_ignoring_winding']==0
                 and topology['connected_vertex_components']==1)
    arrays = args.output/'nemo-metrics-private.npz'
    np.savez_compressed(arrays,element_tags=element_tags[0],gmsh_minSICN=sicn,volumes=volume,**metrics)
    report = {'schema':'m64-nemo-picogk-bridge/v1','execution':'actual_PhysicsNeMo_CPU_float64',
        'input_sha256':MESH_SHA,'prior_report_sha256':REPORT_SHA,'companion_sha256':COMPANION_SHA,
        'source_sha256':pins[Path(__file__)],'versions':versions,'library_source_sha256':libraries,
        'tetrahedra':len(cells),'points':len(points),'comparisons':checks,
        'metrics':{k:summary(v) for k,v in metrics.items()},
        'gmsh_rejected_elements':int(bad.sum()),'gmsh_rejected_aspect_ratio':summary(metrics['aspect_ratio'][bad]),
        'gmsh_rejected_quality_score':summary(metrics['quality_score'][bad]),
        'minSICN_is_not_PhysicsNeMo_quality_score':True,'volume_sum':float(volume.sum()),
        'boundary_STL_sha256':sha(stl),'boundary_STL_topology':topology,'boundary_export_checks_passed':bool(export_ok),
        'STL_float32_max_coordinate_rounding':float(np.abs(points[boundary]-triangles).max()),
        'metrics_sha256':sha(arrays),'input_and_source_unchanged':all(sha(p)==s for p,s in pins.items()),
        'installed_library_unchanged':all(sha(library_root/p)==s for p,s in libraries.items()),
        'native_BRep_replaced':False,'CUDA_run':False,'manufacturing_authorized':False,'CAE_authorized':False,
        'elapsed_seconds':time.monotonic()-started}
    report['arithmetic_and_bridge_passed'] = (all(v['passed'] for v in checks.values()) and export_ok
        and report['input_and_source_unchanged'] and report['installed_library_unchanged']
        and all(v['nonfinite']==0 for v in report['metrics'].values()))
    with (args.output/'report.json').open('x') as stream: json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps({k:report[k] for k in ('tetrahedra','gmsh_rejected_elements','arithmetic_and_bridge_passed')}))
    return 0 if report['arithmetic_and_bridge_passed'] else 2


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','report','companion','output'): parser.add_argument('--'+name,type=Path,required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
