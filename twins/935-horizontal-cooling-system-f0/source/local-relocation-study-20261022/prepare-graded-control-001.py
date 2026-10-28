"""Create an analytic marked unit tetrahedron for native metric/geometry controls."""
import json
import sys
import numpy as np
from run_reconstruction import ROOT, fresh, save, sha

sys.path.insert(0,str(ROOT/'twins/935-horizontal-cooling-system-f0/source/local-relocation-study-20261022'))
from graded_size import nodal_sizes

out=fresh(ROOT/'work/935-local-relocation-20261022/graded-control-prepared-001')
v=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
f=np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]]);tags=np.arange(1,5)
with (out/'boundary.obj').open('x') as stream:np.savetxt(stream,v,fmt='v %.17g %.17g %.17g');np.savetxt(stream,f+1,fmt='f %d %d %d')
with (out/'fluid.smesh').open('x') as stream:
    stream.write('4 3 0 0\n');np.savetxt(stream,np.column_stack([np.arange(4),v]),fmt=['%d','%.17g','%.17g','%.17g']);stream.write('4 1\n');np.savetxt(stream,np.column_stack([np.full(4,3),f,tags]),fmt='%d');stream.write('0\n0\n')
sizes=nodal_sizes(v,f,tags,near=.4,far=.7,growth=.2)
with (out/'fluid.mtr').open('x') as stream:stream.write('4 1\n');np.savetxt(stream,sizes,fmt='%.17g')
assert np.allclose(sizes,[.4,.4,.4,.6],rtol=0,atol=1e-15)
save(out/'receipt.json',{'source_sha256':sha(__file__),'analytic_volume':'1/6','analytic_planes_by_marker':{'1':'x+y+z=1','2':'x=0','3':'y=0','4':'z=0'},'nodal_sizes':sizes.tolist(),'synthetic_control_only':True,'CFD_accepted':False,'manufacturing_authorized':False,'output_sha256':{name:sha(out/name) for name in ['fluid.smesh','boundary.obj','fluid.mtr']}})
print(out)
