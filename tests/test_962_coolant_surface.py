import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source/coolant_flow/prepare_surface.py"
spec = importlib.util.spec_from_file_location("water_surface", SOURCE)
surface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(surface)
spec = importlib.util.spec_from_file_location("water_volume", SOURCE.with_name("mesh_surface.py"))
volume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(volume)


class CoolantSurfaceTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("scipy"), "SciPy is required for the joint-star fixture")
    def test_joint_patch_handles_two_free_nodes_and_keeps_their_exterior(self):
        code = """
import numpy as np
from relocate_patch import maximize_patch
from read_saved import tetra_metrics
p=np.array([[0,0,0],[1,0,0],[.5,np.sqrt(3)/2,0],[.5,np.sqrt(3)/6,np.sqrt(2/3)],[.01,.01,.01]])
t=np.array([[4,1,2,3],[4,0,3,2],[4,0,1,3],[4,0,2,1]])
p=np.vstack((p,p+[3,0,0]));t=np.vstack((t,t+5));nodes=np.array([4,9])
fixed=np.delete(p,nodes,axis=0).copy();total=tetra_metrics(p[t])[1].sum()
new,r=maximize_patch(p,t,nodes);assert r['accepted']
p[nodes]=new;q,v=tetra_metrics(p[t])
assert q.min()>=.1 and v.min()>0 and np.allclose(v.sum(),total,rtol=0,atol=1e-12)
assert np.array_equal(np.delete(p,nodes,axis=0),fixed)
"""
        subprocess.run([sys.executable,"-B","-c",code],cwd=SOURCE.parent,check=True)

    @unittest.skipUnless(importlib.util.find_spec("scipy"), "SciPy is required for the node-star fixture")
    def test_maximin_moves_only_an_interior_node_and_preserves_volume(self):
        code = """
import numpy as np
from relocate_nodes import maximize_node
from read_saved import tetra_metrics
p=np.array([[0,0,0],[1,0,0],[.5,np.sqrt(3)/2,0],[.5,np.sqrt(3)/6,np.sqrt(2/3)],[.01,.01,.01]])
t=np.array([[4,1,2,3],[4,0,3,2],[4,0,1,3],[4,0,2,1]])
q,v=tetra_metrics(p[t]);assert q.min()<.1 and v.min()>0
fixed=p[:4].copy();total=v.sum();new,result=maximize_node(p,t,4)
assert result['accepted']
p[4]=new;q,v=tetra_metrics(p[t])
assert q.min()>=.1 and v.min()>0 and np.allclose(v.sum(),total,rtol=0,atol=1e-12)
assert np.array_equal(p[:4],fixed)
"""
        subprocess.run([sys.executable,"-B","-c",code],cwd=SOURCE.parent,check=True)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is required for the tetrahedron fixture")
    def test_independent_sicn_and_signed_volume_on_exact_reference_cases(self):
        code = """
import numpy as np
from read_saved import tetra_metrics
p=np.array([[0,0,0],[1,0,0],[.5,np.sqrt(3)/2,0],[.5,np.sqrt(3)/6,np.sqrt(2/3)]])
q,v=tetra_metrics(p[None]);assert np.allclose(q,1) and np.allclose(v,np.sqrt(2)/12)
q2,v2=tetra_metrics((p*2)[None]);assert np.allclose(q2,q) and np.allclose(v2,8*v)
q3,v3=tetra_metrics(p[[1,0,2,3]][None]);assert np.allclose(q3,-1) and np.allclose(v3,-v)
flat=p.copy();flat[:,2]=0
q4,v4=tetra_metrics(flat[None]);assert q4[0]==0 and v4[0]==0
"""
        subprocess.run([sys.executable,"-B","-c",code],cwd=SOURCE.parent,check=True)

    @unittest.skipUnless(importlib.util.find_spec("trimesh"), "Trimesh is required for the collapse fixture")
    def test_endpoint_collapse_recovers_a_closed_sphere_after_an_edge_split(self):
        code = """
import numpy as np,trimesh
from repair_last_edge import collapse
from repair_slivers import triangle_q,Q_MIN
m=trimesh.creation.icosphere(subdivisions=0)
u,v=m.faces[0][:2];p=np.vstack((m.vertices,m.vertices[u]*.999+m.vertices[v]*.001));w=len(p)-1
f=[]
for face in m.faces:
    if u in face and v in face:
        for i in range(3):
            a,b,c=face[[i,(i+1)%3,(i+2)%3]]
            if {a,b}=={u,v}:f.extend([[a,w,c],[w,b,c]])
    else:f.append(face.tolist())
f=np.array(f);assert triangle_q(p,f).min()<Q_MIN
r,change=collapse(p,f)
assert change is not None and len(r)==len(m.faces) and triangle_q(p,r).min()>=Q_MIN
n=trimesh.Trimesh(vertices=p,faces=r,process=False)
assert n.is_watertight and n.is_winding_consistent and n.euler_number==m.euler_number
"""
        subprocess.run([sys.executable,"-B","-c",code],cwd=SOURCE.parent,check=True)

    @unittest.skipUnless(importlib.util.find_spec("trimesh"), "Trimesh is required for the local-flip fixture")
    def test_local_flip_repairs_a_flat_sliver_without_moving_points(self):
        code = """
import numpy as np
from repair_slivers import repair_faces, triangle_q, Q_MIN
p=np.array([[0,0,0],[1,0,0],[.5,.001,0],[.5,-1,0]],dtype=float)
t=np.array([[0,1,2],[1,0,3]])
assert triangle_q(p,t).min() < Q_MIN
f,changes=repair_faces(p,t)
assert len(changes)==1 and triangle_q(p,f).min() >= Q_MIN
assert np.array_equal(np.unique(f),np.unique(t))
assert not repair_faces(p,f)[1]
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=SOURCE.parent, check=True)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is required for the patch fixture")
    def test_patch_partition_preserves_caps_and_rejects_missing_port(self):
        code = """
