"""Assemblage CAO, exports STEP et contre-contrôle BRep des distances analytiques."""
import hashlib
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import components as comp
import kinematics as kin
from layout import PLUGS, VALVES

STEP_LIMIT = 1_000_000


def brep_valid(shape):
    return bool(BRepCheck_Analyzer(shape.wrapped).IsValid())


def brep_distance(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return float(d.Value())


def parts(p, phi_deg=0.0):
    laws, _ = kin.cam_laws(p)
    lifts = {side: float(law.valve_lift(np.radians(phi_deg))[0]) * 1e3 for side, law in laws.items()}
    out = {'head': comp.head(p), 'liner': comp.liner(p), 'gasket': comp.gasket(p), 'studs': comp.studs(p),
           'piston': comp.piston(p, phi_deg)}
    if 'plug_thread_reach' in p:
        out.update({f'spark_plug_{k}': comp.spark_plug(p, k) for k in PLUGS})
    articulated = 'rocker_valve_arm' in p
    if articulated:
        import rocker_train
        out.update(rocker_train.parts(p, phi_deg))
    else:
        for side in ('intake', 'exhaust'):
            out[f'camshaft_{side}'] = comp.camshaft(p, side, phi_deg)
    for side, sy in VALVES:
        tag = f'{side}_{"p" if sy > 0 else "m"}'
        lift = lifts[side]
        out[f'valve_{tag}'] = comp.valve(p, side, sy, lift)
        out[f'guide_{tag}'] = comp.guide(p, side, sy)
        out[f'seat_{tag}'] = comp.seat_insert(p, side, sy)
        out[f'retainer_{tag}'] = comp.retainer(p, side, sy, lift)
        out[f'spring_{tag}'] = comp.spring(p, side, sy, lift)
        if not articulated:
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


def chamber_volume(probe, occupied, seed, z0, z1):
    """Mesure uniquement le vide connecté à la chambre, avec fermeture aux bornes de la sonde.

    La différence booléenne évite de compter deux fois les intersections siège/soupape.
    Un vide atteignant une limite axiale artificielle ne définit pas un volume mort fermé.
    Le demandeur borne l'alésage dans la chemise et doit inclure l'extérieur au-dessus,
    pour ne pas transformer une sortie latérale de conduit en paroi artificielle.
    """
    # Les sièges et soupapes se recouvrent dans ce modèle simplifié ; construire d'abord
    # l'union évite les faces coïncidentes invalides d'une différence multi-outils.
    # Ne pas modifier les tolérances des entrées partagées lors du balayage de fenêtres.
    # Exécution sérielle pour rendre cette mesure (petite, hors boucle d'optimisation) répétable.
    union_op, cut_op = BRepAlgoAPI_Fuse(), BRepAlgoAPI_Cut()
    union_op.SetNonDestructive(True)
    cut_op.SetNonDestructive(True)
    solid = occupied[0]._bool_op(occupied[:1], occupied[1:], union_op, parallel=False) \
        if len(occupied) > 1 else occupied[0]
    if not brep_valid(solid):
        return {'clearance_volume_cc': None, 'status': 'blocked_invalid_occupied_brep'}
    void = probe._bool_op([probe], [solid], cut_op, parallel=False)
    result = {'clearance_volume_cc': None, 'status': 'blocked_invalid_chamber_brep'}
    if not brep_valid(void):
        return result
    candidates = [s for s in void.Solids() if s.isInside(seed, 1e-7)]
    if len(candidates) != 1:
        return dict(result, status='blocked_chamber_seed_not_unique', seed_components=len(candidates))
    chamber = candidates[0]
    volume = chamber.Volume()
    if not np.isfinite(volume) or volume <= 0:
        return result
    box = chamber.BoundingBox()
    boundaries = []
    if box.zmin <= z0 + 1e-6:
        boundaries.append('lower_probe_boundary')
    if box.zmax >= z1 - 1e-6:
        boundaries.append('upper_probe_boundary')
    result.update(connected_void_cc=round(volume / 1000, 6),
                  excluded_disconnected_void_cc=round((void.Volume() - volume) / 1000, 6),
                  artificial_boundaries_reached=boundaries)
    if boundaries:
        return dict(result, status='blocked_unsealed_chamber')
    return dict(result, clearance_volume_cc=volume / 1000,
                status='synthetic_twin_estimate_not_m64_value')


def compression_ratio(p, top_margin=2.0):
    """Volume mort connecté au PMH, jamais la somme de tous les vides d'un cylindre.

    Les pièces présentes doivent fermer la chambre (y compris les bougies). Le jeu radial
    piston/chemise sous la calotte est exclu : position des segments et volume de crevasse inconnus.
    Au-dessus de la chemise, la sonde englobe aussi les sorties de conduits : un cylindre
    limité à l'alésage fermerait artificiellement un conduit ouvert sur sa frontière latérale.
    ``top_margin`` agrandit aussi la boîte extérieure latéralement.
    """
    R = p['bore_diameter'] / 2
    crown = float(kin.piston_crown_z(p, np.array([0.0]))[0])
    z0 = crown - max(p['piston_bowl_depth'], p['piston_pocket_depth']) - 1.0
    if not np.isfinite(top_margin) or top_margin <= 0:
        raise ValueError('top_margin must be finite and positive')
    # Englober la culasse entière, pas seulement son toit nominal : les logements de
    # sièges débordent au-dessus du toit et ne doivent pas être tronqués par la sonde.
    z1 = max(p['roof_ridge_height'], p['carrier_face_height']) + top_margin
    head = comp.head(p)
    box = head.BoundingBox()
    shoulder = p['register_depth']
    if crown >= shoulder:
        raise ValueError('compression probe requires positive deck clearance below the liner top')
    # L'alésage ne borne le gaz que dans la chemise. Au-dessus, une boîte dépassant la
    # culasse relie toute fuite par les brides à l'extérieur et à la borne supérieure.
    probe = cq.Solid.makeBox(box.xlen + 2 * top_margin, box.ylen + 2 * top_margin, z1 - shoulder,
                            cq.Vector(box.xmin - top_margin, box.ymin - top_margin, shoulder)).fuse(
        cq.Solid.makeCylinder(R, shoulder - crown, cq.Vector(0, 0, crown)),
        cq.Solid.makeCylinder(R - 0.2, crown - z0, cq.Vector(0, 0, z0))).clean()
    solids = [head, comp.piston(p, 0.0)]
    for side, sy in (('intake', 1), ('intake', -1), ('exhaust', 1), ('exhaust', -1)):
        solids += [comp.valve(p, side, sy, 0.0), comp.seat_insert(p, side, sy)]
    if 'plug_thread_reach' in p:
        solids.extend(comp.spark_plug(p, k) for k in PLUGS)
    result = chamber_volume(probe, solids, cq.Vector(0, 0, crown + 0.5), z0, z1)
    vc = result['clearance_volume_cc']
    vs = float(np.pi) * R ** 2 * p['crank_stroke']
    return dict(result, swept_volume_cc=round(vs / 1000, 1),
                compression_ratio=1.0 + vs / (vc * 1000) if vc is not None else None,
                crown_tdc_z_mm=round(crown, 3), radial_crevice_included=False,
                probe_top_z_mm=z1,
                spark_plug_model='solid_packaging_envelope_no_thread_or_nose_crevices'
                if 'plug_thread_reach' in p else 'absent',
                valve_seat_model='concordant_ideal_faces' if 'seat_face_angle' in p else 'legacy_overlapping_solids',
                method='connected_brep_void_with_full_head_exterior_check')


def export_all(p, out_dir, final_checks, phi_deg=0.0, external_dir=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shapes = parts(p, phi_deg)
    head = shapes['head']
    validity = {name: brep_valid(s) for name, s in shapes.items()}
    head_solids = len(head.Solids())
    files = {}
    twins = dict(COMPONENT_TWINS)
    if 'rocker_valve_arm' in p:
        del twins['camshaft_follower']
        twins['articulated_rocker_train'] = [n for n in shapes if n.startswith(('camshaft_', 'rocker_', 'roller_'))]
    if 'plug_thread_reach' in p:
        twins['spark_plug_envelopes'] = [f'spark_plug_{k}' for k in PLUGS]
    for twin, names in twins.items():
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
    extra = {}
    if int(p.get('port_bezier_segments', 0)) > 0:  # G2 : coupes des conduits et taux de compression
        cuts = {
            'head-section-yz-intake.svg': (cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(p['intake_valve_x'], -500, -500)), (1, 0, 0)),
            'head-section-xy-ports.svg': (cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, -500, p['exhaust_port_z'])), (0, 0, 1)),
        }
        for name, (block, direction) in cuts.items():
            cq.exporters.export(cq.Workplane().add(head.cut(block)), str(out / name),
                                opt={'projectionDir': direction, 'showHidden': False})
            files[name] = (out / name).stat().st_size
        extra = {'compression': compression_ratio(p), 'head_face_count': len(head.Faces())}
    return {**extra,'brep_valid': validity, 'all_brep_valid': all(validity.values()), 'head_solid_count': head_solids,
            'head_volume_mm3': round(head.Volume(), 1), 'files_bytes': files, 'moved_out_of_repo': moved,
            'brep_cross_check': brep_cross_check(p, final_checks), 'assembly_phi_deg': phi_deg,
            'sha256': {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in files if (out / n).exists()}}
