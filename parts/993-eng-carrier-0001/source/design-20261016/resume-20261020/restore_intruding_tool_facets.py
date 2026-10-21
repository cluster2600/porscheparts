"""Intentionally cap only certified intruding facets to the nominal Z=4 plane.

This is a clearance design edit, not a tessellation-error allowance. XY and the
complete face roster are retained. Every source facet touching an open tool
column is capped in full; all other surface points move only downwards in Z,
so the edit cannot introduce an intrusion into a vertical open tool column.
Fresh whole-surface and exact-column checks are still required.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import signal
import time


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--certificate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(120,130));signal.alarm(150);start=time.monotonic()
    import numpy as np
    proof=json.loads(a.certificate.read_text());digest=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    if proof['status']!='open_tool_column_exclusion_refused'or proof['source_mesh_sha256']!=digest or proof['open_Z_interval_mm']!=[4,40]or proof['radius_mm']!=12.5:raise ValueError('Matching complete nominal-column refusal required')
    with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    if v.shape!=(nv,3)or f.shape!=(nf,3)or v[:,2].max()>=40:raise ValueError('Whole source or exterior witness differs')
    failed=sorted({i for col in proof['columns']for i in col['failed_facets']})
    ids=np.unique(f[failed]);ids=ids[v[ids,2]>4];new=v.copy();new[ids,2]=4.
    if not np.all(new[:,2]<=v[:,2]):raise ValueError('The clearance edit must be vertically monotone')
    if not np.all(new[f[failed],2]<=4):raise ValueError('Every intruding facet must be wholly capped')
    if len(np.unique(new,axis=0))!=nv:raise ValueError('Coincident vertices require a coverage-preserving weld; none silently merged')
    triangles=new[f];normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    if np.any(np.all(normals==0,axis=1)):raise ValueError('Collapsed triangle requires explicit image coverage; none silently removed')
    rows=[dict(vertex=int(i),before_Z_mm=float(v[i,2]),after_Z_mm=4.,exact_L1_mm=str(Q(float(v[i,2]))-4))for i in ids]
    maximum=max((Q(row['exact_L1_mm'])for row in rows),default=Q(0));target=a.output/'surface.mesh64'
    with target.open('w')as stream:stream.write(f'{nv} {nf}\n');np.savetxt(stream,new,fmt='%.17g');np.savetxt(stream,f,fmt='%d')
    (a.output/'changed-vertices.json').write_text(json.dumps(rows,indent=2)+'\n')
    report=dict(status='certified_intruding_facets_capped_fresh_audits_pending',source_mesh_sha256=digest,source_certificate_sha256=hashlib.sha256(a.certificate.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),vertices=nv,triangles=nf,source_intruding_facets=len(failed),changed_vertices=len(ids),maximum_exact_design_edit_L1_mm=str(maximum),maximum_design_edit_L1_mm=float(maximum),intentional_clearance_design_edit=True,tessellation_error_budget_changed=False,XY_unchanged=True,face_roster_unchanged=True,geometry_adopted=False,elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps(report))

if __name__=='__main__':main()
