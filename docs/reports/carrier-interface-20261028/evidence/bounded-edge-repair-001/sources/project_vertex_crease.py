"""One fixed-radius nearest-vertex projection; full checks remain mandatory."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import struct

import igl
import numpy as np

r = Path(__file__).resolve().parent
out = r/"projection-002"
plan = json.loads((out/"plan.json").read_text())
assert not (out/"decoded-001").exists()
source = r.parent/"precision-transfer-001/carrier-local-001/candidate.npz"
raw = r/"carrier-001/decoded-001/candidate.npz"
assert hashlib.sha256(source.read_bytes()).hexdigest() == plan["distance_source_sha256"]
assert hashlib.sha256(raw.read_bytes()).hexdigest() == plan["input_sha256"]
inclusion = json.loads((out/"inclusion-002/decoded-001/independent-domain.json").read_text())
assert inclusion["whole_bounded_solid_containment_proved"]
assert inclusion["source_faces"] == 7781064 and inclusion["candidate_faces"] == 1139034
sz, rz = np.load(source), np.load(raw)
sv, sf = sz["vertices"], sz["triangles"]
v, f = rz["vertices"], rz["triangles"]
i, nearest_vertex = plan["vertex_to_project"], plan["expected_nearest_source_vertex"]
before = v[i].copy()
d2, ids, closest = igl.point_mesh_squared_distance(before[None, :], sv, sf)
if not np.array_equal(closest[0], sv[nearest_vertex]):
    raise ValueError("Actual nearest source feature is not the frozen vertex")
distance = float(np.sqrt(d2[0]))
direction = (before-closest[0])/distance
after = closest[0]+plan["target_unsigned_outward_distance_mm"]*direction
bound = float(np.nextafter(np.abs(after-before).sum(), np.inf))
if bound > plan["maximum_complete_l1_displacement_mm"]:
    raise ValueError("Same-topology displacement budget exceeded")
new_d2, new_ids, new_closest = igl.point_mesh_squared_distance(after[None, :], sv, sf)
if not np.array_equal(new_closest[0], sv[nearest_vertex]):
    raise ValueError("Nearest source feature changes after projection")
residual = abs(float(np.sqrt(new_d2[0]))-plan["target_unsigned_outward_distance_mm"])
if residual > plan["maximum_target_distance_residual_mm"]:
    raise ValueError("Projected point misses the source-distance level")
v[i] = after
dest = out/"decoded-001"
dest.mkdir()
np.savez(dest/"candidate.npz", vertices=v, triangles=f)
with (dest/"candidate.meshbin").open("wb") as stream:
    stream.write(struct.pack("<QQ", len(v), len(f)))
    v.astype("<f8").tofile(stream)
    f.astype("<u8").tofile(stream)
report = dict(status="nearest_vertex_projection_authored_independent_checks_pending", vertex=i,
              source_vertex=nearest_vertex, source_vertex_mm=closest[0].tolist(),
              before_mm=before.tolist(), after_mm=after.tolist(), nearest_source_face=int(ids[0]),
              source_distance_before_mm=distance, source_distance_after_mm=float(np.sqrt(new_d2[0])),
              target_residual_mm=residual, authored_l1_displacement_mm=bound,
              libigl_version=importlib.metadata.version("libigl"),
              input_inclusion_report_sha256=hashlib.sha256((out/"inclusion-002/decoded-001/independent-domain.json").read_bytes()).hexdigest(),
              output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir()},
              manufacturing_authorized=False)
(out/"assessment.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
