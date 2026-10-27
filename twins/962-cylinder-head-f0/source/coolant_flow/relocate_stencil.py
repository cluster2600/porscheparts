"""Reuse local SLSQP relocation with SICN, Foundation-13 stencil and face-weight constraints."""
import argparse
import json
from pathlib import Path

from mesh_surface import quality_passes,sha
from read_saved import tetra_metrics

PATTERNS=((1,2,3),(0,3,2),(0,1,3),(0,2,1))


def determinants(tetra,internal):
    import numpy as np
    face=tetra[:,PATTERNS,:]
    areas=.5*np.cross(face[:,:,1]-face[:,:,0],face[:,:,2]-face[:,:,0])*internal[:,:,None]
    count=internal.sum(axis=1)
    average=np.divide(np.linalg.norm(areas,axis=2).sum(axis=1),count,
                      out=np.zeros(len(tetra)),where=count>0)
    normal=np.divide(areas,average[:,None,None],out=np.zeros_like(areas),where=average[:,None,None]>0)
    return np.abs(np.linalg.det(np.einsum('nfi,nfj->nij',normal,normal)))


def optimise_node(points,tets,internal,pairs,node):
    import numpy as np
    from scipy.optimize import minimize
    ids=np.flatnonzero(np.any(tets==node,axis=1));star=tets[ids]
    used=np.full(len(tets),-1);used[ids]=np.arange(len(ids))
    adjacent=pairs[np.any(used[pairs]>=0,axis=1)]
    volume=tetra_metrics(points[tets[np.unique(adjacent)]])[1]
    indices=np.unique(adjacent);lookup={int(c):i for i,c in enumerate(indices)}
    base=points[star].copy();slots=star==node
    def metrics(position):
        local=base.copy();local[slots]=position
        q,v=tetra_metrics(local);d=determinants(local,internal[ids])
        vol=volume.copy()
        for j,cell in enumerate(ids):vol[lookup[int(cell)]]=v[j]
        pair_vol=vol[np.array([[lookup[int(c)] for c in row] for row in adjacent],dtype=int)]
        weight=np.min(pair_vol,axis=1)/pair_vol.sum(axis=1)
        return np.r_[q/.1,d/.001,weight/.05]
    neighbours=np.unique(star);initial=metrics(points[node])
    result=minimize(lambda x:-x[3],np.r_[points[node],initial.min()-1e-9],method='SLSQP',
        bounds=[*zip(points[neighbours].min(axis=0),points[neighbours].max(axis=0)),(0,1.01)],
        constraints=[dict(type='ineq',fun=lambda x:metrics(x[:3])-x[3])],
        options=dict(ftol=1e-11,maxiter=200))
    after=metrics(result.x[:3])
    accepted=bool(result.success and np.isfinite(after).all() and after.min()>=1)
    return (result.x[:3] if accepted else points[node].copy()),dict(
        accepted=accepted,minimum_normalised_before=float(initial.min()),
        minimum_normalised_after=float(after.min()),iterations=int(result.nit),message=str(result.message))


def repair(parent,output):
    import gmsh
    import numpy as np
    import scipy
    receipt=json.loads((parent/'mesh-report.json').read_text())
    audit=json.loads((parent/'saved-readback.json').read_text())
    if sha(parent/'coolant.msh')!=receipt['mesh_sha256'] or receipt['mesh_sha256']!=audit['mesh_sha256']:
        raise ValueError('Parent input binding changed')
    if audit['independent_volume_quality_passed'] is not True:raise ValueError('Parent SICN screen required')
    if output.exists():raise ValueError('Output must be new')
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(parent/'coolant.msh'))
        tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order]
        xyz=np.asarray(xyz).reshape(-1,3)[order]*1000
        types,_,conn=gmsh.model.mesh.getElements(3)
        if list(types)!=[4]:raise ValueError('Linear tetrahedra required')
        t=np.searchsorted(tags,np.asarray(conn[0]).reshape(-1,4))
        boundary=np.unique(gmsh.model.mesh.getElements(2)[2][0]);fixed=np.isin(tags,boundary)
        fixed_before=xyz[fixed].copy()
        keys=np.sort(t[:,PATTERNS].reshape(-1,3),axis=1)
        _,inverse,counts=np.unique(keys,axis=0,return_inverse=True,return_counts=True)
        if counts.max()!=2:raise ValueError('Nonmanifold tetrahedral incidence')
        internal=(counts[inverse]==2).reshape(-1,4)
        order=np.argsort(inverse,kind='stable');starts=np.r_[0,np.cumsum(counts)[:-1]]
        first=starts[counts==2];pairs=np.c_[order[first]//4,order[first+1]//4]
        changes=[]
        for sweep in range(2):
            q,v=tetra_metrics(xyz[t]);d=determinants(xyz[t],internal)
            weights=v[pairs].min(axis=1)/v[pairs].sum(axis=1)
            bad=np.flatnonzero((q<.1)|(d<.001))
            bad=np.unique(np.r_[bad,pairs[weights<.05].ravel()])
            if not len(bad):break
            nodes=np.unique(t[bad]);nodes=nodes[~fixed[nodes]]
            if len(nodes)>1000:raise ValueError('Local repair exceeds 1000-node work bound')
            print('SWEEP',sweep,'BAD',len(bad),'FREE_NODES',len(nodes),flush=True)
            for node in nodes:
                position,result=optimise_node(xyz,t,internal,pairs,int(node))
                result.update(node_tag=int(tags[node]),sweep=sweep,before_mm=xyz[node].tolist(),after_mm=position.tolist())
                if result['accepted']:xyz[node]=position
                changes.append(result)
            if not any(c['accepted'] for c in changes if c['sweep']==sweep):break
        if not np.array_equal(fixed_before,xyz[fixed]):raise ValueError('Boundary moved')
        for node in np.flatnonzero(~fixed):gmsh.model.mesh.setNode(int(tags[node]),xyz[node]*.001,[])
        q,v=tetra_metrics(xyz[t]);d=determinants(xyz[t],internal)
        weights=v[pairs].min(axis=1)/v[pairs].sum(axis=1)
        output.mkdir(parents=True);gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.Binary',0)
        gmsh.write(str(output/'coolant.msh'))
        report=dict(status='stencil_relocation_candidate_requires_native_checkMesh',
            source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'mesh-report.json'),
            parent_mesh_sha256=receipt['mesh_sha256'],surface_receipt_sha256=receipt['surface_receipt_sha256'],
            scipy_version=scipy.__version__,gmsh_version=gmsh.__version__,changes=changes,cells=len(t),
            minimum_sicn=float(q.min()),below_sicn_01=int(np.count_nonzero(q<.1)),
            minimum_determinant=float(d.min()),bad_determinants=int(np.count_nonzero(d<.001)),
            minimum_face_weight=float(weights.min()),bad_face_weights=int(np.count_nonzero(weights<.05)),
            minimum_volume_mm3=float(v.min()),volume_mm3=float(v.sum()),
            volume_quality_passed=quality_passes(q,v),mesh_coordinates='m',mesh_sha256=sha(output/'coolant.msh'),
            openfoam_mesh_accepted=False,hydraulic_performance_validated=False,manufacturing_authorized=False)
        (output/'mesh-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print('REMAINING',report['bad_determinants'],report['bad_face_weights'],report['below_sicn_01'],flush=True)
    finally:gmsh.finalize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parent',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();repair(a.parent.resolve(),a.output.resolve())
