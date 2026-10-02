#!/usr/bin/env python3
"""Bounded max-min SICN optimization of interior nodes, with unchanged skin.

Only the retained 47-defect mesh and its verified 32-defect descendant are admitted. No CAD displacement,
boundary motion, connectivity change or quality-threshold relaxation.
"""
import argparse
import json
from pathlib import Path
import signal
import sys
import time

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from trial_meshers_2026 import read_gmsh, native

MESH_SHA='9efeecaf06da65225a1e2fc4c722ad2a8340e1079d9cf96aed252bc97c68ecb7'
INPUTS={MESH_SHA:47,'ccbbdb4dcef0551a366f4a8f7da8239d4b29b7ed9524613def77c1d9b259e751':32}
IDEAL=np.array([[1,.5,.5],[0,np.sqrt(3)/2,np.sqrt(3)/6],[0,0,np.sqrt(2/3)]])


def metric(xyz):
    if xyz.ndim!=3 or xyz.shape[1:]!=(4,3) or not np.isfinite(xyz).all():
        raise ValueError('finite_linear_tetrahedra_required')
    j=np.transpose(xyz[:,1:]-xyz[:,[0]],(0,2,1))@np.linalg.inv(IDEAL)
    a,b,c=j[:,:,0],j[:,:,1],j[:,:,2]
    cof=np.stack([np.cross(b,c),np.cross(c,a),np.cross(a,b)],axis=2)
    det=np.einsum('ij,ij->i',a,cof[:,:,0])
    denominator=np.sqrt((j*j).sum((1,2))*(cof*cof).sum((1,2)))
    q=np.divide(3*det,denominator,out=np.zeros_like(det),where=denominator>0)
    return q,det*np.linalg.det(IDEAL)/6


def admissible(oldq,oldv,q,v):
    return bool(np.isfinite([*q,*v]).all() and (v>0).all()
        and q.min()>=oldq.min()-1e-12 and (q<.1).sum()<=(oldq<.1).sum()
        and v[q<.1].sum()<=oldv[oldq<.1].sum()+1e-12
        and ((q<.1).sum()<(oldq<.1).sum() or q.min()>oldq.min()+1e-9))


