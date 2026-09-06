#!/usr/bin/env python3
"""Private OCCT same-domain simplification trial, preserving input master."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--helpers', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from audit_brep_f42 import read_step, brepcheck, topology, shape_properties
    from repair_topology_f42_1 import write_step, property_delta
    from repair_pcurves_f42_2 import pcurve_fault_map
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    shape, _ = read_step(a.input)
    unify = ShapeUpgrade_UnifySameDomain(shape, True, True, False)
    unify.SetSafeInputMode(True)
    unify.SetLinearTolerance(1e-7)
    unify.Build()
    candidate = unify.Shape()
    path = a.output / 'candidate.step'
    write_step(candidate, path)
    reloaded, _ = read_step(path)
    report = {'schema': 'porsche-same-domain-trial-f54/v1',
              'source_sha256': a.sha256,
              'step_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'linear_tolerance_scan_units': 1e-7,
              'topology_before': topology(shape), 'topology_after': topology(reloaded),
              'brepcheck': brepcheck(reloaded),
              'pcurve_faults': pcurve_fault_map(reloaded)['result_count'],
              'property_delta': property_delta(shape_properties(shape), shape_properties(reloaded)),
              'full_BOP_and_surface_audit_required': True,
              'manufacturing_authorized': False}
    (a.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
