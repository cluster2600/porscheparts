"""Independently check the adaptive mesher against analytic unit-tetrahedron geometry."""
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from import_conforming_volume import table,exact_orientation
from prepare_conforming_surface import sha

p=Path('/home/lolman/935-local-relocation-20261022/graded-control-native-001')
v=table(p/'fluid.1.node','node');cells=table(p/'fluid.1.ele','ele');proof=exact_orientation(v,cells)
assert proof['negative']==proof['zero']==0 and abs(Fraction(proof['signed_volume_exact'])-Fraction(1,6))<Fraction(1,10**12)
assert np.all(v>=-1e-12) and np.all(v.sum(axis=1)<=1+1e-12)
with (p/'fluid.1.face').open() as stream:head=list(map(int,stream.readline().split()));rows=np.loadtxt(stream,dtype=np.int64,ndmin=2)
assert rows.shape==(head[0],5);boundary=rows[rows[:,4]>0];assert set(boundary[:,4])=={1,2,3,4}
error=0.
for i in range(1,5):
    points=v[boundary[boundary[:,4]==i,1:4]]
    distance=np.abs(points.sum(axis=2)-1) if i==1 else np.abs(points[:,:,i-2])
    error=max(error,float(distance.max()))
assert error<1e-12
execution=json.loads((p/'execution.json').read_text());assert execution['exit']==0 and execution['metric_opened_by_native_mesher'] and execution['inputs_unchanged']
record={'status':'native_adaptive_mesher_analytic_unit_tetrahedron_control_passed','source_sha256':sha(__file__),'execution_sha256':sha(p/'execution.json'),'vertices':len(v),'tetrahedra':len(cells),'boundary_triangles':len(boundary),'maximum_analytic_plane_error':error,'exact_serialized_volume':proof['signed_volume_exact'],'absolute_unit_volume_error':float(abs(Fraction(proof['signed_volume_exact'])-Fraction(1,6))),'all_points_inside_analytic_domain':True,'all_boundary_markers_retained':True,'all_exact_cell_determinants_positive':True,'metric_consumed':True,'CFD_quality_admitted':False,'CFD_accepted':False,'manufacturing_authorized':False}
with (p/'analytic-audit.json').open('x') as stream:json.dump(record,stream,indent=2)
print(json.dumps(record),flush=True)
