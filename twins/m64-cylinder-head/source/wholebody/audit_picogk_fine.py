#!/usr/bin/env python3
"""Audit the existing 17.2M-triangle PicoGK result on bounded native Linux RAM.

Reuses the unchanged coarse auditor's topology/distance functions and thresholds.
Only the explicit resource ceiling differs; the original 5M audit stays frozen.
"""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import resource
import signal
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'picogk'))
from compare_meshes import candidate_provenance,read_mesh,surface_distances,sha256
from export_master import mesh_summary
from run_local_surface_trial import native

MASTER='1029336715767630c07926b5c54e1d883e183ce0ebe3f7fb8d752455db9acd0a'
CANDIDATE='d1e8fa5eb3740d2e1a86ab2cfc2221d478503f01b39221f785f1400201eaf652'
HELPERS={'compare_meshes.py':'f2d21b5996c9e7a435d2e067e364720fd750935d9e9d748cc22e0c4b9c65b694',
         'export_master.py':'34bb2dcd591e92b1ae6f0e8a75f2f858448319b4db4dada6eb364f3c0a1242be'}
VERSIONS={'numpy':'2.3.5','trimesh':'5.1.0','scipy':'1.16.3','rtree':'1.4.1'}


def run(args):
    import numpy as np
    helpers=Path(__file__).resolve().parents[1]/'picogk'
    pins={args.master:MASTER,args.candidate:CANDIDATE,Path(__file__):sha256(__file__),
          args.candidate.parent/'run-report.json':sha256(args.candidate.parent/'run-report.json'),
          **{helpers/name:pin for name,pin in HELPERS.items()}}
    if (args.output.exists() or sys.platform!='linux'
            or any(p.is_symlink() or sha256(p)!=s for p,s in pins.items())
            or any(metadata.version(k)!=v for k,v in VERSIONS.items())):
        raise ValueError('exact_fine_candidate_helpers_Linux_runtime_and_new_output_required')
    resource.setrlimit(resource.RLIMIT_AS,(64*1024**3,64*1024**3));signal.alarm(1200)
    proof=candidate_provenance(.15,args.candidate,MASTER)
    if proof['expected_triangles']!=17214748:raise ValueError('exact_triangle_budget_required')
    witness=mesh_summary(np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])[
        np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]])])
    if (not witness['edge_manifold_closed'] or not witness['winding_consistent_on_two_face_edges']
            or abs(witness['signed_volume_scan_units_cubed']-1/6)>1e-14):
        raise ValueError('analytic_tetrahedron_witness_failed')
    began=time.monotonic()
    report=dict(schema='m64-picogk-fine-audit/v1',status='incomplete',source_sha256=pins[Path(__file__)],
        master_sha256=MASTER,candidate=proof,helper_sha256=HELPERS,versions=VERSIONS,
        memory_limit_bytes=64*1024**3,time_limit_seconds=1200,threshold_scan_units=.040,
        original_five_million_audit_unchanged=True,manufacturing_authorized=False,
        native_CAD_distance_certified=False,continuous_Hausdorff_bound=False)
    native.save(args.output,report)
    try:
        master,original=read_mesh(args.master);candidate,topology=read_mesh(args.candidate)
        if topology['triangles']!=proof['expected_triangles']:raise ValueError('triangle_count_changed')
        report['mesh_topology']=topology;native.save(args.output,report)
        forward=surface_distances(master,candidate,512,917,16)
        reverse=surface_distances(candidate,master,512,918,16)
        clean=(topology['edge_manifold_closed'] and topology['winding_consistent_on_two_face_edges']
            and topology['zero_area_triangles']==topology['duplicate_triangles_ignoring_winding']==0)
        same=all(original[k]==topology[k] for k in ('euler_characteristic','connected_vertex_components'))
        report.update(status='completed',topology_checks_passed=bool(clean and same),
            all_1024_sample_distances_within_0p040=bool(max(d['distance_scan_units']['maximum'] for d in (forward,reverse))<=.040),
            relative_signed_volume_difference=float(candidate.volume/master.volume-1),
            master_to_candidate=forward,candidate_to_master=reverse)
    except Exception as exc:report.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    finally:
        report.update(inputs_and_sources_unchanged=all(sha256(p)==s for p,s in pins.items()),
            elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        native.save(args.output,report)
    print(json.dumps(report))
    return 0 if (report.get('topology_checks_passed') and report.get('all_1024_sample_distances_within_0p040')
                 and report['inputs_and_sources_unchanged']) else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('master','candidate','output'):p.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
