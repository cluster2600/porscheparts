#!/usr/bin/env python3
"""Re-score cached polynomial inputs for minimum-degree fields, without CAD edits."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys


def basis_value(coefficients,u,v):
    import numpy as np
    n,m=np.array(coefficients.shape)-1
    bu=np.array([math.comb(n,i)*u**i*(1-u)**(n-i) for i in range(n+1)])
    bv=np.array([math.comb(m,j)*v**j*(1-v)**(m-j) for j in range(m+1)])
    return np.einsum('i...,ij,j...->...',bu,coefficients,bv)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','trial-directory','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    import numpy as np
    stage=json.loads((a.trial_directory/'surface-report.json').read_text())
    if sha(a.source_step)!=stage['source_sha256']['step']:raise ValueError('source hash mismatch')
    data=np.load(a.trial_directory/'private-bernstein-coefficients.npz');f=data['fcoeff'];poles=data['source_poles'];normal=data['normal']
    u0,u1,v0,v1=data['uv_bounds'];ut,vt=(data['target_uv']-[u0,v0])/[u1-u0,v1-v0];ft=float(basis_value(f,ut,vt))
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.TopAbs import TopAbs_FACE,TopAbs_IN,TopAbs_ON
    from OCP.TopoDS import TopoDS
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.gp import gp_Pnt2d
    face=TopoDS.Face_s(indexed(read_step(a.source_step)[0],TopAbs_FACE).FindKey(stage['selected_face_private']))
    grids=[]
    for count in (81,161):
        u,v=np.meshgrid(np.linspace(0,1,count),np.linspace(0,1,count),indexing='ij');inside=np.zeros_like(u,dtype=bool)
        for i in range(count):
            for j in range(count):inside[i,j]=BRepClass_FaceClassifier(face,gp_Pnt2d(u0+u[i,j]*(u1-u0),v0+v[i,j]*(v1-v0)),1e-9).State() in (TopAbs_IN,TopAbs_ON)
        u,v=u[inside],v[inside];grids.append((count,u,v,basis_value(f,u,v)))
    _,u,v,F=grids[0];pairs=[(p,q) for p in range(2,13) for q in range(2,13)]
    uf=np.array([(u/ut)**p*((1-u)/(1-ut))**q for p,q in pairs]);vf=np.array([(v/vt)**r*((1-v)/(1-vt))**s for r,s in pairs])
    ranked=[]
    for i,(p,q) in enumerate(pairs):
        maxima=.85*np.max(vf*(uf[i]*(F/ft)**2)[None,:],axis=1)
        for j,(r,s) in enumerate(pairs):
            if maxima[j]<=1.:ranked.append((max(p+q+4,r+s+4),p+q+r+s+8,float(maxima[j]),p,q,r,s))
    ranked.sort();selected=[];checked=0
    cross=poles[1,1]-poles[1,0]-poles[0,1]+poles[0,0]
    for row in ranked:
        p,q,r,s=row[3:];checks=[];checked+=1
        factor=ut**p*(1-ut)**q*vt**r*(1-vt)**s*ft**2;c=.85/factor
        for count,u,v,F in grids:
            eu=u**p*(1-u)**q;ev=v**r*(1-v)**s
            deu=p*u**(p-1)*(1-u)**q-q*u**p*(1-u)**(q-1)
            dev=r*v**(r-1)*(1-v)**s-s*v**r*(1-v)**(s-1)
            D=c*eu*ev*F**2
            du=c*ev*(deu*F**2+2*eu*F*basis_value(2*(f[1:]-f[:-1]),u,v))
            dv=c*eu*(dev*F**2+2*ev*F*basis_value(2*(f[:,1:]-f[:,:-1]),u,v))
            su=poles[1,0]-poles[0,0]+v[:,None]*cross;sv=poles[0,1]-poles[0,0]+u[:,None]*cross
            before=np.cross(su,sv);after=np.cross(su+du[:,None]*normal,sv+dv[:,None]*normal)
            orientation=np.sum(before*after,axis=-1)/np.sum(before*before,axis=-1)
            checks.append({'grid_size':count,'retained_points':u.size,'max_displacement':float(np.max(np.abs(D))),
                           'min_orientation_ratio':float(np.min(orientation)),'max_abs_dD_du':float(np.max(np.abs(du))),
                           'max_abs_dD_dv':float(np.max(np.abs(dv)))})
        if all(check['max_displacement']<=1. and check['min_orientation_ratio']>0 for check in checks):
            selected.append({'exponents':[p,q,r,s],'bidegree':[p+q+4,r+s+4],'normalization_C':c,'factor_at_target':factor,'grid_checks':checks})
        if len(selected)==3:break
    result={'schema':'m64-reference-low-degree-polynomial-selection/v1','source_sha256':sha(a.source_step),
            'surface_report_sha256':sha(a.trial_directory/'surface-report.json'),
            'coefficient_sha256':sha(a.trial_directory/'private-bernstein-coefficients.npz'),
            'rescored_fields':len(pairs)**2,'original_search_retained_only_best_not_full_ranking':True,
            'amplitude_feasible_on_81_grid':len(ranked),'refined_candidates_checked':checked,
            'ranking':'minimum_maximum_degree_then_total_degree_then_81_grid_amplitude',
            'candidates':selected,'sampled_not_global_proof':True,'cad_modified':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report_sha256':sha(a.output),'rescored_fields':len(pairs)**2,'amplitude_feasible':len(ranked),'candidates':selected},indent=2))


if __name__=='__main__':main()
