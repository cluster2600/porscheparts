"""Compare complete conservative X-slab surface triangle rosters exactly.

A pass retains every boundary triangle intersecting the declared nominal bore,
tool and end-seat X intervals. No CAD-radius fitting or measured fit is inferred.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--surface',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    raw=a.baseline.read_bytes();count=int.from_bytes(raw[80:84],'little')
    if len(raw)!=84+50*count:raise ValueError('Binary STL length differs')
    baseline=np.frombuffer(raw,dtype=np.dtype([('normal','<f4',3),('vertices','<f4',(3,3)),('attribute','<u2')]),offset=84,count=count)['vertices'].astype(np.float64)
    with a.surface.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    surface=v[f]
    def roster(triangles,lo,hi):
        select=(triangles[:,:,0].max(axis=1)>=lo)&(triangles[:,:,0].min(axis=1)<=hi)
        rows=[tuple(sorted(tuple(map(float,p))for p in t))for t in triangles[select]]
        if len(set(rows))!=len(rows):raise ValueError('Duplicate selected triangle')
        return set(rows)
    rows=[]
    for name,lo,hi in [('left_central_bores_and_tools',-62.5,-37.5),('right_central_bores_and_tools',37.5,62.5),('left_end_bore_and_seats',-296,-264),('right_end_bore_and_seats',264,296)]:
        old,new=roster(baseline,lo,hi),roster(surface,lo,hi)
        rows.append(dict(role=name,closed_X_interval_mm=[lo,hi],baseline_triangles=len(old),new_triangles=len(new),missing_original=len(old-new),additional=len(new-old),exact_coordinate_and_triangle_identity=old==new))
    passed=all(row['exact_coordinate_and_triangle_identity']for row in rows)
    report=dict(status='declared_interface_surface_slabs_identical'if passed else'interface_surface_slab_refused',regions=rows,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.baseline,a.surface,Path(__file__)]},scope='Complete all-Y/all-Z triangle rosters intersecting nominal central bore/tool and end bore/seat X slabs; central pad boundaries and other protected predicates are not included',mechanical_mesh_admitted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
