#!/usr/bin/env python3
"""Probe STEP serialization settings on a private native master, without healing."""
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
    p.add_argument('--surfacecurves', type=int, choices=(0, 1), required=True)
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.helpers))
    from export_native_brep_step_variants_f50 import read_native, sha256
    from audit_brep_f42 import read_step, brepcheck, shape_properties, topology
    from repair_pcurves_f42_2 import pcurve_fault_map
    from repair_topology_f42_1 import property_delta
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.Interface import Interface_Static
    from OCP.IFSelect import IFSelect_RetDone

    source = read_native(a.input)
    # Construct the controller before setting and reading back its static parameters.
    writer = STEPControl_Writer()
    if not Interface_Static.SetCVal_s('write.step.schema', 'AP242DIS'):
        raise ValueError('schema setting rejected')
    if not Interface_Static.SetIVal_s('write.surfacecurve.mode', a.surfacecurves):
        raise ValueError('surfacecurve setting rejected')
    observed = Interface_Static.IVal_s('write.surfacecurve.mode')
    if observed != a.surfacecurves:
        raise ValueError('surfacecurve setting not applied')
    out = a.output / 'candidate.step'
    if writer.Transfer(source, STEPControl_AsIs) != IFSelect_RetDone:
        raise RuntimeError('transfer failed')
    if writer.Write(str(out)) != IFSelect_RetDone:
        raise RuntimeError('write failed')
    reloaded, roots = read_step(out)
    faults = pcurve_fault_map(reloaded)
    report = {
        'schema': 'porsche-head-step-serialization-f53/v1',
        'source_sha256': a.sha256, 'step_sha256': sha256(out),
        'surfacecurve_mode_observed': observed, 'roots': roots,
        'pcurve_faults': faults['result_count'],
        'pcurve_status_counts': faults['status_counts'],
        'brepcheck': brepcheck(reloaded),
        'topology': topology(reloaded),
        'property_delta': property_delta(shape_properties(source), shape_properties(reloaded)),
        'manufacturing_authorized': False,
        'full_BOP_and_surface_deviation_audit_required': True,
    }
    (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pcurve_faults': report['pcurve_faults'],
                      'surfacecurve_mode_observed': observed}))
    return 0 if report['pcurve_faults'] == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
