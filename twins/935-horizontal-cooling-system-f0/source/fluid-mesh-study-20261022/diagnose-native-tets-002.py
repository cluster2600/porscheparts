"""Reproduce native FV failures and locate them against the named boundary patches."""
import hashlib, importlib.util, json, re, sys
from pathlib import Path
import numpy as np

case, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('foam_ascii', Path(__file__).with_name('export-fluid-plc-005.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
mesh = case / 'constant/polyMesh'
def array(name, columns, dtype=float):
    count, body = module.foam_list(mesh / name, maximum_count=10_000_000)
    value = np.fromstring(body.replace('(', ' ').replace(')', ' '), sep=' ', dtype=dtype).reshape(-1, columns)
    assert len(value) == count
    return value
points = array('points', 3)
faces = array('faces', 4, np.int64); assert np.all(faces[:, 0] == 3); faces = faces[:, 1:]
owner = array('owner', 1, np.int64).ravel(); neighbour = array('neighbour', 1, np.int64).ravel()
n = int(max(owner.max(), neighbour.max())) + 1; ni = len(neighbour); assert len(owner) == len(faces)
x = points[faces]; centres = x.mean(axis=1); areas = np.cross(x[:, 1]-x[:, 0], x[:, 2]-x[:, 0])/2
counts = np.bincount(owner, minlength=n) + np.bincount(neighbour, minlength=n); assert np.all(counts == 4)
cc = np.zeros((n, 3)); np.add.at(cc, owner, centres); np.add.at(cc, neighbour, centres[:ni]); cc /= 4
internal_counts = np.bincount(owner[:ni], minlength=n) + np.bincount(neighbour, minlength=n)
mag = np.linalg.norm(areas[:ni], axis=1)
sum_area = np.bincount(owner[:ni], weights=mag, minlength=n) + np.bincount(neighbour, weights=mag, minlength=n)
avg_area = np.divide(sum_area, internal_counts, out=np.ones(n), where=internal_counts > 0)
tensor = np.zeros((n, 3, 3)); products = areas[:ni, :, None] * areas[:ni, None, :]
np.add.at(tensor, owner[:ni], products); np.add.at(tensor, neighbour, products)
determinant = np.abs(np.linalg.det(tensor / avg_area[:, None, None]**2))
bad_cells = determinant < .001
delta = cc[neighbour] - cc[owner[:ni]]
cosine = np.einsum('ij,ij->i', areas[:ni], delta) / (mag * np.linalg.norm(delta, axis=1))
bad_faces = np.degrees(np.arccos(np.clip(cosine, -1, 1))) > 70
log = (case / 'log.checkMesh.allGeometry').read_text()
native_det = int(re.search(r'Cells with small determinant.*?number of cells: (\d+)', log)[1])
native_nonorth = int(re.search(r'Number of severely non-orthogonal.*?faces: (\d+)', log)[1])
assert int(bad_cells.sum()) == native_det and int(bad_faces.sum()) == native_nonorth
_, body = module.foam_list(mesh / 'boundary')
patch_cells = {}
for match in re.finditer(r'([A-Za-z][A-Za-z0-9_]*)\s*\{([^{}]*)\}', body):
    start = int(re.search(r'\bstartFace\s+(\d+)\s*;', match[2])[1]); count = int(re.search(r'\bnFaces\s+(\d+)\s*;', match[2])[1])
    adjacent = np.zeros(n, dtype=bool); adjacent[owner[start:start+count]] = True
    patch_cells[match[1]] = {'adjacent_cells': int(adjacent.sum()), 'small_determinant_cells': int((adjacent & bad_cells).sum()), 'severe_nonorth_faces_touching_adjacent_cells': int((bad_faces & (adjacent[owner[:ni]] | adjacent[neighbour])).sum())}
result = {'status': 'all_native_failure_counts_reproduced_independently', 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'native_log_sha256': hashlib.sha256((case/'log.checkMesh.allGeometry').read_bytes()).hexdigest(), 'cells': n, 'small_determinant_cells': native_det, 'severe_nonorthogonal_faces': native_nonorth, 'small_determinant_by_number_of_internal_faces': {str(k): int((bad_cells & (internal_counts == k)).sum()) for k in range(5)}, 'patch_adjacency': patch_cells, 'boundary_vertices_changed': False, 'CFD_accepted': False}
with output.open('x') as stream: json.dump(result, stream, indent=2)
print(json.dumps(result), flush=True)
