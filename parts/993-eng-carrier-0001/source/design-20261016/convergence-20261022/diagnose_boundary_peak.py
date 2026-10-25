"""Locate admitted stress peaks relative to retained fixed and traction patch rims."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import compare_accepted_fields as fields


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def rim(v,faces,node_ids):
    mask=np.zeros(len(v),dtype=bool);mask[node_ids]=True;patch=faces[np.all(mask[faces],axis=1)]
    if not len(patch):raise ValueError('Complete quadratic patch faces required')
    triangles=np.concatenate([patch[:,ids]for ids in [(0,3,5),(3,1,4),(5,4,2),(3,4,5)]])
    edges=np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1);edges,count=np.unique(edges,axis=0,return_counts=True)
    if not np.all((count==1)|(count==2))or not np.any(count==1):raise ValueError('Manifold open patch rim required')
    return v[edges[count==1]],len(patch)


def distance(point,segments):
    start=segments[:,0];direction=segments[:,1]-start;norm=np.sum(direction*direction,axis=1)
    if not np.all(norm>0):raise ValueError('Nondegenerate patch rim segments required')
    t=np.clip(np.sum((point-start)*direction,axis=1)/norm,0,1);nearest=start+t[:,None]*direction;index=int(np.argmin(np.linalg.norm(nearest-point,axis=1)))
    return dict(distance_mm=float(np.linalg.norm(nearest[index]-point)),nearest_rim_point_mm=nearest[index].tolist())


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--mechanics',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();mesh=a.preparation/'transport.npz';groups=a.preparation/'groups.npz';assessment=a.mechanics/'assessment.json';result=a.mechanics/'results.npz';report=json.loads(assessment.read_text());prepared=a.preparation/'assessment.json'
    if a.output.exists()or report['status']!='complete_linear_C3D10_results_equilibrium_and_energy_passed'or sha(mesh)not in report['source_sha256'].values()or sha(result)!=report['output_sha256']:raise ValueError('Fresh admitted complete T10 field required')
    if sha(prepared)not in report['source_sha256'].values():raise ValueError('Bound preparation contract required')
    with np.load(mesh)as d:v=d['vertices'].copy();c=d['tetrahedra'].copy();skin=d['boundary'].copy()
    with np.load(groups)as d:fixed=np.unique(np.r_[d['end0'],d['end1']]);loaded=np.unique(np.concatenate([d['bolt'+str(i)]for i in range(4)]))
    with np.load(result)as d:vm=d['VM'].copy();reaction_ids=d['reaction_node_indices'].copy()
    if not np.array_equal(np.sort(fixed),np.sort(reaction_ids))or vm.shape!=(len(c)*4,):raise ValueError('Complete fixed reaction and stress rosters required')
    points,weights=fields.samples(v,c,None);central=abs(points[:,0])<=260;global_id=int(np.argmax(vm));ids=np.flatnonzero(central);central_id=int(ids[np.argmax(vm[central])]);support,nfixed=rim(v,skin,fixed);traction,nloaded=rim(v,skin,loaded);rows=[]
    for label,index in [('global',global_id),('central_abs_X_le_260',central_id)]:
        point=points[index];rows.append(dict(region=label,VM_MPa=float(vm[index]),position_mm=point.tolist(),fixed_patch_rim=distance(point,support),traction_patch_rim=distance(point,traction)))
    if not np.allclose(rows[0]['position_mm'],report['peak_integration_point_position_mm'],rtol=0,atol=1e-9)or rows[0]['VM_MPa']!=report['integration_point_VM_max_MPa']:raise ValueError('Independent peak reconstruction differs')
    out=dict(status='accepted_field_patch_rim_peak_diagnostic_completed',peaks=rows,fixed_quadratic_faces=nfixed,traction_quadratic_faces=nloaded,all_integration_points_retained=True,stress_observables_excluded=False,singularity_proved=False,convergence_demonstrated=False,scope='Distance to piecewise-linear displayed quadratic patch rims is a diagnostic, not a continuum singularity proof or a stress exclusion',source_sha256={str(x):sha(x)for x in [mesh,groups,assessment,result,prepared,Path(__file__),Path(fields.__file__)]});a.output.mkdir();(a.output/'assessment.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(rows))


if __name__=='__main__':main()
