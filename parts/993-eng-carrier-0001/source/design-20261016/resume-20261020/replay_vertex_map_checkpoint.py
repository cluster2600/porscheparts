"""Replay every saved contraction, including a refused partial run, exactly."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--prior-flips',type=Path,required=True);p.add_argument('--rounding',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 a.output.mkdir(parents=True)
 import numpy as np
 def load(name,file):
  spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 geometry=load('_replay_geometry','certified_patch_collapse.py');cleanup=load('_replay_cleanup','exact_triangle_cleanup.py');maps=load('_replay_vertex_map','vertex_map_certificate.py');topology=load('_replay_local_boundary','certified_union_collapse.py')
 proof=json.loads(a.proof.read_text());prior=json.loads(a.prior_flips.read_text());rounding=json.loads(a.rounding.read_text())
 if hashlib.sha256(a.mesh.read_bytes()).hexdigest()!=proof['source_mesh_sha256']or proof['source_mesh_sha256']!=prior['output_sha256']:raise ValueError('Saved proof input identity differs')
 with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
 active=np.ones(nf,dtype=bool);tracker=maps.VertexMap(v)
 for row in proof['steps']:
  ids=np.array(row['affected_source_face_ids']);old=f[ids].copy()
  if not active[ids].all():raise ValueError('Inactive face present in saved contraction star')
  keep,remove=row['retained_vertex'],row['removed_vertex'];new=old.copy();new[new==remove]=keep;retained,certificate=cleanup.cleanup_certificate(new.tolist())
  if certificate!=row['redundant_image_coverage']:raise ValueError('Saved degenerate-image coverage differs')
  if topology.boundary(old)!=topology.boundary(new[retained]):raise ValueError('Local oriented boundary changed')
  bound=tracker.apply(keep,remove)
  if bound!=F(row['composed_vertex_map_L1_bound_mm']):raise ValueError('Composed original-vertex displacement differs')
  f[ids]=new;active[ids[certificate['removed_source_triangle_indices']]]=False
 before=F(rounding['exact_to_rounded_complete_surface_L1_bound_mm'])+F(prior['flip_L1_bound_mm']);total=before+tracker.maximum
 if total>F(.06):raise ValueError('Complete exact-master-to-checkpoint bound exceeds unchanged limit')
 certificate=tracker.certificate();faces=f[active];used=np.unique(faces);lookup=np.full(nv,-1,dtype=np.int64);lookup[used]=np.arange(len(used));points=v[used];faces=lookup[faces]
 target=a.output/'union.mesh64'
 with target.open('w')as stream:stream.write(f'{len(points)} {len(faces)}\n');np.savetxt(stream,points,fmt='%.17g');np.savetxt(stream,faces,fmt='%d')
 q=geometry.ratios(points,faces,np);bad=np.flatnonzero(q<.001)
 report=dict(status='partial_refused_mesh_checkpoint_replayed',vertices=len(points),triangles=len(faces),remaining_needles=len(bad),remaining_needle_triangles=[dict(index=int(i),vertices=faces[i].tolist(),points_mm=points[faces[i]].tolist(),ratio=float(q[i]))for i in bad],vertex_map=certificate,prior_bound_mm=str(before),complete_exact_polyhedral_union_to_output_L1_bound_mm=str(total),complete_bound_mm_float=float(total),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),geometry_admitted=False,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.mesh,a.proof,a.prior_flips,a.rounding,Path(__file__)]})
 (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','vertices','triangles','remaining_needles','complete_bound_mm_float']}))

if __name__=='__main__':main()
