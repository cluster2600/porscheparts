#!/usr/bin/env python3
"""Bounded fTetWild alternative; approximate polygon envelope, never new CAD."""
import argparse
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import time
import numpy as np
from trial_meshers_2026 import MESH_SHA,boundary,read_gmsh,audit_output,native


def run(args):
    import gmsh
    import wildmeshing
    if (args.envelope not in (.02,.005) or args.output.exists() or args.input.is_symlink() or native.sha256(args.input)!=MESH_SHA
            or metadata.version('wildmeshing')!='0.4.1' or gmsh.__version__!='4.15.2'
            or np.__version__!='2.2.6'):
        raise ValueError('exact_runtime_input_and_new_output_required')
    args.output.mkdir(mode=0o700,parents=True); started=time.monotonic()
    helper=Path(__file__).with_name('trial_meshers_2026.py')
    pins={args.input:MESH_SHA,Path(__file__):native.sha256(__file__),helper:native.sha256(helper)}
    report={'schema':'m64-envelope-mesher-trial/v1','status':'incomplete',
        'input_sha256':MESH_SHA,'source_sha256':pins[Path(__file__)],'helper_sha256':pins[helper],
        'wildmeshing_version':'0.4.1','native_CAD_conformance_certified':False,
        'physical_millimetres_certified':False,'manufacturing_authorized':False,'CAE_authorized':False,
        'input_is_previous_linear_volume_mesh_boundary_not_exact_CAD':True,
        'boundary_roles_transferred':False}
    target=args.output/'report.json'; native.save(target,report)
    gmsh.initialize(['envelope','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        points,cells,stored,_=read_gmsh(args.input); faces=boundary(cells)
        if set(map(tuple,np.sort(faces,axis=1)))!=set(map(tuple,np.sort(stored,axis=1))):
            raise ValueError('stored_boundary_mismatch')
        used,inverse=np.unique(faces,return_inverse=True); surface=points[used]
        faces=inverse.reshape(-1,3).astype(np.int32)
        diagonal=float(np.linalg.norm(np.ptp(surface,axis=0)))
        options=dict(stop_quality=8.,max_its=80,max_threads=16,epsilon=args.envelope/diagonal,
                     edge_length_r=3./diagonal,skip_simplify=True,coarsen=False)
        report.update(options=options,requested_polygon_envelope_scan_units=args.envelope,
            input_surface_vertices=len(surface),input_surface_triangles=len(faces))
        native.save(target,report)
        engine=wildmeshing.Tetrahedralizer(**options); engine.set_mesh(surface,faces)
        engine.tetrahedralize()
        p,c,labels=engine.get_tet_mesh(smooth_open_boundary=False,floodfill=False,
            use_input_for_wn=True,manifold_surface=True,correct_surface_orientation=False,all_mesh=False)
        p=np.asarray(p,dtype=np.float64);c=np.asarray(c,dtype=np.int64)
        np.savez_compressed(args.output/'output-private.npz',points=p,cells=c,labels=labels)
        report['mesh']=audit_output(p,c,boundary(c),args.output/'result-private.msh')
        xyz=points[cells];reference=math.fsum(map(float,np.linalg.det(xyz[:,1:]-xyz[:,[0]])/6))
        report['input_polyhedral_volume']=reference
        report['polyhedral_volume_relative_difference']=abs(report['mesh']['tetra_volume']/reference-1)
        report['mesh']['coarse_checks_passed'] &= report['polyhedral_volume_relative_difference']<=.01
        report['status']='completed_diagnostic_only'
    except Exception as exc: report.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    finally:
        gmsh.finalize();report['elapsed_seconds']=time.monotonic()-started
        report['inputs_and_sources_unchanged']=all(native.sha256(p)==s for p,s in pins.items())
        native.save(target,report)
    print(json.dumps(report),flush=True)
    return 0 if report['status']=='completed_diagnostic_only' else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--envelope',type=float,choices=(.02,.005),default=.02,
                   help='Global polygon envelope in provisional scan units; not CAD deviation.')
    for name in ('input','output'):p.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
