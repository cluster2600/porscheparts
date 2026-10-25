"""Joint maximin SICN for the interior one-ring of the remaining deficient cell."""
import argparse
import json
from pathlib import Path

from mesh_surface import quality_passes,sha
from read_saved import tetra_metrics


def maximize_patch(points,tets,nodes):
    import numpy as np
    from scipy.optimize import minimize
    nodes=np.asarray(nodes,dtype=int)
    incident=np.any(np.isin(tets,nodes),axis=1);star=tets[incident]
    slots=np.full(len(points),-1,dtype=int);slots[nodes]=np.arange(len(nodes));index=slots[star];mask=index>=0
    base=points[star].copy();before=tetra_metrics(base)[0]
    def qualities(x):
        local=base.copy();local[mask]=x[:-1].reshape(-1,3)[index[mask]]
        return tetra_metrics(local)[0]
    bounds=[]
    for node in nodes:
        neighbours=np.unique(tets[np.any(tets==node,axis=1)])
        bounds.extend(zip(points[neighbours].min(axis=0),points[neighbours].max(axis=0)))
    initial=np.r_[points[nodes].ravel(),before.min()-1e-10]
    result=minimize(lambda x:-x[-1],initial,method='SLSQP',bounds=[*bounds,(0,1)],
                    constraints=[dict(type='ineq',fun=lambda x:qualities(x)-x[-1])],
                    options=dict(ftol=1e-12,maxiter=200))
    after=qualities(result.x)
    accepted=bool(result.success and np.isfinite(result.x).all() and after.min()>=.1 and after.min()>=before.min())
    return (result.x[:-1].reshape(-1,3) if accepted else points[nodes].copy()),dict(
        accepted=accepted,minimum_before=float(before.min()),minimum_after=float(after.min()),
        iterations=int(result.nit),message=str(result.message),affected_cells=int(incident.sum()))


if __name__=='__main__':
    import gmsh
    import numpy as np
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();p=args.parent;o=args.output
    parent=json.loads((p/'mesh-report.json').read_text())
    if sha(p/'coolant.msh')!=parent['mesh_sha256']:raise ValueError('Parent changed')
    if o.exists():raise ValueError('Output must be new')
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(p/'coolant.msh'))
        tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order]
        xyz=np.asarray(xyz).reshape(-1,3)[order]*1000
        typ,_,connections=gmsh.model.mesh.getElements(3)
        if list(typ)!=[4]:raise ValueError('Expected tetrahedra')
        tets=np.searchsorted(tags,np.asarray(connections[0]).reshape(-1,4))
        fixed=np.isin(tags,np.unique(gmsh.model.mesh.getElements(2)[2][0]))
        fixed_before=xyz[fixed].copy()
        bad=tetra_metrics(xyz[tets])[0]<.1;seed=np.unique(tets[bad]);seed=seed[~fixed[seed]]
        incident=np.any(np.isin(tets,seed),axis=1);nodes=np.unique(tets[incident]);nodes=nodes[~fixed[nodes]]
        if not 0<len(nodes)<=20:raise ValueError('Joint patch exceeds the declared 20-node compute bound')
        print('JOINT_PATCH',len(nodes),flush=True)
        new,result=maximize_patch(xyz,tets,nodes)
        old=xyz[nodes].copy()
        if result['accepted']:
            xyz[nodes]=new
            for node in nodes:gmsh.model.mesh.setNode(int(tags[node]),xyz[node]*.001,[])
        if not np.array_equal(fixed_before,xyz[fixed]):raise ValueError('Boundary moved')
        q,v=tetra_metrics(xyz[tets]);o.mkdir(parents=True)
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.Binary',0)
        gmsh.write(str(o/'coolant.msh'))
        report=dict(parent,status='joint_local_maximin_volume_screen_only',source_sha256=sha(Path(__file__)),
                    parent_receipt_sha256=sha(p/'mesh-report.json'),joint_patch=result,
                    node_tags=tags[nodes].tolist(),before_mm=old.tolist(),after_mm=xyz[nodes].tolist(),
                    cells=len(q),minimum_sicn=float(q.min()),below_sicn_01=int(np.count_nonzero(q<.1)),
                    minimum_volume_mm3=float(v.min()),volume_mm3=float(v.sum()),
                    volume_quality_passed=quality_passes(q,v),mesh_sha256=sha(o/'coolant.msh'))
        (o/'mesh-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    finally:gmsh.finalize()
