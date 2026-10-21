"""A real quadratic 3D elasticity patch with one unconstrained interior node."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    vertices=[(0.,0.,0.),(1.,0.,0.),(1.,1.,0.),(0.,1.,0.),(0.,0.,1.),(1.,0.,1.),(1.,1.,1.),(0.,1.,1.)]
    tets=[(0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6)]
    edges=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)];midpoints={};quadratic=[]
    for tet in tets:
        cell=list(tet)
        for i,j in edges:
            key=tuple(sorted((tet[i],tet[j])))
            if key not in midpoints:
                midpoints[key]=len(vertices);vertices.append(tuple((vertices[key[0]][k]+vertices[key[1]][k])/2 for k in range(3)))
            cell.append(midpoints[key])
        quadratic.append(cell)
    E=Q(107000);nu=Q(31,100);amplitude=Q(1,1000000);mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));body=2*amplitude*(lam+2*mu)
    fixed=[i for i,p in enumerate(vertices)if any(x in (0.,1.)for x in p)];free=[i for i in range(len(vertices))if i not in fixed]
    if len(vertices)!=27 or len(free)!=1 or vertices[free[0]]!=(.5,.5,.5):raise ValueError('A free interior quadratic node is required')
    expected_u=[[float(amplitude)*p[0]*p[0],0.,0.]for p in vertices]
    low=(5-math.sqrt(5))/20;high=1-3*low;gauss=[]
    for tet in tets:
        rows=[]
        for special in range(4):
            bary=[high if i==special else low for i in range(4)];x=sum(bary[i]*vertices[tet[i]][0]for i in range(4));strain=2*float(amplitude)*x
            rows.append([float(lam+2*mu)*strain,float(lam)*strain,float(lam)*strain,0.,0.,0.])
        gauss.append(rows)
    lines=['*NODE,NSET=ALLN']+[str(i+1)+','+','.join(format(x,'.17g')for x in p)for i,p in enumerate(vertices)]
    lines+=['*ELEMENT,TYPE=C3D10,ELSET=BODY']+[str(i+1)+','+','.join(str(j+1)for j in c)for i,c in enumerate(quadratic)]
    lines+=['*MATERIAL,NAME=CONTROL','*ELASTIC',f'{float(E)},{float(nu)}','*DENSITY','1.','*SOLID SECTION,ELSET=BODY,MATERIAL=CONTROL','*NSET,NSET=FIXED']
    lines += [','.join(str(i+1)for i in fixed[j:j+16])for j in range(0,len(fixed),16)]
    lines+=['*STEP','*STATIC,SOLVER=SPOOLES','*BOUNDARY']
    for i in fixed:
        for axis,value in enumerate(expected_u[i],1):lines.append(f'{i+1},{axis},{axis},{value:.14g}')
    load=['*DLOAD',f'BODY,GRAV,{float(body):.14g},-1.,0.,0.']
    output=['*NODE PRINT,NSET=ALLN','U','*NODE PRINT,NSET=FIXED','RF','*EL PRINT,ELSET=BODY','S','*END STEP']
    (a.output/'control.inp').write_text('\n'.join(lines+load+output)+'\n');(a.output/'missing-body-counterexample.inp').write_text('\n'.join(lines+output)+'\n')
    report=dict(status='quadratic_patch_control_prepared',domain='unit cube, six straight C3D10 tetrahedra',exact_displacement='u=(A*x^2,0,0), A=1e-6',nodes=vertices,cells=quadratic,free_node_indices=free,fixed_node_indices=fixed,E_MPa=float(E),nu=float(nu),amplitude_mm=float(amplitude),density_for_analytic_body_force=1.,exact_negative_X_body_force_N_per_mm3=str(body),expected_displacements=expected_u,expected_stresses_per_cell_unordered=gauss,exact_elastic_energy_Nmm=str(Q(2,3)*(lam+2*mu)*amplitude**2),displacement_tolerance_mm=1e-11,stress_tolerance_MPa=1e-6,energy_relative_tolerance=1e-4,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.output.glob('*.inp')})
    (a.output/'analytic.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(nodes=len(vertices),cells=len(tets),free_nodes=free)))

if __name__=='__main__':main()
