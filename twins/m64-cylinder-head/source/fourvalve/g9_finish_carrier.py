#!/usr/bin/env python3
"""Finish only G9's fine carrier after a dependency failure; preserve prior output."""
import argparse
import json
from pathlib import Path

import g9_reference_campaign as campaign

g8 = campaign.g8


def finish(args):
    checkpoint = args.partial / 'report.partial.json'
    report = json.loads(checkpoint.read_text())
    expected = {('witness-2.0', 'x')} | {(c+'-'+str(s), d)
        for c, sizes in (('central_diaphragm', (3., 2., 1.5)), ('carrier_base_p', (3., 2.)))
        for s in sizes for d in ('x', 'minus_z')}
    if (len(report['cases']) != 11 or {(r['case'], r['direction']) for r in report['cases']} != expected
            or not all(r['numerical_crosscheck_passed'] for r in report['cases'])
            or report['source_sha256'] != g8.sha256(Path(campaign.__file__))
            or report['complete'] is not False):
        raise ValueError('requires unchanged cross-checked 11-case checkpoint')
    # Recheck the scalar receipt against its actual preserved solver artifacts.
    for row in report['cases']:
        for name, digest in row['hashes'].items():
            if g8.sha256(args.partial / row['case'] / name) != digest:
                raise ValueError('checkpoint artifact changed')
    baseline = json.loads(g8.BASELINE.read_text())
    for path, expected_hash in baseline['source_sha256'].items():
        if g8.sha256(g8.REPO / path) != expected_hash:
            raise ValueError('G7 source fingerprint mismatch: ' + path)
    if g8.sha256(args.cad / 'carrier_base_p.step') != baseline['files_sha256']['carrier_base_p.step']:
        raise ValueError('G7 STEP changed')
    args.output.mkdir(parents=True, exist_ok=False)
    case = args.output / 'carrier_base_p-1.5'
    case.mkdir()
    p = baseline['values']
    axes = {s: g8.rocker_geometry.frame(p, s, 1)[0] for s in ('intake', 'exhaust')}
    forces = {s: max(r['G7_shaft_only']['outer_rib_reaction_N'] for r in baseline['screens']['shaft_comparison'] if r['side'] == s) for s in axes}
    points, elements, support, weights, mesh = g8.mesh(args.cad / 'carrier_base_p.step', 1.5, p, axes, 'carrier_base_p', case)
    for name, direction in (('x', [1, 0, 0]), ('minus_z', [0, 0, -1])):
        g8.solve(case, points, elements, support, weights, forces, direction, name)
    (case / 'mesh-info.json').write_text(json.dumps(mesh, indent=2))
    report['cases'].extend(campaign.audit(case, ('x', 'minus_z'), args.legacy, 'cuda'))
    report['checkpoint_sha256'] = g8.sha256(checkpoint)
    report['resume_source_sha256'] = g8.sha256(Path(__file__))
    report['complete'] = len(report['cases']) == 13 and all(r['numerical_crosscheck_passed'] for r in report['cases'])
    (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('partial', 'cad', 'legacy', 'output'):
        parser.add_argument('--'+flag, type=Path, required=True)
    raise SystemExit(finish(parser.parse_args()))
