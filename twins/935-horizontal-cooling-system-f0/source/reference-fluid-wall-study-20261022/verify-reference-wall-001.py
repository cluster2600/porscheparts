"""Independently verify complete serialized reference/outer-wall identity."""
import hashlib
import json
import signal
from pathlib import Path

import numpy as np
from run_reconstruction import read_obj, save

signal.alarm(300)
root = Path.cwd()
phase = root / 'work/935-reference-fluid-wall-20261022'
prepared = phase / 'prepared-001'
parent = root / 'work/935-cfd-mesh-correction-20261022/prepared-concavity20-001'
reference = root / 'work/935-cfd-pilot-20261022/rotor-001/coarse/constant/triSurface/rotor.obj'
sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()
proof = json.loads((prepared / 'receipt.json').read_text())
assert sha(reference) == proof['reference_SI_OBJ_sha256'] == '5eb9ee8a73b140198013fe511916c150316acc8e31174a2ca1fea4bac4db3e44'
for name, expected in proof['output_sha256'].items():
    assert sha(prepared / name) == expected
rv, rf, ignored = read_obj(reference)
assert len(rv) == 436712 and len(rf) == 873444
with np.load(prepared / 'boundary.npz') as data:
    v, f, m, hole = (data[k] for k in ['vertices', 'triangles', 'markers', 'hole'])
assert np.all(np.isfinite(v)) and len(v) == 445215 and len(f) == 890446
offset = len(v) - len(rv)
assert np.array_equal(v[offset:], rv)
assert np.array_equal(f[m == 4][:, ::-1] - offset, rf)
with np.load(parent / 'boundary.npz') as data:
    assert np.array_equal(m[m != 4], data['markers'][data['markers'] != 4])
    assert np.array_equal(v[f[m != 4]], data['vertices'][data['triangles'][data['markers'] != 4]])
ov, of, _ = read_obj(prepared / 'boundary.obj')
assert np.array_equal(ov, v) and np.array_equal(of, f)
with (prepared / 'fluid.smesh').open() as stream:
    assert list(map(int, stream.readline().split())) == [len(v), 3, 0, 0]
    nodes = np.loadtxt(stream, max_rows=len(v), ndmin=2)
    assert nodes.shape == (len(v), 4) and np.array_equal(nodes[:, 0], np.arange(len(v))) and np.array_equal(nodes[:, 1:], v)
    assert list(map(int, stream.readline().split())) == [len(f), 1]
    rows = np.loadtxt(stream, max_rows=len(f), dtype=np.int64, ndmin=2)
    assert rows.shape == (len(f), 5) and np.all(rows[:, 0] == 3) and np.array_equal(rows[:, 1:4], f) and np.array_equal(rows[:, 4], m)
    assert stream.readline().split() == ['1']
    hole_record = np.array(list(map(float, stream.readline().split())))
    assert hole_record.shape == (4,) and hole_record[0] == 0 and np.array_equal(hole_record[1:], hole)
    assert stream.readline().split() == ['0'] and not stream.read().strip()
r = {'status': 'all_reference_rotor_and_outer_duct_triangles_exact_in_bundle_OBJ_and_smesh', 'source_sha256': sha(__file__), 'preparation_receipt_sha256': sha(prepared / 'receipt.json'), 'reference_OBJ_sha256': sha(reference), 'reference_vertices_independently_read': len(rv), 'reference_triangles_independently_read': len(rf), 'reference_rotor_coordinate_and_triangle_order_identity': True, 'reference_rotor_orientation_reversed_for_fluid_hole': True, 'complete_outer_coordinate_triangle_marker_identity': True, 'complete_OBJ_and_smesh_readback_identity': True, 'surface_distance_between_reference_and_new_rotor_boundary_exactly_zero': True, 'identity_scope': 'entire serialized reference triangle set; not a bound to raw scans or historical hardware', 'output_hashes': proof['output_sha256'], 'scale_verified': False, 'CFD_accepted': False, 'manufacturing_authorized': False}
output = phase / 'serialized-wall-verification-001.json'
assert not output.exists()
save(output, r)
print(json.dumps(r), flush=True)
