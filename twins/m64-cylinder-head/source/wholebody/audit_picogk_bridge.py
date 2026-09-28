#!/usr/bin/env python3
"""Reuse bounded surface diagnostics on a PicoGK tetra-boundary roundtrip.

Not a native CAD-distance certificate. The original STEP-specific coordinator
is deliberately not used with invented STEP provenance.
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
from compare_meshes import candidate_provenance, read_mesh, surface_distances, sha256

MASTER_SHA='1029336715767630c07926b5c54e1d883e183ce0ebe3f7fb8d752455db9acd0a'


def run(args):
    if args.output.exists() or sha256(args.master)!=MASTER_SHA:
        raise ValueError('fresh_output_and_exact_tetra_boundary_required')
    pins={Path(__file__):sha256(__file__),args.master:MASTER_SHA,
          args.candidate:sha256(args.candidate),args.candidate.parent/'run-report.json':sha256(args.candidate.parent/'run-report.json')}
    receipt=candidate_provenance(args.voxel,args.candidate,MASTER_SHA)
    if receipt['expected_triangles']>5_000_000: raise ValueError('five_million_triangle_audit_budget_exceeded')
    start=time.monotonic()
    master,original=read_mesh(args.master); candidate,topology=read_mesh(args.candidate)
    if topology['triangles']!=receipt['expected_triangles']: raise ValueError('triangle_count_changed')
    forward=surface_distances(master,candidate,512,917,16)
    reverse=surface_distances(candidate,master,512,918,16)
    clean=(topology['edge_manifold_closed'] and topology['winding_consistent_on_two_face_edges']
           and topology['zero_area_triangles']==0 and topology['duplicate_triangles_ignoring_winding']==0)
    same=(original['euler_characteristic']==topology['euler_characteristic']
          and original['connected_vertex_components']==topology['connected_vertex_components'])
    within=max(d['distance_scan_units']['maximum'] for d in (forward,reverse))<=.040
    report={'schema':'m64-picogk-tetra-boundary-audit/v1','source_sha256':pins[Path(__file__)],
        'master_sha256':MASTER_SHA,'candidate':receipt,'mesh_topology':topology,
        'helper_sha256':{name:sha256(Path(__file__).resolve().parents[1]/'picogk'/name)
                         for name in ('compare_meshes.py','export_master.py')},
        'versions':{name:metadata.version(name) for name in ('numpy','trimesh','scipy','rtree')},
        'topology_checks_passed':bool(clean and same),
        'relative_signed_volume_difference':float(candidate.volume/master.volume-1),
        'master_to_candidate':forward,'candidate_to_master':reverse,
        'all_1024_sample_distances_within_0p040':bool(within),
        'sample_distances_are_not_continuous_or_native_CAD_bounds':True,
        'candidate_selected_as_native_CAD':False,'manufacturing_authorized':False,
        'length_unit':'uncalibrated_scan_unit','input_and_source_unchanged':all(sha256(p)==s for p,s in pins.items()),
        'elapsed_seconds':time.monotonic()-start,
        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)}
    with args.output.open('x') as stream: json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps({k:report[k] for k in ('topology_checks_passed','all_1024_sample_distances_within_0p040','elapsed_seconds')}))
    return 0 if clean and same and within and report['input_and_source_unchanged'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('master','candidate','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--voxel',type=float,required=True)
    args=parser.parse_args(); signal.alarm(480)
    raise SystemExit(run(args))
