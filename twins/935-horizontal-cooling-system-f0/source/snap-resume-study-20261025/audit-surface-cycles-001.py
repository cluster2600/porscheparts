"""Locate passages on the complete certified analysis surface; preserve every coordinate."""
import json
import time
import numpy as np
from locate_surface_cycles import surface_cycles
from run_reconstruction import ROOT, fresh, save, sha

started = time.monotonic()
parent = ROOT/'work/935-local-relocation-20261022'
source = parent/'candidate-002/candidate.npz'
expected = '0642cc25734981859c8c6d7bdf2e69d756d4ece0de422c78831067c4a8e164c6'
assert sha(source) == expected
proof = json.loads((parent/'geometry-assessment-002.json').read_text())
assert proof['complete_surface_bound_established'] and proof['output_sha256']['candidate.npz'] == expected
with np.load(source, allow_pickle=False) as data:
    vertices, faces = data['vertices'].copy(), data['faces'].copy()
cycles, report = surface_cycles(vertices, faces)
assert report['genus'] == 6 and report['basis_cycles'] == 12 and sha(source) == expected
out = fresh(ROOT/'work/935-snap-resume-20261025/surface-cycles-001')
np.savez_compressed(out/'cycles.npz', **{f'cycle_{i:02d}': cycle for i, cycle in enumerate(cycles)})
lengths = [float(np.linalg.norm(np.diff(vertices[cycle], axis=0), axis=1).sum()) for cycle in cycles]
report.update(source_sha256=sha(__file__), helper_sha256=sha(ROOT/'twins/935-horizontal-cooling-system-f0/source/locate_surface_cycles.py'),
              input_sha256=expected, cycles_npz_sha256=sha(out/'cycles.npz'),
              cycle_vertices=[len(c)-1 for c in cycles], cycle_lengths_source_units=lengths,
              elapsed_s=time.monotonic()-started, source_unit='uncalibrated_scan_unit',
              scale_verified=False, CFD_accepted=False, manufacturing_authorized=False,
              self_intersection_test_executed_by_this_audit=False)
save(out/'assessment.json', report)
print(json.dumps(report), flush=True)
