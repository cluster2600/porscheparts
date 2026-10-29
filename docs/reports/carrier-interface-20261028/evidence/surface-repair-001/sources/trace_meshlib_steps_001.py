from pathlib import Path
import numpy as np
from meshlib import mrmeshpy as mr,mrmeshnumpy as mn
w=Path('work/carrier-interface-20261028');out=w/'meshlib-stage-diagnostic-001';out.mkdir();z=np.load(w/'seed-p10-r3-h0125-003-networks/positive.npz');m=mn.meshFromFacesVerts(z['triangles'].astype(np.int32),z['vertices'])
def save(name):np.savez_compressed(out/(name+'.npz'),vertices=mn.getNumpyVerts(m).copy().astype(float),triangles=mn.getNumpyFaces(m.topology).copy().astype(np.int64))
save('loaded');s=mr.SelfIntersections.Settings();s.method=mr.SelfIntersections.Settings.Method.CutAndFill;s.maxExpand=2;s.relaxIterations=2;s.touchIsIntersection=True;mr.SelfIntersections.fix(m,s);save('self_fix')
q=mr.FixMeshDegeneraciesParams();q.maxDeviation=.005;q.tinyEdgeLength=.0001;q.criticalTriAspectRatio=100;q.mode=mr.FixMeshDegeneraciesParams.Mode.Remesh;mr.fixMeshDegeneracies(m,q);save('degeneracies')
d=mr.DecimateSettings();d.maxError=.005;d.packMesh=True;d.stabilizer=1e-6;mr.decimateMesh(m,d);save('decimated');mr.SelfIntersections.fix(m,s);save('final')
