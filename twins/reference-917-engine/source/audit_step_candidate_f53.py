#!/usr/bin/env python3
"""Hash-bound full OCCT audit of a private STEP candidate; no release claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--helpers', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != args.sha256:
        raise ValueError('source hash mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step, brepcheck, topology
    from repair_topology_f42_1 import full_bop_map
    shape, _ = read_step(args.input)
    report = {'schema': 'porsche-full-step-audit-f53/v1',
              'source_sha256': args.sha256,
              'brepcheck': brepcheck(shape), 'topology': topology(shape),
              'full_bop': full_bop_map(shape),
              'manufacturing_authorized': False}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    return 2 if report['full_bop']['has_faulty'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
