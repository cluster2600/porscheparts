"""Assemblage CAO, exports STEP et contre-contrôle BRep des distances analytiques."""
import hashlib
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import components as comp
import kinematics as kin
from layout import VALVES

STEP_LIMIT = 1_000_000


def brep_valid(shape):
    return bool(BRepCheck_Analyzer(shape.wrapped).IsValid())


def brep_distance(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return float(d.Value())


def parts(p, phi_deg=0.0):
    phi, lifts = kin.lift_table(p, 1.0)
    k = int(np.argmin(np.abs(phi - (phi_deg % 720))))
    out = {'head': comp.head(p), 'liner': comp.liner(p), 'gasket': comp.gasket(p), 'studs': comp.studs(p),
           'piston': comp.piston(p, phi_deg)}
    for side in ('intake', 'exhaust'):
        out[f'camshaft_{side}'] = comp.camshaft(p, side, phi_deg)
    for side, sy in VALVES:
        tag = f'{side}_{"p" if sy > 0 else "m"}'
        lift = float(lifts[side][k])
        out[f'valve_{tag}'] = comp.valve(p, side, sy, lift)
        out[f'guide_{tag}'] = comp.guide(p, side, sy)
        out[f'seat_{tag}'] = comp.seat_insert(p, side, sy)
        out[f'retainer_{tag}'] = comp.retainer(p, side, sy, lift)
        out[f'spring_{tag}'] = comp.spring(p, side, sy, lift)
        out[f'follower_{tag}'] = comp.follower(p, side, sy, lift)
    return out


COMPONENT_TWINS = {
    'head': ['head'], 'valve_intake': ['valve_intake_p', 'valve_intake_m'], 'valve_exhaust': ['valve_exhaust_p', 'valve_exhaust_m'],
    'guide_seat_retainer': [f'{k}_{s}_{t}' for k in ('guide', 'seat', 'retainer') for s in ('intake', 'exhaust') for t in ('p', 'm')],
    'spring_gsc5092': [f'spring_{s}_{t}' for s in ('intake', 'exhaust') for t in ('p', 'm')],
    'camshaft_follower': ['camshaft_intake', 'camshaft_exhaust'] + [f'follower_{s}_{t}' for s in ('intake', 'exhaust') for t in ('p', 'm')],
    'cylinder_liner': ['liner'], 'piston': ['piston'], 'gasket': ['gasket'], 'studs': ['studs'],
}


def _export(shapes, path):
    cq.exporters.export(cq.Workplane().add(cq.Compound.makeCompound(shapes)), str(path))
    return path.stat().st_size


def brep_cross_check(p, final_checks, angles_per_side=4):
    """Distances BRep aux pires angles analytiques ; la BRep est une distance euclidienne (≤ jeu vertical)."""
    phi, lifts = kin.lift_table(p, 1.0)
    rows = []
    for side in ('intake', 'exhaust'):
        gaps = np.minimum(*(kin.valve_piston_gap(p, side, sy, phi, lifts[side]) for sy in (1, -1)))
        for k in np.argsort(gaps)[:angles_per_side]:
            pis = comp.piston(p, float(phi[k]))
            d = min(brep_distance(comp.valve(p, side, sy, float(lifts[side][k])), pis) for sy in (1, -1))
            rows.append({'pair': f'valve_{side}/piston', 'phi_deg': float(phi[k]), 'analytic_vertical_gap': round(float(gaps[k]), 3),
                         'brep_distance': round(d, 3), 'required': p[f'{side}_piston_clearance'],
                         'passed': d >= p[f'{side}_piston_clearance'] - 1e-6})
    vv = [c for c in final_checks if c['check'] == 'valve_valve_clearance_cycle'][0]
    ang = float(vv['detail'].split('φ=')[1].split('°')[0])
    k = int(np.argmin(np.abs(phi - ang)))
    d = min(brep_distance(comp.valve(p, 'intake', a, float(lifts['intake'][k])), comp.valve(p, 'exhaust', b, float(lifts['exhaust'][k])))
            for a in (1, -1) for b in (1, -1))
    rows.append({'pair': 'valve_intake/valve_exhaust', 'phi_deg': ang, 'analytic_distance': vv['value'],
                 'brep_distance': round(d, 3), 'required': p['min_valve_clearance'], 'passed': d >= p['min_valve_clearance'] - 1e-6})
    return rows


def export_all(p, out_dir, final_checks, phi_deg=0.0, external_dir=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shapes = parts(p, phi_deg)
    head = shapes['head']
    validity = {name: brep_valid(s) for name, s in shapes.items()}
    head_solids = len(head.Solids())
    files = {}
    for twin, names in COMPONENT_TWINS.items():
        path = out / f'twin-{twin}.step'
        size = _export([shapes[n] for n in names], path)
        files[path.name] = size
    asm = out / f'assembly-phi{int(phi_deg):03d}.step'
    size = _export(list(shapes.values()), asm)
    files[asm.name] = size
    moved = {}
    for name, size in list(files.items()):
        if size >= STEP_LIMIT and external_dir:
            ext = Path(external_dir)
            ext.mkdir(parents=True, exist_ok=True)
            (out / name).replace(ext / name)
            moved[name] = str(ext / name)
    keep = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, p['intake_valve_y'], -500))
    section = out / 'head-section-xz.svg'
    cq.exporters.export(cq.Workplane().add(head.cut(keep)), str(section),
                        opt={'projectionDir': (0, 1, 0), 'showHidden': False})
    files[section.name] = section.stat().st_size
    return {'brep_valid': validity, 'all_brep_valid': all(validity.values()), 'head_solid_count': head_solids,
            'head_volume_mm3': round(head.Volume(), 1), 'files_bytes': files, 'moved_out_of_repo': moved,
            'brep_cross_check': brep_cross_check(p, final_checks), 'assembly_phi_deg': phi_deg,
            'sha256': {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in files if (out / n).exists()}}
