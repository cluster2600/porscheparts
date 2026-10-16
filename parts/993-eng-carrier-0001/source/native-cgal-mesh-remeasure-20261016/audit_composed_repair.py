"""Compose original exact-to-float conversion with DIRECT original-to-final distances."""
import argparse,hashlib,importlib.util,json,math
from fractions import Fraction as Q
from pathlib import Path
import numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['original_native_job','final_snap_job','direct_distance_job','frozen_limit_job','plan','output']:p.add_argument(n,type=Path)
    p.add_argument('--conversion-module',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('frozen_conversion_helpers',a.conversion_module);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    original,final,distance,frozen=a.original_native_job,a.final_snap_job,a.direct_distance_job,a.frozen_limit_job
    files=[Path(__file__),a.conversion_module,a.plan,original/'result.mesh64.exact',original/'result.npz',final/'result.npz']
    for job in [original,final,distance,frozen]:
        files += [job/n for n in ['native.json','audit.json','execution-receipt.json'] if (job/n).exists()]
    before={str(f):sha(f) for f in files}
    for job in [original,distance]:h.validate_execution(job/'execution-receipt.json')
    e=json.loads((final/'execution-receipt.json').read_text());assert e['identities_unchanged'] and e['owned_scope_inactive']
    assert all(sha(f)==value for f,value in {**e['inputs_sha256'],**e['copied_sources_sha256']}.items())
    n=json.loads((original/'native.json').read_text());na=json.loads((original/'audit.json').read_text())
    s=json.loads((final/'native.json').read_text());sa=json.loads((final/'audit.json').read_text());d=json.loads((distance/'audit.json').read_text())
    f=json.loads((frozen/'audit.json').read_text());fn=json.loads((frozen/'native.json').read_text());plan=json.loads(a.plan.read_text())
    assert na['native_exact_gate_pass'] and na['native']==n and n['bbox_parent_matches']==0
    assert n['exact_output_self_intersection_free'] and n['exact_collinear_output_triangles']==0
    assert sa['native_gate_pass'] and sa['topology_gate_pass'] and sa['native']==s
    assert s['native_return'] and s['post_double_self_intersection_free'] and s['exact_collinear_output_triangles']==0 and s['all_output_coordinates_exactly_double']
    assert s['snap_grid_bits']==fn['snap_grid_bits']==51 and s['iteration_budget']==fn['iteration_budget']==5
    assert d['pass'] and d['native_geometry_gate_pass'] and d['topology_gate_pass']
    assert na['result_sha256']==sha(original/'result.npz')==d['input_sha256']==plan['original_float_sha256']
    assert na['exact_result_sha256']==sha(original/'result.mesh64.exact')
    assert sa['result_sha256']==sha(final/'result.npz')==d['result_sha256']
    assert d['plan_sha256']==sha(a.plan) and d['candidate_sha256']==sa['input_sha256']
    for key,name in [('origin_native_sha256','native.json'),('origin_audit_sha256','audit.json'),('origin_execution_receipt_sha256','execution-receipt.json')]:assert d[key]==sha(final/name)
    limit_float=plan['frozen_shape_drift_limit_mm'];assert limit_float==f['shape_drift_limit_mm']==fn['cumulative_rounding_budget_mm']==d['shape_drift_limit_mm']
    assert f['shape_drift_limit_source']=='iterations*norm(native_grid_step)/2'
    conversion=h.verify_indexed_conversion(original/'result.mesh64.exact',original/'result.npz',Q(n['maximum_coordinate_rounding_squared_mm2_exact']))
    assert d['exact_distance']['input_to_output']['samples']==conversion['verified_vertices']+conversion['verified_faces']
    with np.load(final/'result.npz') as arrays:assert d['exact_distance']['output_to_input']['samples']==len(arrays['vertices'])+len(arrays['faces'])
    limit=Q.from_float(limit_float);e2=Q(conversion['maximum_distance_squared_exact']);directions={}
    for direction in ['input_to_output','output_to_input']:
        metric=d['exact_distance'][direction];d2=Q(metric['maximum_distance_squared_exact'])
        directions[direction]={'distance_witness_upper_bound_squared_exact':str(d2),'conversion_upper_bound_squared_exact':str(e2),'composed_upper_bound_mm_approx':math.sqrt(float(d2))+math.sqrt(float(e2)),'finite_samples':metric['samples'],'pass':h.bounded_sum(d2,e2,limit)}
    assert all(sha(f)==value for f,value in before.items())
    result={'schema':'original-exact-to-repaired-final-composed-finite-drift-v1','pass':all(d['pass'] for d in directions.values()),'inputs_sha256':before,'identities_unchanged':True,'original_shape_drift_limit_mm':limit_float,'conversion':conversion,'directions':directions,
        'measurement_chain':'Original sealed exact geometry → original indexed float export (E); DIRECT exact original-float triangle-soup to final distances (D). No addition of separate snap-to-snap distances, no assumption of face-index correspondence after repair.',
        'scope':'All original exact vertices/face-centroids and final vertices/face-centroids, bidirectional finite samples; NOT continuous Hausdorff. Original exact-to-float triangle correspondence alone has its original continuous E bound.',
        'parent_scope':'Changed repaired faces have no inherited positive parent/anchor proof. Geometry/distance admission does not supply one; semantic exposure/contact audits remain separate.'}
    (a.output/'composed-drift.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'directions':directions}));return 0 if result['pass'] else 2

if __name__=='__main__':raise SystemExit(main())
