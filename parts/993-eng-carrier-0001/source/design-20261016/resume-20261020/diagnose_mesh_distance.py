"""Deterministic full vertex/centroid distance diagnostics; no global admission."""
import hashlib
import json
from pathlib import Path


def main():
 import numpy as np
 import igl
 out=Path('/output')
 def read(path):
  with path.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
  if v.shape!=(nv,3)or f.shape!=(nf,3):raise ValueError('Complete mesh counts differ')
  return v,f
 a=Path('/input/reference.mesh64');b=Path('/input/retained.mesh64');va,fa=read(a);vb,fb=read(b);report=dict(status='incomplete',global_admission=False,scope='All vertices and all triangle centroids, both directions; diagnostic lower witnesses only, not a continuous upper bound',input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a,b,Path(__file__)]},directions=[])
 for label,v,f,target,tf in [('reference_to_retained',va,fa,vb,fb),('retained_to_reference',vb,fb,va,fa)]:
  points=np.vstack([v,v[f].mean(axis=1)]);squared,face,closest=igl.point_mesh_squared_distance(points,target,tf);distance=np.sqrt(np.maximum(0,squared));worst=np.argsort(distance)[-32:][::-1];rows=[]
  for i in worst:
   rows.append(dict(point_kind='vertex'if i<len(v)else'triangle_centroid',source_index=int(i if i<len(v)else i-len(v)),point_mm=points[i].tolist(),distance_mm=float(distance[i]),target_face_index=int(face[i]),closest_target_point_mm=closest[i].tolist()))
  report['directions'].append(dict(direction=label,source_vertices=len(v),source_faces=len(f),probes=len(points),maximum_diagnostic_distance_mm=float(distance.max()),p99_mm=float(np.quantile(distance,.99)),probes_over_006_mm=int(np.count_nonzero(distance>.06)),worst=rows))
  np.savez_compressed(out/f'{label}.npz',vertex_distance_mm=distance[:len(v)],face_centroid_distance_mm=distance[len(v):],nearest_target_face=face)
  (out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
 report['status']='complete_deterministic_distance_diagnostics';(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],directions=[{k:x[k]for k in ['direction','maximum_diagnostic_distance_mm','probes_over_006_mm']}for x in report['directions']])))

if __name__=='__main__':main()
