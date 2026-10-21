"""Actual P1/P2 constant-traction cube control with an analytic uniaxial solution."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--quadratic-control',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--dat',type=Path);p.add_argument('--order',choices=['P1','P2']);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    source=json.loads(a.quadratic_control.read_text());allv=np.array(source['nodes']);allc=np.array(source['cells']);E=source['E_MPa'];nu=source['nu']
    if a.dat:
        n=8 if a.order=='P1'else 27;ips=1 if a.order=='P1'else 4;u={};s={};current=None
        for raw in a.dat.read_text().splitlines():
            line=raw.strip()
            if line.startswith('displacements ('):current='u';continue
            if line.startswith('stresses ('):current='s';continue
            if line.startswith('forces ('):current=None;continue
            f=line.split()
            if not f or not f[0].isdigit():continue
            target=u if current=='u'and len(f)==4 else s if current=='s'and len(f)==8 else None
            if target is None:continue
            key=int(f[0])-1 if target is u else (int(f[0])-1,int(f[1]))
            if key in target:raise ValueError('Duplicate result row')
            target[key]=list(map(float,f[1:]if target is u else f[2:]))
        if set(u)!=set(range(n))or set(s)!={(i,j)for i in range(6)for j in range(1,ips+1)}:raise ValueError('Incomplete control result rosters')
        expected=allv[:n]*np.array([1,-nu,-nu])/E;ue=float(np.max(abs(np.array([u[i]for i in range(n)])-expected)));se=float(np.max(abs(np.array(list(s.values()))-np.array([1,0,0,0,0,0]))));passed=ue<=1e-11 and se<=1e-6
        report=dict(status='consistent_traction_patch_passed'if passed else'consistent_traction_patch_refused',order=a.order,maximum_displacement_error_mm=ue,maximum_stress_error_MPa=se,displacement_limit_mm=1e-11,stress_limit_MPa=1e-6,complete_node_rows=n,complete_stress_rows=len(s),source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.dat,a.quadratic_control,Path(__file__)]})
        (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if passed else 2
    for order in ['P1','P2']:
        v=allv[:8]if order=='P1'else allv;c=allc[:,:4]if order=='P1'else allc;loads=np.zeros_like(v)
        # The two x=1 parent faces are (1,2,6) and (1,6,5).
        for corners in [(1,2,6),(1,6,5)]:
            area=np.linalg.norm(np.cross(v[corners[1]]-v[corners[0]],v[corners[2]]-v[corners[0]]))/2
            slots=list(corners)if order=='P1'else [next(i for i,pnt in enumerate(v)if np.array_equal(pnt,(v[j]+v[k])/2))for j,k in [(corners[0],corners[1]),(corners[1],corners[2]),(corners[2],corners[0])]]
            for index in slots:loads[index,0]+=area/3
        lines=['*NODE,NSET=ALLN']+[str(i+1)+','+','.join(format(x,'.17g')for x in point)for i,point in enumerate(v)]
        lines += ['*ELEMENT,TYPE='+('C3D4'if order=='P1'else'C3D10')+',ELSET=BODY']+[str(i+1)+','+','.join(str(j+1)for j in cell)for i,cell in enumerate(c)]
        lines += ['*MATERIAL,NAME=CONTROL','*ELASTIC',f'{E},{nu}','*SOLID SECTION,ELSET=BODY,MATERIAL=CONTROL','*STEP','*STATIC,SOLVER=SPOOLES','*BOUNDARY']
        for i,point in enumerate(v):
            for axis,x in enumerate(point,1):
                if x==0:lines.append(f'{i+1},{axis},{axis},0.')
        lines += ['*CLOAD']+[f'{i+1},1,{force:.17g}'for i,force in enumerate(loads[:,0])if force]
        lines += ['*NODE PRINT,NSET=ALLN','U','*EL PRINT,ELSET=BODY','S','*END STEP'];(a.output/(order+'.inp')).write_text('\n'.join(lines)+'\n')
    print('Prepared P1/P2 uniaxial traction controls')
    return 0

if __name__=='__main__':raise SystemExit(main())
