"""Exact whole-simplex C3D10 Jacobian positivity by an affine perturbation bound.

For each cell, A is its corner affine Jacobian and d_e each midside deviation
from the exact edge midpoint. The quadratic perturbation has infinity norm
<=16 sum_e ||d_e||inf everywhere in the reference simplex. If ||A^-1||inf times
that bound is <1, the whole homotopy remains nonsingular with positive sign.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

EDGES=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)]


def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def integer_cell_bound(points):
    p=points[:4];u=tuple(p[1][j]-p[0][j]for j in range(3));v=tuple(p[2][j]-p[0][j]for j in range(3));w=tuple(p[3][j]-p[0][j]for j in range(3));vw=cross(v,w);det=sum(u[j]*vw[j]for j in range(3))
    if det<=0:return None
    cofactor=max(sum(map(abs,row))for row in [vw,cross(w,u),cross(u,v)]);maximum_delta_L1=0;sum_max_delta=0
    for k,(i,j)in enumerate(EDGES):
        difference=tuple(2*points[4+k][axis]-p[i][axis]-p[j][axis]for axis in range(3));sum_max_delta+=max(map(abs,difference));maximum_delta_L1=max(maximum_delta_L1,sum(map(abs,difference)))
    return(8*cofactor*sum_max_delta,det,maximum_delta_L1)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(180,190));signal.alarm(210);start=time.monotonic()
    import numpy as np
    record=json.loads((a.geometry/'assessment.json').read_text());mesh=a.geometry/'quadratic.npz'
    if hashlib.sha256(mesh.read_bytes()).hexdigest()!=record['output_sha256']['quadratic.npz']:raise ValueError('Prepared input identity differs')
    with np.load(mesh,allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy()
    ratios=[];scale=1
    for point in v:
        row=[float(x).as_integer_ratio()for x in point];ratios.append(row)
        for _,den in row:scale=max(scale,den)
    integers=[tuple(num*(scale//den)for num,den in row)for row in ratios];del ratios
    maximum_num=0;maximum_den=1;max_delta=0;worst=None;refused=[];minimum_det=None
    for index,cell in enumerate(cells):
        result=integer_cell_bound([integers[int(i)]for i in cell])
        if result is None:refused.append(index);continue
        numerator,denominator,delta=result;minimum_det=denominator if minimum_det is None else min(minimum_det,denominator);max_delta=max(max_delta,delta)
        if numerator>=denominator:refused.append(index)
        if numerator*maximum_den>maximum_num*denominator:maximum_num,maximum_den,worst=numerator,denominator,index
    eta=Q(maximum_num,maximum_den);curvature_bound=Q(3*max_delta,4*scale);corner_bound=Q(record['complete_corner_transport_L1_bound_mm']);combined=Q(float(record['whole_surface_reference_distance_upper_mm']))+corner_bound+curvature_bound;passed=not refused and combined<=Q(3,50)
    report=dict(status='complete_C3D10_mapping_and_geometry_budget_passed'if passed else'quadratic_mapping_screen_refused',elements=len(cells),nodes=len(v),common_integer_coordinate_scale=str(scale),exact_maximum_affine_relative_Jacobian_perturbation=str(eta),maximum_affine_relative_Jacobian_perturbation=float(eta),worst_cell_zero_based=worst,minimum_corner_integer_determinant=str(minimum_det),whole_simplex_and_whole_homotopy_positive=not refused,refused_cell_indices=refused,exact_complete_curved_to_corner_surface_L1_bound_mm=str(curvature_bound),complete_curved_to_corner_surface_L1_bound_mm=float(curvature_bound),exact_composed_reference_to_quadratic_surface_bound_mm=str(combined),composed_reference_to_quadratic_surface_bound_mm=float(combined),fixed_geometry_distance_limit_mm=.06,geometry_adopted=False,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [mesh,a.geometry/'assessment.json',Path(__file__)]},elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps({k:report[k]for k in ['status','elements','maximum_affine_relative_Jacobian_perturbation','composed_reference_to_quadratic_surface_bound_mm','elapsed_seconds']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
