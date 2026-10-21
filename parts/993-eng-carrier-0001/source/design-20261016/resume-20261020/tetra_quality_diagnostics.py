"""Full-cell quality diagnostics, with no invented mechanical acceptance limit."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    with np.load(a.mesh,allow_pickle=False) as data:
        v=data['vertices'];cells=data['tetrahedra']
    ratios=[];conditions=[];altitudes=[];edge_ratios=[]
    for start in range(0,len(cells),10000):
        x=v[cells[start:start+10000]]
        jac=np.stack([x[:,j]-x[:,0] for j in (1,2,3)],axis=2)
        det=np.linalg.det(jac)
        edges=np.stack([np.sum((x[:,i]-x[:,j])**2,axis=1)for i,j in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]],axis=1)
        ratios.append(12*np.cbrt((det/2)**2)/edges.sum(axis=1))
        sv=np.linalg.svd(jac,compute_uv=False)
        conditions.append(sv[:,0]/sv[:,-1])
        areas=np.stack([np.linalg.norm(np.cross(x[:,j]-x[:,i],x[:,k]-x[:,i]),axis=1) for i,j,k in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]],axis=1)
        altitudes.append(det/areas.max(axis=1))
        edge_ratios.append(np.sqrt(edges.max(axis=1)/edges.min(axis=1)))
    values={k:np.concatenate(a0) for k,a0 in [('mean_ratio',ratios),('Jacobian_condition_2norm',conditions),('minimum_altitude_mm',altitudes),('longest_to_shortest_edge',edge_ratios)]}
    summary={}
    for key,array in values.items():
        if not np.isfinite(array).all():raise ValueError('Nonfinite diagnostic')
        index=int(array.argmax() if key in ['Jacobian_condition_2norm','longest_to_shortest_edge'] else array.argmin())
        summary[key]=dict(minimum=float(array.min()),maximum=float(array.max()),quantiles=dict(zip(['p0.1','p1','p10','p50','p90','p99','p99.9'],map(float,np.quantile(array,[.001,.01,.1,.5,.9,.99,.999])))),worst_cell_zero_based=index,worst_centroid_mm=v[cells[index]].mean(axis=0).tolist())
    np.savez_compressed(a.output/'quality.npz',**values)
    result=dict(status='all_cell_quality_diagnostics_completed',cells=len(cells),metrics=summary,
        formula='mean_ratio = 12*(3*V)^(2/3)/sum(squared edge lengths); regular tetrahedron = 1. Jacobian condition uses the stored local node ordering.',
        acceptance_threshold=None,mechanical_mesh_admitted=False,source_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest())
    (a.output/'assessment.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cells=len(cells),metrics={k:dict(minimum=d['minimum'],maximum=d['maximum'])for k,d in summary.items()})))

if __name__=='__main__':main()
