"""Certify finite exact-native/snap samples under a frozen bound; no geometry edits."""
import argparse,hashlib,json,math,shutil,sys
from fractions import Fraction
from pathlib import Path
import numpy as np

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def bounded_sum(d2,e2,limit):
    """sqrt(d2)+sqrt(e2)<=limit, using rational comparisons only."""
    assert d2>=0 and e2>=0 and limit>=0
    margin=limit*limit-d2-e2
    return margin>=0 and margin*margin>=4*d2*e2

def validate_execution(path):
    execution=json.loads(path.read_text())
    assert execution['status']=='executed' and execution['identities_unchanged'] and execution['owned_scope_inactive']
    assert all(sha(p)==value for p,value in {**execution['inputs_sha256'],**execution['copied_sources_sha256']}.items())
    return execution

def verify_indexed_conversion(exact_path,mesh_path,claimed):
    """Independent rational check of every paired vertex and every face index."""
    with np.load(mesh_path,allow_pickle=False) as arrays:
        v=arrays['vertices'];f=arrays['faces']
        assert v.dtype==np.float64 and np.isfinite(v).all() and np.issubdtype(f.dtype,np.integer)
        assert v.ndim==f.ndim==2 and v.shape[1]==f.shape[1]==3
        maximum=Fraction(0);worst=None
        with exact_path.open() as stream:
            nv,nf=map(int,stream.readline().split());assert (nv,nf)==(len(v),len(f))
            for i,row in enumerate(v):
                exact=[Fraction(s) for s in stream.readline().split()];assert len(exact)==3
                squared=sum((x-Fraction.from_float(float(y)))**2 for x,y in zip(exact,row))
                if squared>maximum:maximum=squared;worst=i
            for row in f:assert list(map(int,stream.readline().split()))==row.tolist()
            assert not stream.read().strip()
    assert maximum==claimed, 'Native conversion metric differs from independent rational recomputation'
    return {'verified_vertices':nv,'verified_faces':nf,'maximum_distance_squared_exact':str(maximum),'worst_vertex':worst,
      'proof':'Identical triangle indices and barycentric correspondence give continuous bidirectional exact-native/float-export distance <= maximum paired vertex displacement, including triangles that collapse after rounding.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('native_job',type=Path);p.add_argument('snap_job',type=Path);p.add_argument('distance_job',type=Path)
    p.add_argument('frozen_limit_job',type=Path);p.add_argument('output',type=Path);p.add_argument('--plan',type=Path)
    args=p.parse_args();out=args.output.resolve();assert not out.exists();out.mkdir(parents=True)
    jobs=[args.native_job.resolve(),args.snap_job.resolve(),args.distance_job.resolve(),args.frozen_limit_job.resolve()]
    native_job,snap_job,distance_job,frozen=jobs
    input_files=[Path(__file__).resolve()]
    for job in jobs:
        input_files += [job/name for name in ['native.json','audit.json','execution-receipt.json'] if (job/name).is_file()]
    input_files += [native_job/'result.npz',native_job/'result.mesh64.exact',snap_job/'result.npz']
    if args.plan:input_files.append(args.plan.resolve())
    before={str(path):sha(path) for path in input_files}
    for name,job in [('native',native_job),('snap',snap_job),('distance',distance_job)]:
        validate_execution(job/'execution-receipt.json')
        for file in ['audit.json','execution-receipt.json','native.json']:
            if (job/file).is_file():shutil.copyfile(job/file,out/(name+'-'+file))
    n=json.loads((native_job/'native.json').read_text());a=json.loads((native_job/'audit.json').read_text())
    s=json.loads((snap_job/'native.json').read_text());sa=json.loads((snap_job/'audit.json').read_text())
    d=json.loads((distance_job/'audit.json').read_text());frozen_a=json.loads((frozen/'audit.json').read_text());frozen_n=json.loads((frozen/'native.json').read_text())
    assert a['native_exact_gate_pass'] and n==a['native'] and n['exact_output_self_intersection_free'] and n['exact_collinear_output_triangles']==0 and n['source_face_lineage_complete']
    assert a['result_sha256']==sha(native_job/'result.npz') and a['exact_result_sha256']==sha(native_job/'result.mesh64.exact')
    assert s['native_return'] and s['all_output_coordinates_exactly_double'] and s['post_double_self_intersection_free'] and s['exact_collinear_output_triangles']==0 and s['source_face_lineage_complete']
    assert s['snap_grid_bits']==frozen_n['snap_grid_bits']==51 and s['iteration_budget']==frozen_n['iteration_budget']==5
    assert sa['native_gate_pass'] and sa['topology_gate_pass'] and sa['result_sha256']==sha(snap_job/'result.npz')
    assert sa['input_sha256']==sha(native_job/'result.npz')
    assert d['pass'] and d['native_geometry_gate_pass'] and d['topology_gate_pass'] and d['drift_gate_pass']
    assert d['input_sha256']==sha(native_job/'result.npz') and d['result_sha256']==sha(snap_job/'result.npz')
    for key,file in [('origin_native_sha256','native.json'),('origin_audit_sha256','audit.json'),('origin_execution_receipt_sha256','execution-receipt.json')]:assert d[key]==sha(snap_job/file)
    assert frozen_a['shape_drift_limit_source']=='iterations*norm(native_grid_step)/2'
    limit_float=frozen_a['shape_drift_limit_mm'];limit=Fraction.from_float(float(limit_float));assert limit>=0
    assert frozen_n['cumulative_rounding_budget_mm']==limit_float
    if args.plan:
        plan=json.loads(args.plan.read_text());frozen_plan=plan['downstream_frozen']
        assert frozen_plan['original_shape_drift_limit_mm']==limit_float
        assert frozen_plan['original_snap_audit_sha256']==sha(frozen/'audit.json')
        assert frozen_plan['original_snap_native_sha256']==sha(frozen/'native.json')
        assert [plan['inputs_sha256'][role]['sha256'] for role in ['roofs','mask','part']]==a['input_sha256']
    conversion=verify_indexed_conversion(native_job/'result.mesh64.exact',native_job/'result.npz',Fraction(n['maximum_coordinate_rounding_squared_mm2_exact']))
    assert d['exact_distance']['input_to_output']['samples']==conversion['verified_vertices']+conversion['verified_faces']
    with np.load(snap_job/'result.npz',allow_pickle=False) as final_arrays:
        assert d['exact_distance']['output_to_input']['samples']==len(final_arrays['vertices'])+len(final_arrays['faces'])
    e2=Fraction(conversion['maximum_distance_squared_exact']);directions={}
    for direction in ['input_to_output','output_to_input']:
        metric=d['exact_distance'][direction];d2=Fraction(metric['maximum_distance_squared_exact'])
        passed=bounded_sum(d2,e2,limit)
        directions[direction]={'distance_witness_upper_bound_squared_exact':str(d2),'conversion_upper_bound_squared_exact':str(e2),
          'composed_upper_bound_mm_approx':math.sqrt(float(d2))+math.sqrt(float(e2)),
          'limit_mm':limit_float,'pass':passed,'finite_samples':metric['samples']}
    unchanged=all(sha(path)==value for path,value in before.items());assert unchanged
    result={'schema':'exact-native-to-snap-composed-finite-drift-v1','pass':all(row['pass'] for row in directions.values()),
      'inputs_sha256':before,'identities_unchanged':unchanged,'original_shape_drift_limit_mm':limit_float,'limit_exact':str(limit),
      'conversion':conversion,'directions':directions,
      'exact_comparison':'For D2,E2,L>=0: L2-D2-E2>=0 and (L2-D2-E2)^2>=4*D2*E2; no floating comparison of distances.',
      'scope':'All exact-native vertices and exact rational face centroids to final snap; all final-snap vertices and exact rational face centroids to exact-native. Triangle conversion correspondence is continuous, but the final composed admission is finite samples, NOT a continuous Hausdorff certificate.',
      'geometry_modified':False,'other_gates':'Native exact, snap native/topology and exact-distance receipts checked. Contact adjudication remains a separate required gate.'}
    (out/'composed-drift.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'limit_mm':limit_float,'directions':directions}))
    return 0 if result['pass'] else 2

if __name__=='__main__':sys.exit(main())
