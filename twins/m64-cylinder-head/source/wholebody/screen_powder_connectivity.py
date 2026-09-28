#!/usr/bin/env python3
"""Resolution-limited cavity screen: classify empty regions, never fill them.

Surface voxelization can close a narrow passage. A trapped region is therefore
a candidate requiring refinement/inspection, not a prediction of powder flow.
"""
import argparse
import json
from pathlib import Path
import signal
import time

from render_v5_v2 import sha, save
from trial_meshers_2026 import read_gmsh, boundary

MESH_SHA='e73f26de19b7409579cd83579d53bd29d2972e4ad581f9b7887ae1ec9edb3590'


def classify_voids(mesh, pitch):
    import numpy as np
    from scipy import ndimage
    if (pitch not in (.5,1.) or not mesh.is_watertight or not mesh.is_winding_consistent
            or not np.isfinite(mesh.vertices).all()
            or np.prod(np.ceil(mesh.extents/pitch)+5)>50000000):
        raise ValueError('bounded_closed_surface_and_pitch_required')
    skin=mesh.voxelized(pitch)
    occupied=np.asarray(skin.matrix,dtype=bool)
    labels,count=ndimage.label(np.pad(~occupied,1,constant_values=True),
        structure=ndimage.generate_binary_structure(3,1))
    outside=int(labels[0,0,0]); counts=np.bincount(labels.ravel())
    objects=ndimage.find_objects(labels); rows=[]
    for label,box in enumerate(objects,1):
        if label==outside or box is None: continue
        indices=np.flatnonzero((labels[box]==label).ravel())
        selected=indices[np.linspace(0,len(indices)-1,min(8,len(indices)),dtype=int)]
        local=np.column_stack(np.unravel_index(selected,labels[box].shape))
        grid=local+np.array([s.start for s in box])-1
        points=skin.indices_to_points(grid)
        contained=mesh.contains(points)
        kind='material' if contained.all() else 'candidate_void' if not contained.any() else 'ambiguous'
        rows.append(dict(label=label,voxels=int(counts[label]),classification=kind,
                         classification_samples=len(points),volume_scan_units3=float(counts[label]*pitch**3)))
    candidates=[r for r in rows if r['classification']=='candidate_void']
    return dict(pitch_scan_units=pitch,surface_voxel_count=int(occupied.sum()),
        grid_shape=list(map(int,occupied.shape)),enclosed_empty_regions=rows,
        candidate_void_regions=len(candidates),
        candidate_void_volume_scan_units3=sum(r['volume_scan_units3'] for r in candidates),
        ambiguous_regions=sum(r['classification']=='ambiguous' for r in rows),
        surface_fill_used=False,material_classification='up to eight ray-parity samples per enclosed empty region',
        powder_flow_simulated=False,physical_powder_removal_validated=False,
        narrow_passages_below_pitch_may_be_closed=True)


def run(args):
    import gmsh
    import numpy as np
    import trimesh
    if args.output.exists() or args.mesh.is_symlink() or sha(args.mesh)!=MESH_SHA:
        raise ValueError('exact_refined_mesh_and_fresh_output_required')
    source_sha=sha(__file__); started=time.monotonic()
    gmsh.initialize(['powder','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try: points,cells,_,_=read_gmsh(args.mesh)
    finally: gmsh.finalize()
    faces=boundary(cells);used,inverse=np.unique(faces,return_inverse=True)
    mesh=trimesh.Trimesh(points[used],inverse.reshape(-1,3),process=False)
    result=classify_voids(mesh,args.pitch)
    result.update(schema='m64-powder-connectivity-screen/v1',input_mesh_sha256=MESH_SHA,
        source_sha256=source_sha,physical_millimetres_certified=False,manufacturing_authorized=False,
        inputs_unchanged=sha(args.mesh)==MESH_SHA and sha(__file__)==source_sha,
        elapsed_seconds=time.monotonic()-started)
    save(args.output,result); print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pitch',type=float,choices=(.5,1.),required=True)
    signal.alarm(600)
    run(parser.parse_args())