def run(args):
    import gmsh
    import scipy
    from scipy.optimize import minimize
    mesh_sha=native.sha256(args.mesh)
    if (args.output.exists() or args.mesh.is_symlink() or mesh_sha not in INPUTS
            or gmsh.__version__!='4.15.2' or scipy.__version__ not in ('1.15.3','1.16.2')):
        raise ValueError('fresh_output_exact_mesh_and_runtime_required')
    args.output.mkdir(mode=0o700);source_sha=native.sha256(__file__);start=time.monotonic()
    report=dict(schema='m64-fixed-skin-sicn/v1',source_sha256=source_sha,input_sha256=mesh_sha,
        runtime=dict(numpy=np.__version__,scipy=scipy.__version__,gmsh=gmsh.__version__,python=sys.version),
        native_helper_sha256=native.sha256(native.__file__),
        status='incomplete',boundary_motion_allowed=False,CAD_modified=False,
        manufacturing_authorized=False,CAE_authorized=False,history=[])
    target=args.output/'report.json'
    gmsh.initialize(['fixed-skin','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0);signal.alarm(600)
    try:
        points,cells,triangles,et=read_gmsh(args.mesh);initial=points.copy()
        nt,_,_=gmsh.model.mesh.getNodes();nt=np.sort(nt)
        quality=np.asarray(gmsh.model.mesh.getElementQualities(et,'minSICN'))
        q,v=metric(points[cells])
        if len(cells)!=1341461 or (quality<.1).sum()!=INPUTS[mesh_sha] or not np.allclose(q,quality,rtol=1e-10,atol=1e-12):
            raise ValueError('bound_mesh_and_independent_metric_match_required')
        skin=np.unique(triangles);free=np.setdiff1d(np.unique(cells[q<.1]),skin)
        if not 0<len(free)<=300:raise ValueError('bounded_free_node_set_required')
        report.update(free_nodes=len(free),before=native.quality_distribution(q.tolist(),(6*v).tolist()))
        stars={int(i):np.flatnonzero((cells==i).any(1)) for i in free}
        scales={i:.5*np.linalg.norm(initial[np.setdiff1d(np.unique(cells[rows]),[i])]-initial[i],axis=1).min()
                for i,rows in stars.items()}
        for iteration in range(6):
            moved=0
            for i,rows in stars.items():
                patch=points[cells[rows]].copy();mask=cells[rows]==i
                oldq,oldv=metric(patch)
                if oldq.min()>=.1:continue
                def evaluate(x):
                    trial=patch.copy();trial[mask]=initial[i]+scales[i]*x[:3]
                    return metric(trial)
                x0=np.r_[(points[i]-initial[i])/scales[i],oldq.min()]
                result=minimize(lambda x:-x[3],x0,method='SLSQP',bounds=[(-1,1)]*3+[(0,.2)],
                    constraints=[dict(type='ineq',fun=lambda x:evaluate(x)[0]-x[3])],
                    options=dict(maxiter=60,ftol=1e-10))
                if not result.success or not np.isfinite(result.x).all():continue
                nq,nv=evaluate(result.x)
                if admissible(oldq,oldv,nq,nv):
                    points[i]=initial[i]+scales[i]*result.x[:3];moved+=1
            q,v=metric(points[cells]);summary=native.quality_distribution(q.tolist(),(6*v).tolist())
            report['history'].append(dict(sweep=iteration+1,moved=moved,quality=summary))
            native.save(target,report)
            print(json.dumps(dict(sweep=iteration+1,moved=moved,bad=int((q<.1).sum()))),flush=True)
            if not moved or (q>=.1).all():break
        for i in free:gmsh.model.mesh.setNode(int(nt[i]),points[i].tolist(),[])
        qg=np.asarray(gmsh.model.mesh.getElementQualities(et,'minSICN'))
        if not np.allclose(q,qg,rtol=1e-10,atol=1e-12):raise ValueError('final_native_metric_disagreement')
        gmsh.option.setNumber('Mesh.Binary',1);gmsh.option.setNumber('Mesh.SaveAll',1)
        out=args.output/'interior-optimized-private.msh';gmsh.write(str(out));out.chmod(0o600)
        rp,rc,rf,ret=read_gmsh(out)
        exact=bool(np.array_equal(rc,cells) and np.array_equal(rf,triangles) and np.array_equal(ret,et)
                   and np.array_equal(rp,points) and np.array_equal(rp[skin],initial[skin]))
        qr=gmsh.model.mesh.getElementQualities(ret,'minSICN');dv=gmsh.model.mesh.getElementQualities(ret,'minDetJac')
        conn=native.connectivity_metrics(dict(enumerate(tuple(map(float,p)) for p in rp)),rc.tolist(),rf.tolist())
        accepted=bool(exact and conn['boundary_matches'] and conn['tetra_connected_components']==1
                      and conn['count_negative']==conn['count_zero']==0)
        report.update(status='completed',after=native.quality_distribution(list(map(float,qr)),list(map(float,dv))),
            exact_roundtrip_and_fixed_skin=exact,connectivity=conn,invariants_passed=accepted,
            mesh_sha256=native.sha256(out),maximum_interior_node_displacement=float(np.linalg.norm(points-initial,axis=1).max()),
            project_quality_passed=bool(accepted and np.min(qr)>=.1))
    except Exception as exc:
        report.update(status='failed',error=type(exc).__name__+': '+str(exc))
    finally:
        signal.alarm(0);gmsh.finalize();report.update(seconds=time.monotonic()-start,
            inputs_unchanged=native.sha256(args.mesh)==mesh_sha and native.sha256(__file__)==source_sha)
        native.save(target,report)
    return 0 if report.get('project_quality_passed') and report['inputs_unchanged'] else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('mesh','output'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
