"""Compare complete accepted carrier fields without averaging integration-point peaks."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def weighted_quantile(values,weights,fraction):
    if not 0<fraction<=1 or len(values)!=len(weights) or not len(values):raise ValueError('Invalid weighted distribution')
    if not np.isfinite(values).all() or not np.isfinite(weights).all() or not np.all(weights>0):raise ValueError('Finite positive integration weights required')
    order=np.argsort(values);total=np.cumsum(weights[order]);return float(values[order[np.searchsorted(total,fraction*total[-1])]])


def samples(vertices,cells,stress):
    if cells.shape[1]==4:
        points=vertices[cells];jac=np.transpose(points[:,1:]-points[:,0,None,:],(0,2,1));volume=np.linalg.det(jac)/6
        return points.mean(1),volume
    low=(5-np.sqrt(5.))/20;bary=np.full((4,4),low);np.fill_diagonal(bary,1-3*low);grad=np.array([[-1,-1,-1],[1,0,0],[0,1,0],[0,0,1]])
    edges=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)];shape=np.column_stack([bary*(2*bary-1),np.stack([4*bary[:,i]*bary[:,j]for i,j in edges],axis=1)])
    derivatives=[np.vstack([(4*row-1)[:,None]*grad,np.stack([4*(row[i]*grad[j]+row[j]*grad[i])for i,j in edges])])for row in bary]
    positions=np.empty((len(cells),4,3));weights=np.empty((len(cells),4))
    for start in range(0,len(cells),8192):
        stop=min(start+8192,len(cells));points=vertices[cells[start:stop]];positions[start:stop]=np.einsum('ik,nkj->nij',shape,points)
        for ip,derivative in enumerate(derivatives):weights[start:stop,ip]=np.linalg.det(np.einsum('nki,kj->nij',points-points[:,0,None,:],derivative))/24
    return positions.reshape(-1,3),weights.ravel()


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--cases',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Fresh comparison required')
    cases=json.loads(args.cases.read_text());rows=[];sources={str(args.cases):sha(args.cases),str(Path(__file__)):sha(Path(__file__))}
    for item in cases:
        prep=Path(item['preparation']);assessment=Path(item['assessment']);report=json.loads(assessment.read_text());results=assessment.with_name('results.npz');energy=Path(item['energy'])if item.get('energy')else assessment
        energy_report=json.loads(energy.read_text())
        if report['status']not in ['complete_linear_C3D4_results_and_equilibrium_passed','complete_linear_C3D10_results_equilibrium_and_energy_passed']:raise ValueError('Unaccepted full field')
        if report['output_sha256']!=sha(results) or sha(prep/'transport.npz')not in report['source_sha256'].values():raise ValueError('Result or geometry identity differs')
        if energy_report.get('relative_energy_residual',1)>1e-4:raise ValueError('Independent stress energy required')
        with np.load(prep/'transport.npz',allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy()
        with np.load(results,allow_pickle=False)as data:stress=data['stress'].copy();vm=data['VM'].copy()
        positions,weights=samples(v,cells,stress)
        if len(vm)!=len(weights)or not np.all(weights>0):raise ValueError('Complete positive integration roster required')
        central=abs(positions[:,0])<=260;row=dict(label=item['label'],elements=len(cells),nodes=len(v),order=cells.shape[1],displacement_max_mm=report['displacement_max_mm'],compliance_Nmm=report['external_work_Nmm'],global_peak_VM_MPa=float(vm.max()),volume_weighted_p95_VM_MPa=weighted_quantile(vm,weights,.95),central_peak_VM_MPa=float(vm[central].max()),central_volume_weighted_p95_VM_MPa=weighted_quantile(vm[central],weights[central],.95),volume_mm3=float(weights.sum()),independent_energy_relative_residual=energy_report['relative_energy_residual'],central_exclusion_does_not_qualify_global_peak=True)
        rows.append(row)
        for path in [assessment,energy,results,prep/'transport.npz']:sources[str(path)]=sha(path)
    comparisons=[]
    for left,right in zip(rows,rows[1:]):
        changes={key:abs(right[key]-left[key])/abs(right[key])for key in ['displacement_max_mm','compliance_Nmm','global_peak_VM_MPa','volume_weighted_p95_VM_MPa','central_peak_VM_MPa','central_volume_weighted_p95_VM_MPa']}
        comparisons.append(dict(left=left['label'],right=right['label'],relative_change_using_finer_denominator=changes,within_limits=all(value<=(.02 if key in ['displacement_max_mm','compliance_Nmm']else .05)for key,value in changes.items())))
    args.output.write_text(json.dumps(dict(rows=rows,comparisons=comparisons,convergence_demonstrated=len(comparisons)>=2 and all(row['within_limits']for row in comparisons[-2:]),source_sha256=sources),indent=2)+'\n')
    print(json.dumps(rows))


if __name__=='__main__':main()
