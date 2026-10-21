"""Direct original-float to repaired-final exact distances; no geometry execution."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,v,f):
    assert v.dtype==np.float64 and np.isfinite(v).all() and np.issubdtype(f.dtype,np.integer)
    with path.open('w') as stream:
        stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['input','candidate','final_job','plan','output','binary']:p.add_argument(name,type=Path)
    a=p.parse_args();out=a.output;plan=json.loads(a.plan.read_text());input_sha=sha(a.input)
    assert input_sha==plan['original_float_sha256']
    native=json.loads((a.final_job/'native.json').read_text());audit=json.loads((a.final_job/'audit.json').read_text())
    execution=json.loads((a.final_job/'execution-receipt.json').read_text())
    assert execution['identities_unchanged'] and execution['owned_scope_inactive']
    assert audit['native_gate_pass'] and audit['topology_gate_pass'] and native==audit['native']
    assert native['native_return'] and native['post_double_self_intersection_free'] and native['exact_collinear_output_triangles']==0
    assert native['all_output_coordinates_exactly_double'] and native['snap_grid_bits']==51 and native['iteration_budget']==5
    assert audit['input_sha256']==sha(a.candidate) and audit['result_sha256']==sha(a.final_job/'result.npz')
    raw=np.load(a.input,allow_pickle=False);candidate=np.load(a.candidate,allow_pickle=False);final=np.load(a.final_job/'result.npz',allow_pickle=False)
    lookup=final['autorefine_input_face'];assert lookup.dtype==np.int64 and lookup.shape==(len(final['faces']),)
    assert lookup.min()>=0 and lookup.max()<len(candidate['faces'])
    for key in ['source','source_face']:assert np.array_equal(final[key],candidate[key][lookup])
    hints=candidate['historical_snap_input_face'][lookup];assert hints.min()>=0 and hints.max()<len(raw['faces'])
    np.savetxt(out/'distance-search-hints.txt',hints,fmt='%d')
    write(out/'input.mesh64',raw['vertices'],raw['faces']);write(out/'result.mesh64',final['vertices'],final['faces'])
    limit=plan['frozen_shape_drift_limit_mm']
    command=[str(a.binary),str(out/'input.mesh64'),str(out/'result.mesh64'),str(out/'exact-distance.json'),repr(limit),str(out/'distance-search-hints.txt')]
    with (out/'native-distance.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    metric=json.loads((out/'exact-distance.json').read_text()) if (out/'exact-distance.json').is_file() else None
    result={'schema':'direct-original-float-to-local-repair-finite-distance-v1','input_sha256':input_sha,'candidate_sha256':sha(a.candidate),
        'result_sha256':sha(a.final_job/'result.npz'),'plan_sha256':sha(a.plan),'native_returncode':r.returncode,'exact_distance':metric,
        'native_geometry_gate_pass':True,'topology_gate_pass':True,'output_topology':audit['output_topology'],
        'pass':bool(r.returncode==0 and metric and metric['pass']),'shape_drift_limit_mm':limit,
        'origin_native_sha256':sha(a.final_job/'native.json'),'origin_audit_sha256':sha(a.final_job/'audit.json'),
        'origin_execution_receipt_sha256':sha(a.final_job/'execution-receipt.json'),'distance_search_hints_sha256':sha(out/'distance-search-hints.txt'),
        'hint_scope':'Hints compose final-to-repair producer indices with historical repair-to-raw indices; every target triangle distance is checked exactly. Not parent containment nor anchor evidence.',
        'scope':'All original float vertices and exact rational face centroids to final, and all final vertices/centroids to original float. Original collinear triangles handled as exact segments/points. No continuous Hausdorff claim; original exact-to-float E must still be composed under the original frozen bound.'}
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'native_returncode':r.returncode}));return 0 if result['pass'] else 2

if __name__=='__main__':raise SystemExit(main())
