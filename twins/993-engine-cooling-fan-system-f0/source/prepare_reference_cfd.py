#!/usr/bin/env python3
"""Prepare an audited isolated-rotor comparison, never an installed PMB model."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import trimesh

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('geometry', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--level', type=int, default=4, choices=[3, 4, 5])
p.add_argument('--iterations', type=int, default=500, choices=[300, 500])
p.add_argument('--device', default='cpu')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
original = a.geometry / 'rotor-mm.stl'
m = trimesh.load_mesh(original, process=True)
assert m.is_watertight and m.body_count == 1 and m.is_winding_consistent
# Preserve triangle order for the independent mm/metre audit.
m.export(a.output / 'rotor-mm.stl')
m.apply_scale(.001); m.export(a.output / 'rotor-metres.stl')
generation = json.loads((a.geometry / 'generation.json').read_text())
report = {'source_generation': generation,
          'source_stl_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
          'input_parameters': {'outer_diameter_mm':generation['parameters']['rotor_diameter_mm'],
          'housing_diameter_mm':generation['parameters']['rotor_diameter_mm']+3,
          'depth_mm':float(abs(m.bounds).max(axis=0)[2]*2000)},
          'rig': 'Cylindrical test duct; assumed 1.5 mm nominal radial clearance',
          'rotation': 'Negative about +Z; geometric pumping direction, not verified vehicle drive',
          'pmb_represented':False, 'manufacturing_authorized':False}
(a.output / 'picogk-report.json').write_text(json.dumps(report,indent=2)+'\n')
runpy.run_path(str(HERE/'audit_fan_physicsnemo.py'))['audit'](
    a.output/'rotor-mm.stl', a.output/'physicsnemo-surface-audit.json', a.device)
runpy.run_path(str(HERE/'build_fan_cfd.py'))['generate'](
    a.output/'case', a.output/'rotor-metres.stl', 3000, 24, a.level, rotor_only=True, rotation_sign=-1)
control = a.output/'case/system/controlDict'
control.write_text(control.read_text().replace('endTime 1200;', f'endTime {a.iterations};')
                   .replace('writeInterval 1200;', f'writeInterval {a.iterations};'))
manifest = a.output/'case/fan-input.json'
data = json.loads(manifest.read_text())
data['study_iteration_budget'] = a.iterations
data['termination_policy'] = 'Bounded exploratory trial; no convergence claim at budget exhaustion or after an explicit mesh-quality rejection'
manifest.write_text(json.dumps(data, indent=2)+'\n')
