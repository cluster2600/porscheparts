"""Exact signed surface volume and nominal dense mass on every stored facet."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import signal
import time


def determinant(a,b,c):
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--surface-audit',type=Path,required=True);p.add_argument('--density',type=int,default=4420);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(120,130));signal.alarm(150);start=time.monotonic()
    if not 0<a.density<30000:raise ValueError('Positive stated density in kg/m3 required')
    digest=hashlib.sha256(a.mesh.read_bytes()).hexdigest();audit=json.loads(a.surface_audit.read_text())
    if audit['status']!='complete_surface_screen_passed'or audit['source_mesh_sha256']!=digest:raise ValueError('Matching complete closed-surface audit required')
    # Independently known oriented unit tetrahedron and reversed orientation.
    control=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)];faces=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
    assert sum(determinant(*(control[i]for i in f))for f in faces)==1
    assert sum(determinant(*(control[i]for i in reversed(f)))for f in faces)==-1
    with a.mesh.open()as stream:
        nv,nf=map(int,stream.readline().split());ratios=[];scale=1
        for _ in range(nv):
            point=[float(x).as_integer_ratio()for x in stream.readline().split()]
            if len(point)!=3:raise ValueError('Three finite coordinates required')
            for _,den in point:
                if den&(den-1):raise ValueError('Dyadic coordinate required')
                scale=max(scale,den)
            ratios.append(point)
        vertices=[tuple(num*(scale//den)for num,den in point)for point in ratios];del ratios
        total=0;count=0
        for line in stream:
            ids=list(map(int,line.split()))
            if len(ids)!=3 or min(ids)<0 or max(ids)>=nv:raise ValueError('Triangle roster differs')
            total+=determinant(*(vertices[i]for i in ids));count+=1
        if count!=nf or total<=0:raise ValueError('Full outward positive closed-surface volume required')
    volume=Q(total,6*scale**3);mass=volume*Q(a.density,10**9);passed=mass<=Q(13,10)
    report=dict(status='exact_nominal_dense_mass_within_1_30kg'if passed else'exact_nominal_dense_mass_exceeds_1_30kg',source_mesh_sha256=digest,surface_audit_sha256=hashlib.sha256(a.surface_audit.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),vertices=nv,triangles=nf,common_integer_coordinate_scale=str(scale),signed_determinant_sum_integer=str(total),exact_volume_mm3=str(volume),volume_mm3=float(volume),density_kg_m3=a.density,exact_nominal_dense_mass_kg=str(mass),nominal_dense_mass_kg=float(mass),exact_mass_ceiling_kg='13/10',exact_remaining_mass_kg=str(Q(13,10)-mass),remaining_mass_g=float((Q(13,10)-mass)*1000),coordinate_semantics='Exact dyadic values of every parsed binary64 vertex; every oriented surface triangle included',supports_and_machining_stock_included=False,geometry_adopted=False,elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps({k:report[k]for k in ['status','triangles','nominal_dense_mass_kg','remaining_mass_g','elapsed_seconds']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
