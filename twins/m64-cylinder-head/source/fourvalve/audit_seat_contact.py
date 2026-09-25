#!/usr/bin/env python3
"""Audit des portées idéales et balayage limité des angles, sans autorisation de fabrication.

Usage : audit_seat_contact.py PARAMETERS_RESOLVED.json NEW_OUTPUT_DIRECTORY
"""
import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]

import assembly
import cadquery as cq
import checks
import components as comp
import layout
import numpy as np
import provenance


def audit(parameters, out):
    out.mkdir(parents=True, exist_ok=False)
    legacy = {k: row['value'] for k, row in json.loads(parameters.read_text()).items()}
    p = dict(legacy)
    extra = [HERE / name for name in ('params-plugs/spark_plug_envelope.json', 'params-seats/seat_contact.json')]
    for path in extra:
        for name, row in json.loads(path.read_text())['parameters'].items():
            provenance.verify_provenance(name, row, {})
            p[name] = row['value']
    head = comp.head(p)
    contacts, shapes = [], []
    for side, sy in layout.VALVES:
        valve, seat = comp.valve(p, side, sy), comp.seat_insert(p, side, sy)
        shapes.extend([valve, seat])
        r0, r1, z0, z1 = layout.seat_contact(p, side)
        area = math.pi * (r0 + r1) * math.hypot(r0 - r1, z1 - z0)
        vf = [f for f in valve.Faces() if f.geomType() == 'CONE' and abs(f.Area() - area) < 1e-6]
        sf = [f for f in seat.Faces() if f.geomType() == 'CONE' and abs(f.Area() - area) < 1e-6]
        shared = vf[0].intersect(sf[0]).Area() if len(vf) == len(sf) == 1 else None
        contacts.append({'side': side, 'sy': sy, 'valid': assembly.brep_valid(valve) and assembly.brep_valid(seat),
                         'legacy_overlap_mm3': comp.valve(legacy, side, sy).intersect(comp.seat_insert(legacy, side, sy)).Volume(),
                         'overlap_mm3': valve.intersect(seat).Volume(), 'closed_gap_mm': assembly.brep_distance(valve, seat),
                         'analytic_contact_area_mm2': area, 'brep_shared_face_area_mm2': shared,
                         'valve_head_overlap_mm3': valve.intersect(head).Volume(),
                         'seat_head_overlap_mm3': seat.intersect(head).Volume(),
                         'lift_gaps_mm': {str(lift): assembly.brep_distance(comp.valve(p, side, sy, lift), seat)
                                          for lift in (0.1, 1.0, p[f'{side}_max_lift'])}})
    with patch.object(comp, 'head', return_value=head):
        windows = [dict(exterior_margin_mm=m, **assembly.compression_ratio(p, m)) for m in (2.0, 5.0, 10.0)]
        negative = {}
        real_valve = comp.valve
        for side in layout.SIDES:
            def opened(p, s, sy, lift=0):
                return real_valve(p, s, sy, 1 if (s, sy) == (side, 1) else lift)
            with patch.object(comp, 'valve', side_effect=opened):
                negative[side + '_open_1mm'] = assembly.compression_ratio(p)
    # Échantillons bornés, pas une optimisation globale : tous les autres paramètres restent fixes.
    ladder = []
    for factor in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75):
        q = dict(p)
        if factor != 1:
            for side in layout.SIDES:
                q[f'{side}_axis_angle'] *= factor
            q['roof_ridge_height'] = q['register_depth'] + q['min_roof_edge_height'] + max(
                (abs(q[f'{s}_valve_x']) + q[f'{s}_valve_head_diameter'] / 2 * math.cos(math.radians(q[f'{s}_axis_angle'])))
                * math.tan(math.radians(q[f'{s}_axis_angle'])) for s in layout.SIDES)
        rows, summary = checks.evaluate(q, 0.5, force_cycle=True)
        ladder.append({'angle_factor': factor, 'intake_angle_deg': q['intake_axis_angle'],
                       'exhaust_angle_deg': q['exhaust_axis_angle'], 'roof_ridge_height_mm': q['roof_ridge_height'],
                       'uncalibrated_proxy_ratio_not_a_brep_result': checks.compression_ratio(q),
                       'geometry_summary': summary, 'checks': rows})
    assembly._export(shapes, out / 'four-valves-and-seats.step')
    # Zoom en coupe de la portée d'admission ; ne représente pas la culasse complète.
    centre, axis = layout.head_centre(p, 'intake', 1), layout.axis_up(p, 'intake')
    window = cq.Solid.makeCylinder(p['intake_valve_head_diameter'] / 2 + p['seat_insert_radial_wall'] + 1,
                                  p['seat_insert_height'] + 4, cq.Vector(*(centre - axis * 2)), cq.Vector(*axis))
    half = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, centre[1], -500))
    section = cq.Compound.makeCompound([s.intersect(window).cut(half) for s in shapes[:2]])
    section = section.translate(tuple(-centre)).rotate((0, 0, 0), (0, 1, 0), p['intake_axis_angle'])
    section = section.rotate((0, 0, 0), (1, 0, 0), -90)
    cq.exporters.export(cq.Workplane().add(section), str(out / 'seat-contact-section.svg'),
                        opt={'projectionDir': (0, 0, -1), 'showHidden': False, 'strokeWidth': 0.05,
                             'width': 1100, 'height': None, 'marginLeft': 20, 'marginTop': 20})
    # Normaliser avant de calculer les empreintes, jamais après publication de la preuve.
    svg = out / 'seat-contact-section.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    volumes = [r['clearance_volume_cc'] for r in windows]
    result = {'artifact': 'm64_g3_concordant_seat_contact_audit', 'manufacturing_authorized': False,
              'status': 'candidate_contact_geometry_only', 'head_geometry_modified': False,
              'contacts': contacts, 'compression_window_sweep': windows,
              'window_spread_cc': max(volumes) - min(volumes) if all(v is not None for v in volumes) else None,
              'negative_controls': negative, 'angle_ladder': ladder,
              'parameters_sha256': sha(parameters),
              'candidate_parameters_sha256': {str(f.relative_to(HERE)): sha(f) for f in extra},
              'source_sha256': {str(f.relative_to(HERE)): sha(f) for f in
                               sorted(list(HERE.glob('*.py')) + list((HERE / 'cad').glob('*.py')))},
              'files_sha256': {f.name: sha(f) for f in sorted(out.iterdir())},
              'environment': {'python': platform.python_version(), 'cadquery': cq.__version__, 'numpy': np.__version__},
              'limitations': ['ideal cold geometry, not a loaded contact analysis', 'no interference fit or manufacturing tolerances',
                              'no qualified heat transfer, fatigue or materials', 'thread, nose and ring-pack crevices omitted',
                              'angle ladder is a local screen, not a proof of global feasibility or impossibility']}
    (out / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'contacts': contacts, 'compression': windows, 'negative_controls': negative,
                      'ladder_failures': {str(r['angle_factor']): r['geometry_summary']['blocking_failed'] for r in ladder}}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.parameters, args.output)
