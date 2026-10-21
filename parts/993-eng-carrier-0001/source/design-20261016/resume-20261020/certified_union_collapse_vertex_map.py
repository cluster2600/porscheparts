"""Local contractions with an exact composed vertex-map bound on the full surface.

The certificate is relative to the exact POLYHEDRAL union, not a new bound on
an uncomputed native CAD union. All source triangle IDs and changes are saved.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def boundary(f):
    edges={}
    for t in f:
        for j in range(3):
            a,b=int(t[j]),int(t[(j+1)%3]);key=tuple(sorted((a,b)));n,s=edges.get(key,(0,0));edges[key]=(n+1,s+(1 if a<b else -1))
    if any(n>2 or(n==2 and s!=0)for n,s in edges.values()):raise ValueError('Invalid local edge topology')
    return {key:s for key,(n,s)in edges.items()if s}


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--rounding-audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prior-flips',type=Path,required=True);p.add_argument('--original-rounding-audit',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic()
    import numpy as np
    def load(name,file):
        spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    base=load('_union_collapse_geometry','certified_patch_collapse.py');cleanup=load('_union_exact_cleanup','exact_triangle_cleanup.py');mapping_module=load('_union_vertex_map','vertex_map_certificate.py')
    audit=json.loads(a.rounding_audit.read_text());raw=a.mesh.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=audit['source_mesh_sha256']:raise ValueError('Audited mesh identity differs')
    if audit['failures']!=['needle_triangles']:raise ValueError('This trial requires an otherwise fully screened source')
    with a.mesh.open()as stream:
        nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    if f.shape!=(nf,3):raise ValueError('Face count differs')
    tracker=mapping_module.VertexMap(v);active=np.ones(nf,dtype=bool);spent=F(0);prior_flips=json.loads(a.prior_flips.read_text());original_rounding=json.loads(a.original_rounding_audit.read_text())
    if prior_flips['output_sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('Prior flip identity differs')
    prior=F(original_rounding['exact_to_rounded_complete_surface_L1_bound_mm'])+F(prior_flips['flip_L1_bound_mm']);steps=[]
    report=dict(status='incomplete',source_mesh_sha256=hashlib.sha256(raw).hexdigest(),steps=steps,maximum_allowed_L1_bound_mm=.06,scope='Bound relative to exact polyhedral CGAL union, not to an uncomputed native CAD union')
    try:
        while True:
            live=np.flatnonzero(active);quality=base.ratios(v,f[live],np);bad=live[quality<.001]
            if not len(bad):break
            edges={tuple(sorted((int(t[j]),int(t[(j+1)%3]))))for t in f[bad]for j in range(3)};needed={x for e in edges for x in e};adj={x:set()for x in needed}
            hit=np.flatnonzero(active&np.any(np.isin(f,list(needed)),axis=1))
            for face_id in hit:
                for vertex in f[face_id]:
                    if int(vertex)in adj:adj[int(vertex)].add(int(face_id))
            choice=None
            for x,y in edges:
                cost=sum(abs(F(float(q))-F(float(r)))for q,r in zip(v[x],v[y]))
                if prior+cost>F(.06):continue
                ids=np.array(sorted(adj[x]|adj[y]),dtype=np.int64);old=f[ids];old_boundary=boundary(old);before=int((base.ratios(v,old,np)<.001).sum())
                for keep,remove in [(x,y),(y,x)]:
                    proposed=tracker.proposal(keep,remove)
                    if prior+proposed>F(.06):continue
                    changed=old.copy();changed[changed==remove]=keep
                    try:
                        retained,coverage=cleanup.cleanup_certificate(changed.tolist())
                        if retained is None:continue
                        new=changed[retained]
                        if boundary(new)!=old_boundary:continue
                    except ValueError:continue
                    if len(np.unique(np.sort(new,axis=1),axis=0))!=len(new):continue
                    q=base.ratios(v,new,np)
                    if not np.isfinite(q).all()or np.any(q==0):continue
                    after=int((q<.001).sum());count=len(bad)-before+after
                    if count>=len(bad):continue
                    score=(proposed,cost,count,keep,remove)
                    if choice is None or score<choice[0]:choice=(score,ids,changed,coverage)
            if choice is None:raise ValueError(f'No admissible local contraction for {len(bad)} needles')
            (_,cost,count,keep,remove),ids,changed,coverage=choice;f[ids]=changed;active[ids[coverage['removed_source_triangle_indices']]]=False;spent=tracker.apply(keep,remove)
            steps.append(dict(retained_vertex=keep,removed_vertex=remove,retained_point_mm=v[keep].tolist(),removed_point_mm=v[remove].tolist(),L1_displacement_mm=str(cost),composed_vertex_map_L1_bound_mm=str(spent),needles_before=len(bad),needles_after=count,affected_source_face_ids=ids.tolist(),redundant_image_coverage=coverage,local_oriented_boundary_unchanged=True))
            (a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        report['composed_vertex_map_certificate']=tracker.certificate()
        f=f[active];used=np.unique(f);mapping=np.full(nv,-1,dtype=int);mapping[used]=np.arange(len(used));v=v[used];f=mapping[f]
        target=a.output/'union.mesh64'
        with target.open('w')as stream:stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')
        report.update(status='local_contractions_and_surface_bound_passed',exact_union_to_rounded_bound_mm=str(prior),contraction_L1_bound_mm=str(spent),complete_exact_polyhedral_union_to_output_L1_bound_mm=str(prior+spent),complete_bound_mm_float=float(prior+spent),vertices=len(v),triangles=len(f),minimum_triangle_ratio=float(base.ratios(v,f,np).min()),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),independent_full_surface_audit_pending=True)
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error));raise
    finally:report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','vertices','triangles','complete_bound_mm_float','minimum_triangle_ratio']}))

if __name__=='__main__':main()