import numpy as np
from mesh_discrete import partition
p=np.array([[-76,0,0],[-76,1,0],[-76,0,1],[76,0,0],[76,1,0],[76,0,1]],dtype=float)
t=np.array([[0,1,2],[3,5,4],[0,3,1]])
g=partition(p,t)
assert {k:len(v) for k,v in g.items()} == dict(inlet=1,outlet=1,walls=1)
try: partition(p,t[[0,2]])
except ValueError: pass
else: raise AssertionError('Missing outlet accepted')
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=SOURCE.parent, check=True)

    def test_volume_gate_requires_every_cell_not_only_positive_volume(self):
        self.assertTrue(volume.quality_passes([.1, 1], [1, 2]))
        for q, v in (([], []), ([.099], [1]), ([1], [-1]),
                     ([1], [0]), ([1], [float('nan')]), ([float('nan')], [1]),
                     ([1, 1], [1])):
            with self.subTest(q=q, v=v):
                self.assertFalse(volume.quality_passes(q, v))

    def test_gate_rejects_distance_topology_and_nonfinite_values(self):
        baseline = dict(sampled_deviations_mm=[.01, 0, .02, .03], watertight=True,
                        consistent_winding=True, components=1, euler_preserved=True,
                        relative_volume_change=.001)
        self.assertTrue(surface.admitted(baseline))
        for change in (dict(sampled_deviations_mm=[.063, 0, 0, 0]),
                       dict(sampled_deviations_mm=[float('nan'), 0, 0, 0]),
                       dict(sampled_deviations_mm=[0]), dict(watertight=False),
                       dict(consistent_winding=False), dict(components=2),
                       dict(euler_preserved=False), dict(relative_volume_change=.021),
                       dict(relative_volume_change=float('nan'))):
            with self.subTest(change=change):
                self.assertFalse(surface.admitted({**baseline, **change}))

    def test_input_and_overwrite_checks_precede_native_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "input.stl"; source.write_bytes(b"fixture")
            with self.assertRaises(ValueError): surface.prepare(source, "wrong", root / "out")
            self.assertFalse((root / "out").exists())
            with self.assertRaises(ValueError): surface.prepare(source, surface.sha(source), root)


if __name__ == "__main__":
    unittest.main()
