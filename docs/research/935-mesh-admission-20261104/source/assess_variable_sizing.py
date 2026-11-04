"""Independent admission of an actually completed variable-sizing candidate."""
import argparse
import json
from pathlib import Path
import numpy as np
from trial_planar_flips import sha, save_json, quality, samples, distances
from trial_masked_isotropic_v2 import triangle_keys
from run_constraint_controls import read_off
from run_variable_sizing import bounded


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trial','parent','mask','scan','inspector','topology-python','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--parent-sha256',required=True)
    parser.add_argument('--scan-sha256',required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Existing assessment directory refused.')
    receipt=json.loads((args.trial/'head.execution.json').read_text())
    native=json.loads((args.trial/'head-native.json').read_text())
    if receipt['exit_code']!=0 or receipt['termination_reason'] or not native['remesher_executed']:
        raise SystemExit('Candidate native execution is incomplete or failed.')
    plan=json.loads((args.trial/'plan.json').read_text())
    if sha(args.parent)!=args.parent_sha256 or sha(args.scan)!=args.scan_sha256 or sha(args.mask)!=plan['mask_sha256']:
        raise SystemExit('Reference input hash mismatch.')
    args.output.mkdir(parents=True)
    candidate=args.trial/'candidate.off';candidate_sha=sha(candidate)
    save_json(args.output/'assessment-plan.json',{'candidate_off_sha256':candidate_sha,
        'parent_npz_sha256':args.parent_sha256,'scan_arrays_sha256':args.scan_sha256,
        'mask_sha256':sha(args.mask),'inspector_sha256':sha(args.inspector),
        'source_sha256':sha(Path(__file__)),'gates':plan['head_gates'],
        'sampling_seeds':{'parent':9350701,'candidate':9350702,'scan':9350703},
        'scope':'Independent software/study geometry assessment; no physical qualification.'})
    v2,f2=read_off(candidate)
    if len(v2)!=native['vertices'] or len(f2)!=native['faces']:raise SystemExit('Native OFF import counts differ.')
    np.savez_compressed(args.output/'candidate.npz',vertices=v2,triangles=f2)
    with np.load(args.parent,allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
    np.savez_compressed(args.output/'parent.npz',vertices=v,triangles=f)
    inspector_run=bounded([str(args.inspector),str(candidate)],args.output/'candidate-native.log',300,8*1024**3)
    inspected=json.loads((args.output/'candidate-native.log').read_text()) if not inspector_run['termination_reason'] else {}
    topology_script=Path(__file__).with_name('inspect_vertex_topology.py');topologies={}
    for name in ('parent','candidate'):
        run=bounded([str(args.topology_python),str(topology_script),str(args.output/(name+'.npz'))],args.output/(name+'-topology.log'),300,8*1024**3)
        if run['termination_reason']:raise SystemExit('Topology assessment did not complete.')
        topologies[name]=json.loads((args.output/(name+'-topology.log')).read_text())
        topologies[name]['process_exit_code']=run['exit_code']
    protected=np.atleast_1d(np.loadtxt(args.mask,dtype=np.int64))
    kept=np.isin(triangle_keys(v,f[protected]),triangle_keys(v2,f2))
    before,after=quality(v,f),quality(v2,f2)
    candidate_points=samples(v2,f2,9350702)
    p_to_c=distances(samples(v,f,9350701),v2,f2)
    c_to_p=distances(candidate_points,v,f)
    vertices=distances(v2,v,f)
    with np.load(args.scan,allow_pickle=False) as a:sv,sf=a['vertices'],a['triangles']
    s_to_c=distances(samples(sv,sf,9350703),v2,f2);c_to_s=distances(candidate_points,sv,sf)
    checks={'native_geometry':inspector_run['exit_code']==0 and not inspector_run['termination_reason'],
        'vertex_edge_topology':topologies['parent']['process_exit_code']==0 and topologies['candidate']['process_exit_code']==0,
        'euler_and_components':all(topologies['parent'][k]==topologies['candidate'][k] for k in ('euler_characteristic','edge_connected_components')),
        'exact_protected_triangles':bool(kept.all()),
        'parent_sampled_deviations':max(p_to_c['sampled_max_mm'],c_to_p['sampled_max_mm'])<=.01,
        'all_candidate_vertices_to_parent':vertices['sampled_max_mm']<=.01,
        'relative_volume_change':abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1)<=.0001,
        'material_quality_improvement':1-after['below_0p01']/before['below_0p01']>=.5}
    if sha(candidate)!=candidate_sha or sha(args.parent)!=args.parent_sha256 or sha(args.scan)!=args.scan_sha256:
        raise SystemExit('An input changed during independent assessment.')
    save_json(args.output/'assessment.json',{'before':before,'after':after,'vertices':len(v2),'triangles':len(f2),
        'native_geometry':inspected,'topology':topologies,'protected_triangles_missing_or_changed':int((~kept).sum()),
        'parent_to_candidate':p_to_c,'candidate_to_parent':c_to_p,'all_candidate_vertices_to_parent':vertices,
        'scan_to_candidate':s_to_c,'candidate_to_scan':c_to_s,'checks':checks,
        'accepted_for_volume_study':all(checks.values()),'physical_geometry_accepted':False,
        'manufacturing_authorized':False,'limitations':'Sampled surface distances are not Hausdorff bounds. Study assembly and inferred surfaces do not establish faithful bare-head CAD.'})
    print(json.dumps({'checks':checks,'vertices':len(v2),'triangles':len(f2)}))


if __name__=='__main__':
    main()
