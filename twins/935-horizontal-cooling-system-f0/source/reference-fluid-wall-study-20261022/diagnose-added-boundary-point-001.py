"""Locate the unexpected boundary split without accepting or modifying it."""
import json
from pathlib import Path
import numpy as np
from import_conforming_volume import table, integer_points
from prepare_conforming_surface import sha

p = Path('/home/lolman/935-reference-fluid-wall-20261022')
source = p / 'prepared-001'
meshed = p / 'tetgen-001'
with np.load(source / 'boundary.npz') as z:
    rv, rf, tags = (z[k] for k in ['vertices', 'triangles', 'markers'])
v = table(meshed / 'fluid.1.node', 'node')
assert np.array_equal(v[:len(rv)], rv)
with (meshed / 'fluid.1.face').open() as stream:
    head = list(map(int, stream.readline().split()))
    data = np.loadtxt(stream, dtype=np.int64, ndmin=2)
assert data.shape == (head[0], 5)
boundary = data[data[:, 4] > 0, 1:4]
markers = data[data[:, 4] > 0, 4]
extra = np.setdiff1d(np.unique(boundary), np.arange(len(rv)))
assert len(extra) == 1
index = int(extra[0])
affected = np.any(boundary == index, axis=1)
new_faces = boundary[affected]
old = {tuple(sorted(f)): (f, int(t)) for f, t in zip(rf, tags)}
remaining = {tuple(sorted(f)) for f in boundary[~affected]}
missing = [f for key, (f, t) in old.items() if key not in remaining]
vertices = sorted(set(map(int, new_faces.ravel())) - {index})
edge = sorted(set(map(int, missing[0])) & set(map(int, missing[1])))
assert len(missing) == 2 and len(new_faces) == 4 and len(edge) == 2
ints, scale = integer_points(v[[*edge, index]])
a, b, c = map(np.array, ints)
cross = np.cross(b - a, c - a)
t = float(np.dot(v[index] - v[edge[0]], v[edge[1]] - v[edge[0]]) / np.sum((v[edge[1]] - v[edge[0]]) ** 2))
cells = table(meshed / 'fluid.1.ele', 'ele')
star = np.flatnonzero(np.any(cells == index, axis=1))
report = {'source_sha256': sha(__file__), 'new_boundary_point': index, 'coordinates_m': v[index].tolist(), 'patch_markers': sorted(set(map(int, markers[affected]))), 'old_faces': [list(map(int, f)) for f in missing], 'new_faces': new_faces.tolist(), 'edge': edge, 'projected_edge_parameter': t, 'exact_cross_product_in_common_integer_coordinates': list(map(str, cross)), 'exactly_collinear': all(x == 0 for x in cross), 'common_coordinate_scale': str(scale), 'distance_from_projected_edge_m': float(np.linalg.norm(v[index] - (v[edge[0]] + t * (v[edge[1]] - v[edge[0]])))), 'incident_cell_ids': star.tolist(), 'incident_cells': cells[star].tolist(), 'CFD_accepted': False}
with (p / 'added-boundary-point-diagnosis-001.json').open('x') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report), flush=True)
