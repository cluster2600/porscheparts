"""Maximize the minimum SICN in each deficient interior-node star, keeping its exterior fixed."""
import argparse
import json
from pathlib import Path

from mesh_surface import quality_passes,sha
from read_saved import tetra_metrics


def maximize_node(points,tets,node):
    import numpy as np
    from scipy.optimize import minimize
    incident=np.any(tets==node,axis=1);star=tets[incident]
    before=tetra_metrics(points[star])[0]
    neighbours=np.unique(star)
    lower=points[neighbours].min(axis=0);upper=points[neighbours].max(axis=0)
    def qualities(position):
        local=points[star].copy();local[star==node]=position
        return tetra_metrics(local)[0]
    x0=np.r_[points[node],float(before.min())-1e-10]
    result=minimize(lambda x:-x[3],x0,method='SLSQP',
                    bounds=[*zip(lower,upper),(0,1)],
                    constraints=[dict(type='ineq',fun=lambda x:qualities(x[:3])-x[3])],
                    options=dict(ftol=1e-12,maxiter=200))
    after=qualities(result.x[:3])
    accepted=bool(result.success and np.isfinite(result.x).all() and after.min()>=.1 and after.min()>=before.min())
    return (result.x[:3] if accepted else points[node].copy()),dict(
        accepted=accepted,minimum_before=float(before.min()),minimum_after=float(after.min()),
        iterations=int(result.nit),message=str(result.message))


if __name__=='__main__':
    import gmsh
    import numpy as np
    import scipy
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();p=args.parent;o=args.output
    parent=json.loads((p/'mesh-report.json').read_text());audit=json.loads((p/'saved-readback.json').read_text())
    if sha(p/'coolant.msh')!=parent['mesh_sha256'] or parent['mesh_sha256']!=audit['mesh_sha256']:
        raise ValueError('Saved parent changed')
    if o.exists():raise ValueError('Output must be new')
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(p/'coolant.msh'))
        tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order]
        xyz=np.asarray(xyz).reshape(-1,3)[order]*1000
        typ,_,connections=gmsh.model.mesh.getElements(3)
        if list(typ)!=[4]:raise ValueError('Expected linear tetrahedra')
        tets=np.searchsorted(tags,np.asarray(connections[0]).reshape(-1,4))
        boundary=np.unique(gmsh.model.mesh.getElements(2)[2][0]);fixed=np.isin(tags,boundary)
        original_boundary=xyz[fixed].copy()
        bad=tetra_metrics(xyz[tets])[0]<.1
        nodes=np.unique(tets[bad]);nodes=nodes[~fixed[nodes]]
        changes=[]
        for node in nodes:
            position,result=maximize_node(xyz,tets,int(node))
            result.update(node_tag=int(tags[node]),before_mm=xyz[node].tolist(),after_mm=position.tolist())
            if result['accepted']:
                xyz[node]=position;gmsh.model.mesh.setNode(int(tags[node]),position*.001,[])
            changes.append(result)
        if not np.array_equal(original_boundary,xyz[fixed]):raise ValueError('Boundary moved')
        q,v=tetra_metrics(xyz[tets])
        o.mkdir(parents=True)
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.Binary',0)
        gmsh.write(str(o/'coolant.msh'))
        report=dict(parent,status='local_maximin_sicn_volume_screen_only',source_sha256=sha(Path(__file__)),
                    independent_metric_source_sha256=sha(Path(__file__).with_name('read_saved.py')),
                    parent_receipt_sha256=sha(p/'mesh-report.json'),scipy_version=scipy.__version__,
                    changes=changes,cells=len(q),minimum_sicn=float(q.min()),below_sicn_01=int(np.count_nonzero(q<.1)),
                    minimum_volume_mm3=float(v.min()),volume_mm3=float(v.sum()),
                    volume_quality_passed=quality_passes(q,v),mesh_sha256=sha(o/'coolant.msh'))
        (o/'mesh-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    finally:gmsh.finalize()
