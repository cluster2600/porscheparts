#!/usr/bin/env python3
"""fTetWild on a new, receipt-bound spatially refined native boundary.

The old input-specific runner is unchanged. This remains an approximate
polygon-envelope diagnostic, with no native curved-CAD acceptance implied.
"""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import time

from trial_meshers_2026 import read_gmsh, boundary, audit_output, native
from run_local_surface_trial import BODY_SHA


def run(args):
    import gmsh
    import numpy as np
    import wildmeshing
    mesh=args.trial/'native-trial/mesh/coarse-native-head.msh'
    source_report=args.trial/'native-trial/mesh/mesh-report.json'
    parent=args.trial/'junction-trial.json'
    record=json.loads(source_report.read_text()); prior=json.loads(parent.read_text())
    if (args.output.exists() or mesh.is_symlink() or prior.get('status')!='completed'
            or prior.get('inputs_and_sources_unchanged') is not True
            or prior['mesh_report_sha256']!=native.sha256(source_report)
            or record['native_BRep_sha256']!=BODY_SHA or record['native_input_unchanged'] is not True
            or native.sha256(mesh)!=record['mesh']['sha256']
            or metadata.version('wildmeshing')!='0.4.1' or gmsh.__version__!='4.15.2' or np.__version__!='2.2.6'):
        raise ValueError('fresh_output_exact_runtime_and_bound_native_trial_required')
    args.output.mkdir(mode=0o700)
    pins={p:native.sha256(p) for p in (mesh,source_report,parent,Path(__file__))}
    started=time.monotonic()
    report=dict(schema='m64-junction-envelope-trial/v1',status='incomplete',
        input_sha256=pins[mesh],source_sha256=pins[Path(__file__)],native_BRep_sha256=BODY_SHA,
        requested_polygon_envelope_scan_units=args.envelope,
        input_is_locally_refined_linear_mesh_not_exact_CAD=True,
        native_CAD_conformance_certified=False,physical_millimetres_certified=False,
        boundary_roles_transferred=False,CAE_authorized=False,manufacturing_authorized=False)
    target=args.output/'report.json';native.save(target,report)
    gmsh.initialize(['junction-envelope','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        p,c,stored,_=read_gmsh(mesh);faces=boundary(c)
        if set(map(tuple,np.sort(stored,axis=1)))!=set(map(tuple,np.sort(faces,axis=1))):
            raise ValueError('input_boundary_mismatch')
        used,inverse=np.unique(faces,return_inverse=True)
        surface=p[used];faces=inverse.reshape(-1,3).astype(np.int32)
        diagonal=float(np.linalg.norm(np.ptp(surface,axis=0)))
        options=dict(stop_quality=8.,max_its=80,max_threads=16,
            epsilon=args.envelope/diagonal,edge_length_r=3./diagonal,skip_simplify=True,coarsen=False)
        report.update(options=options,input_surface_triangles=len(faces),input_surface_vertices=len(surface))
        native.save(target,report)
        engine=wildmeshing.Tetrahedralizer(**options);engine.set_mesh(surface,faces);engine.tetrahedralize()
        p,c,labels=engine.get_tet_mesh(smooth_open_boundary=False,floodfill=False,
            use_input_for_wn=True,manifold_surface=True,correct_surface_orientation=False,all_mesh=False)
        p=np.asarray(p,dtype=np.float64);c=np.asarray(c,dtype=np.int64)
        np.savez_compressed(args.output/'output-private.npz',points=p,cells=c,labels=labels)
        report['mesh']=audit_output(p,c,boundary(c),args.output/'result-private.msh')
        report['polyhedral_volume_relative_difference']=abs(report['mesh']['tetra_volume']/record['mesh']['connectivity']['signed_volume_sum']-1)
        report['mesh']['coarse_checks_passed'] &= report['polyhedral_volume_relative_difference']<=.01
        report['status']='completed_diagnostic_only'
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    finally:
        gmsh.finalize()
        report.update(elapsed_seconds=time.monotonic()-started,
            inputs_and_sources_unchanged=all(native.sha256(p)==h for p,h in pins.items()))
        native.save(target,report)
    print(json.dumps(report),flush=True)
    return 0 if report['status']=='completed_diagnostic_only' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trial','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--envelope',type=float,choices=(.02,.005),default=.02)
    raise SystemExit(run(parser.parse_args()))
