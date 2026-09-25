#!/usr/bin/env python3
"""Reprise bornée de l'implantation ressorts/chambre, à interfaces et gabarit fixes.

Usage : audit_spring_layout.py PARAMETERS_RESOLVED.json NEW_OUTPUT_DIRECTORY
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
import iterate
import layout
import numpy as np
import provenance
from cadcommon import _cyl


def floor_rows(p):
    rows = []
    for side in layout.SIDES:
        u = layout.axis_up(p, side)
        c = layout.head_centre(p, side, 1) + u * p[f'{side}_spring_seat_axial']
        r = p['spring_pocket_diameter'] / 2
        disk = cq.Face.makeFromWires(cq.Wire.makeCircle(r, cq.Vector(*c), cq.Vector(*u)))
        rows.append({'side': side, 'centre_z_mm': float(c[2]),
                     'analytic_rim_z_mm': float(c[2] + r * math.hypot(*u[:2])),
                     'brep_rim_z_mm': disk.BoundingBox().zmax,
                     'carrier_face_z_mm': p['carrier_face_height']})
    return rows


def audit(parameters, out):
    out.mkdir(parents=True, exist_ok=False)
    baseline = {k: row['value'] for k, row in json.loads(parameters.read_text()).items()}
    extra = [HERE / name for name in ('params-plugs/spark_plug_envelope.json', 'params-seats/seat_contact.json')]
    for path in extra:
        for name, row in json.loads(path.read_text())['parameters'].items():
            provenance.verify_provenance(name, row, {})
            baseline[name] = row['value']
    # Le facteur historique provenait d'une chambre ouverte. Proxy brut pour ce seul classement.
    base = dict(baseline, chamber_proxy_calibration=1.0, compression_proxy_band_tolerance=0.0)
    space = provenance.load_design_space()
    moving = {'intake_axis_angle', 'exhaust_axis_angle', 'intake_valve_x', 'exhaust_valve_x', 'valve_length_delta'}
    fixed = {v['name']: base[v['name']] for v in space['variables'] if v['stage'] == 1 and v['name'] not in moving}
    budget = dict(space['budget'], grid_samples=200, local_evaluations=400)
    search = iterate.Search(provenance.load_spec(), space, base, fixed=fixed, budget=budget)
    best = search.run(max_stage=1, seed_designs=[{k: base[k] for k in sorted(moving)}])
    design = iterate.mirror(dict(fixed, **best['design']), space)
    p = layout.derive(base, design)
    rows, summary = checks.evaluate(p, 0.5, force_cycle=True)
    old_rows, old_summary = checks.evaluate(baseline, 0.5, force_cycle=True)
    print(json.dumps({'trials': len(search.history), 'best': best, 'final_summary': summary}), flush=True)
    shapes = assembly.parts(p)
    with patch.object(comp, 'head', return_value=shapes['head']):
        compression = [dict(exterior_margin_mm=m, **assembly.compression_ratio(p, m)) for m in (2.0, 10.0)]
    cyl = layout.cylinders(p)
    walls = [{'stud': a, 'pocket': b, 'distance_mm': assembly.brep_distance(_cyl(*cyl[a]), _cyl(*cyl[b]))}
             for a in sorted(cyl) if a.startswith('stud_') for b in sorted(cyl) if b.startswith('pocket_')]
    contacts = []
    for side, sy in layout.VALVES:
        u = layout.axis_up(p, side)
        c = layout.head_centre(p, side, sy) + u * p[f'{side}_spring_seat_axial']
        spring = comp.spring(p, side, sy)
        faces = [f for f in spring.Faces() if f.geomType() == 'PLANE' and
                 abs((f.Center() - cq.Vector(*c)).dot(cq.Vector(*u))) < 1e-6]
        contacts.append({'side': side, 'sy': sy, 'base_face_count': len(faces),
                         'base_area_mm2': faces[0].Area() if len(faces) == 1 else None,
                         'supported_area_mm2': faces[0].intersect(shapes['head']).Area() if len(faces) == 1 else None,
                         'head_overlap_mm3': {str(lift): comp.spring(p, side, sy, lift).intersect(shapes['head']).Volume()
                                              for lift in (0.0, p[f'{side}_max_lift'])}})
    # Coupe CAO réelle à travers l'axe de la paire admission ; pas un rendu génératif.
    half = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, p['intake_valve_y'], -500))
    section = cq.Compound.makeCompound([s.cut(half) for s in shapes.values()]).rotate((0, 0, 0), (1, 0, 0), -90)
    cq.exporters.export(cq.Workplane().add(section), str(out / 'spring-layout-section.svg'),
                        opt={'projectionDir': (0, 0, -1), 'showHidden': False, 'strokeWidth': 0.15,
                             'width': 1100, 'height': None, 'marginLeft': 20, 'marginTop': 20})
    svg = out / 'spring-layout-section.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    (out / 'candidate.json').write_text(json.dumps({'manufacturing_authorized': False, 'design': design,
        'values': p, 'changed_values': {k: {'before': baseline[k], 'after': v} for k, v in p.items() if v != baseline[k]}},
        ensure_ascii=False, indent=2) + '\n')
    (out / 'search-history.json').write_text(json.dumps(search.history, ensure_ascii=False, separators=(',', ':')) + '\n')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {'artifact': 'm64_g4_spring_layout_audit', 'manufacturing_authorized': False, 'master_geometry': False,
              'status': 'candidate_layout_only', 'selected_trial': best['trial'], 'budget': budget,
              'moving_variables': sorted(moving), 'search_space_sha256': sha(provenance.DESIGN_SPACE),
              'baseline': {'floor_rows': floor_rows(baseline), 'summary': old_summary, 'checks': old_rows},
              'candidate': {'floor_rows': floor_rows(p), 'summary': summary, 'checks': rows,
                            'brep_validity': {n: assembly.brep_valid(s) for n, s in shapes.items()},
                            'head_solid_count': len(shapes['head'].Solids()), 'pocket_stud_walls': walls,
                            'spring_support_contacts': contacts,
                            'kinematic_brep_cross_checks': assembly.brep_cross_check(p, rows),
                            'compression_windows': compression, 'raw_proxy_ratio': checks.compression_ratio(p)},
              'parameters_sha256': sha(parameters), 'candidate_parameters_sha256': {str(f.relative_to(HERE)): sha(f) for f in extra},
              'source_sha256': {str(f.relative_to(HERE)): sha(f) for f in
                               sorted(list(HERE.glob('*.py')) + list((HERE / 'cad').glob('*.py')))},
              'files_sha256': {f.name: sha(f) for f in sorted(out.iterdir())},
              'environment': {'python': platform.python_version(), 'cadquery': cq.__version__, 'numpy': np.__version__},
              'limitations': ['bounded local search, not a global optimum', 'synthetic geometry, not a reconstructed M64 master',
                              'no qualified floor thickness, tolerances or loaded spring support',
                              'no functional rocker or cam carrier design', 'no thermal, fatigue, CFD or print qualification']}
    (out / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'compression': compression, 'minimum_pocket_stud_wall_mm': min(r['distance_mm'] for r in walls)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.parameters, args.output)
