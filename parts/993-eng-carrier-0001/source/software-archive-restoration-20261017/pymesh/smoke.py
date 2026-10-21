"""Import the restored PyMesh rootfs and run the existing nested-prism witness only."""
import hashlib, json, sys, time
from pathlib import Path
import numpy as np
import pymesh, PyMesh
from witnesses import prism

started = time.monotonic()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sys.version_info[:3] == (3, 6, 11)
assert np.__version__ == '1.19.0' and pymesh.__version__ == '0.3'
assert sha(PyMesh.__file__) == '17cd2bb3a74539b1f913501f49a362f65cb395a62ab65bc5a6e8815ccc585d8a'
leaves = [pymesh.form_mesh(*prism(h)) for h in (10, 20)]
tree = pymesh.CSGTree({'union': [{'mesh': mesh} for mesh in leaves]})
result = tree.mesh  # First and only conversion of the exact tree to the public mesh.
v, f = result.vertices, result.faces
assert v.dtype == np.float64 and np.isfinite(v).all() and len(f) > 0
edges = np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
unique, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
sums = np.bincount(inverse, weights=np.where(edges[:, 0] < edges[:, 1], 1, -1), minlength=len(unique))
assert (counts == 2).all() and (sums == 0).all()
assert result.volume == 4000.0
np.savez_compressed('result.npz', vertices=v, faces=f)
report = dict(status='restored_runtime_import_and_existing_prism_smoke_passed', python=sys.version,
              numpy=np.__version__, pymesh=pymesh.__version__, native_sha256=sha(PyMesh.__file__),
              native_module=PyMesh.__file__, vertices=len(v), faces=len(f), volume_mm3=result.volume,
              boundary_edges=0, nonmanifold_edges=0, inconsistent_orientation_edges=0,
              final_tree_mesh_accesses=1, result_sha256=sha('result.npz'), seconds=time.monotonic()-started,
              exact_installed_Cpp_commit=None, carrier_mesh_written=False, global_admission=False)
Path('smoke-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
