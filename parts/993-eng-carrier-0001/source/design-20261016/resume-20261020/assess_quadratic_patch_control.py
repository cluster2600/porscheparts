"""Verify every quadratic-patch node and integration point at fixed tolerances."""
import argparse
from fractions import Fraction as Q
import hashlib
import itertools
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--dat',type=Path,required=True);p.add_argument('--analytic',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);data=json.loads(a.analytic.read_text());nodes=data['nodes'];cells=data['cells'];u={};stress={};current=None
    for raw in a.dat.read_text().splitlines():
        line=raw.strip()
        if line.startswith('displacements ('):current='u';continue
        if line.startswith('stresses ('):current='s';continue
        if line.startswith('forces ('):current=None;continue
        fields=line.split()
        if not fields or not fields[0].isdigit():continue
        if current=='u'and len(fields)==4:
            index=int(fields[0])-1
            if index in u:raise ValueError('Duplicate node result')
            u[index]=list(map(float,fields[1:]))
        if current=='s'and len(fields)==8:
            cell,ip=int(fields[0])-1,int(fields[1])
            if (cell,ip)in stress:raise ValueError('Duplicate integration point')
            stress[cell,ip]=list(map(float,fields[2:]))
    if set(u)!=set(range(len(nodes)))or set(stress)!={(i,j)for i in range(len(cells))for j in range(1,5)}:raise ValueError('Complete quadratic result rosters required')
    E=float(data['E_MPa']);nu=float(data['nu']);A=float(data['amplitude_mm']);mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));low=(5-math.sqrt(5))/20;high=1-3*low
    displacement_error=max(abs(u[i][j]-(A*p[0]*p[0]if j==0 else 0.))for i,p in enumerate(nodes)for j in range(3));stress_error=0.;energy=0.;permutations=[]
    for i,cell in enumerate(cells):
        expected=[]
        for special in range(4):
            x=sum((high if k==special else low)*nodes[cell[k]][0]for k in range(4));strain=2*A*x;expected.append([(lam+2*mu)*strain,lam*strain,lam*strain,0.,0.,0.])
        observed=[stress[i,j]for j in range(1,5)]
        matches=[(max(abs(observed[j][k]-expected[perm[j]][k])for j in range(4)for k in range(6)),perm)for perm in itertools.permutations(range(4))];error,perm=min(matches);permutations.append(list(perm));stress_error=max(stress_error,error)
        for sx,sy,sz,xy,xz,yz in observed:energy+=(sx*sx+sy*sy+sz*sz-2*nu*(sx*sy+sy*sz+sz*sx)+2*(1+nu)*(xy*xy+xz*xz+yz*yz))/(2*E)/24
    analytic_energy=float(Q(data['exact_elastic_energy_Nmm']));energy_error=abs(energy/analytic_energy-1);passed=displacement_error<=1e-11 and stress_error<=1e-6 and energy_error<=1e-4
    report=dict(status='complete_quadratic_patch_control_passed'if passed else'quadratic_patch_control_refused',nodes=len(u),integration_point_rows=len(stress),free_interior_node_indices=data['free_node_indices'],maximum_displacement_error_mm=displacement_error,displacement_limit_mm=1e-11,maximum_stress_error_MPa=stress_error,stress_limit_MPa=1e-6,relative_internal_energy_error=energy_error,energy_relative_limit=1e-4,independent_analytic_energy_Nmm=analytic_energy,complete_stress_energy_Nmm=energy,per_cell_Gauss_row_permutations=permutations,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.dat,a.analytic,Path(__file__)]})
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','maximum_displacement_error_mm','maximum_stress_error_MPa','relative_internal_energy_error']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
