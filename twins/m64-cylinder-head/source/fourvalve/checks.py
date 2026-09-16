"""Contrôles de l'assemblage 4 soupapes / 2 bougies. Chaque échec est rapporté, jamais ajusté."""
import math

import numpy as np

import kinematics as kin
from layout import (PLUGS, SIDES, VALVES, axis_up, cam_axis_point, cylinders, head_centre, head_projection,
                    plug_open_radius, plug_opening, segment_distance)


def _c(name, value, limit, relation, detail, blocking=True, family='geometry'):
    value, limit = float(value), float(limit)
    slack = value - limit if relation == '>=' else limit - value
    return {'check': name, 'family': family, 'value': round(value, 3), 'limit': round(limit, 3),
            'relation': relation, 'slack': round(slack, 3), 'passed': bool(slack >= -1e-9),
            'blocking': blocking, 'detail': detail}


def not_computable(name, reason):
    return {'check': name, 'family': 'geometry', 'value': None, 'limit': None, 'relation': None, 'slack': None,
            'passed': None, 'blocking': False, 'status': 'not_computable', 'detail': reason}


def required_liner_od(p):
    return p['bore_diameter'] + 2 * p['liner_min_spigot_wall'] + 2 * p['liner_spigot_radial_clearance']


def displacement_cc(bore_mm, stroke_mm, cylinders=6):
    return cylinders * math.pi / 4 * bore_mm ** 2 * stroke_mm / 1000.0


def chamber_volume_mm3(p, n=361):
    """Volume mort approché au PMH : toit moins calotte, intégré sur le disque d'alésage.

    Proxy numpy pour l'itération (sans CAO). La calotte reprend ``crown_depression`` : poches et
    bol comptent donc exactement comme en cinématique, recouvrements compris. Restent ignorés les
    logements de sièges, les gorges et les conduits qui débouchent dans la chambre : c'est le biais
    résiduel que corrige ``chamber_proxy_calibration``. Le rapport CAO garde le volume BRep comme
    valeur de référence.
    """
    R = p['bore_diameter'] / 2
    crown = float(kin.piston_crown_z(p, np.array([0.0]))[0])
    grid = np.linspace(-R, R, n)
    X, Y = np.meshgrid(grid, grid)
    inside = X ** 2 + Y ** 2 <= R ** 2
    zi = p['roof_ridge_height'] + X * math.tan(math.radians(p['intake_axis_angle']))
    ze = p['roof_ridge_height'] - X * math.tan(math.radians(p['exhaust_axis_angle']))
    roof = np.maximum(np.minimum(zi, ze), p['register_depth'])
    floor = crown - kin.crown_depression(p, np.stack((X, Y), axis=-1))
    cell = (2 * R / (n - 1)) ** 2
    return float(np.sum(np.maximum(roof - floor, 0.0)[inside]) * cell)


def calibrated_chamber_volume_mm3(p, n=361):
    """Proxy corrigé du biais résiduel mesuré en BRep (sièges, gorges, conduits)."""
    return chamber_volume_mm3(p, n) * p.get('chamber_proxy_calibration', 1.0)


def _ratio(vc, p):
    vs = math.pi * (p['bore_diameter'] / 2) ** 2 * p['crank_stroke']
    return (vs + vc) / vc if vc > 0 else math.inf


def compression_ratio(p):
    return _ratio(chamber_volume_mm3(p), p)


def calibrated_compression_ratio(p):
    return _ratio(calibrated_chamber_volume_mm3(p), p)


def compression_proxy(p, tolerance=None):
    """Volume mort calibré, taux et écart à la plage, en une seule intégration.

    L'itération appelle ce point d'entrée à chaque essai : la boucle est chaude et l'intégration
    sur le disque d'alésage est la partie coûteuse. ``tolerance`` élargit la plage ; le proxy n'est
    pas le juge et ne doit pas écarter un candidat que la mesure BRep aurait retenu. Hors G2,
    l'écart est nul : aucun critère de combustion n'existe.
    """
    vc = calibrated_chamber_volume_mm3(p)
    cr = _ratio(vc, p)
    if 'compression_ratio_min' not in p:
        return {'clearance_mm3': vc, 'ratio': cr, 'band_gap': 0.0}
    tol = p.get('compression_proxy_band_tolerance', 0.0) if tolerance is None else tolerance
    gap = max(p['compression_ratio_min'] - tol - cr, cr - p['compression_ratio_max'] - tol, 0.0)
    return {'clearance_mm3': vc, 'ratio': cr, 'band_gap': float(gap)}


def compression_band_gap(p, tolerance=None):
    """Écart, en points de taux, entre le taux calibré et la plage visée ; 0 dans la plage."""
    return compression_proxy(p, tolerance)['band_gap']


def _ellgap(A, B):
    return float(np.min(np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)))


def static_checks(p):
    out = []
    R, L, wall = p['bore_diameter'] / 2, p['min_ligament'], p['min_wall']
    proj = {v: head_projection(p, *v) for v in VALVES}
    out.append(_c('valve_heads_within_bore', min(R - np.max(np.hypot(*a.T)) for a in proj.values()),
                  p['min_bore_edge_margin'], '>=', f'retrait du bord de tête projeté sous l\'alésage Ø{2 * R:g}'))
    out.append(_c('ligament_intake_intake', _ellgap(proj[('intake', 1)], proj[('intake', -1)]), L, '>=', 'pont adm/adm projeté'))
    out.append(_c('ligament_exhaust_exhaust', _ellgap(proj[('exhaust', 1)], proj[('exhaust', -1)]), L, '>=', 'pont éch/éch projeté'))
    out.append(_c('ligament_intake_exhaust', min(_ellgap(proj[('intake', a)], proj[('exhaust', b)])
                                                for a in (1, -1) for b in (1, -1)), L, '>=', 'pont adm/éch projeté (4 paires)'))
    ridge = min(-(p['intake_valve_x'] + p['intake_valve_head_diameter'] / 2 * math.cos(math.radians(p['intake_axis_angle']))),
                p['exhaust_valve_x'] - p['exhaust_valve_head_diameter'] / 2 * math.cos(math.radians(p['exhaust_axis_angle'])))
    out.append(_c('valve_face_on_own_roof_plane', ridge, 0.0, '>=', 'tête entièrement de son côté de l\'arête du toit'))
    # bougies
    openings = {k: plug_opening(p, k) for k in PLUGS}
    ropen = {k: plug_open_radius(p, k) for k in PLUGS}
    out.append(_c('spark_plugs_within_bore', min(R - np.hypot(*openings[k][0][:2]) - ropen[k] for k in PLUGS),
                  p['min_bore_edge_margin'], '>=', 'empreinte des 2 puits de bougie sous l\'alésage'))
    for k in PLUGS:
        o = openings[k][0][:2]
        g = min(float(np.min(np.hypot(*(a - o).T))) for a in proj.values()) - ropen[k]
        out.append(_c(f'ligament_plug_{k}_to_seats', g, L, '>=', f'pont projeté bougie {k} / bords de têtes'))
    g = float(np.hypot(*(openings[1][0][:2] - openings[2][0][:2]))) - ropen[1] - ropen[2]
    out.append(_c('ligament_plug_plug', g, L, '>=', 'pont projeté bougie 1 / bougie 2'))
    cyl = cylinders(p)

    def gap(a, b):
        pa, qa, ra = cyl[a]
        pb, qb, rb = cyl[b]
        return segment_distance(pa, qa, pb, qb) - ra - rb

    def worst(prefix_a, prefix_b, name, detail, blocking=True, family='geometry'):
        pairs = {tuple(sorted((a, b))) for a in cyl if a.startswith(prefix_a)
                 for b in cyl if b.startswith(prefix_b) and a != b}
        if prefix_a == prefix_b:
            pairs = {q for q in pairs if q[0][:-2] != q[1][:-2] or True}
        g_, who = min((gap(a, b), (a, b)) for a, b in pairs)
        out.append(_c(name, g_, wall, '>=', f'{detail} ; pire paire {who[0]} / {who[1]}', blocking, family))

    worst('plug_1', 'plug_2', 'plug_plug_wall', 'paroi puits 1 / puits 2 (capsules)')
    worst('plug_', 'port_', 'plug_vs_ports', 'paroi puits de bougie / conduits')
    worst('plug_', 'stud_', 'plug_vs_studs', 'paroi puits de bougie / goujons')
    worst('plug_', 'pocket_', 'plug_vs_spring_pockets', 'paroi puits de bougie / logements de ressort')
    worst('plug_', 'guide_', 'plug_vs_guides', 'paroi puits de bougie / guides')
    # goujons
    r_stud = p['stud_hole_diameter'] / 2
    stud_r = math.hypot(p['stud_span_x'] / 2, p['stud_span_y'] / 2)
    out.append(_c('stud_wall_to_chamber', stud_r - r_stud - R, wall, '>=', f'paroi trou de goujon / alésage Ø{2 * R:g}'))
    worst('stud_', 'port_', 'stud_vs_ports', 'paroi goujon / conduits')
    worst('stud_', 'pocket_', 'stud_vs_spring_pockets', 'paroi goujon / logements de ressort')
    # logements de ressort
    worst('pocket_intake', 'pocket_exhaust', 'spring_pocket_intake_vs_exhaust', 'paroi logements adm / éch')
    for side in SIDES:
        g_ = gap(f'pocket_{side}_p', f'pocket_{side}_m')
        out.append(_c(f'spring_pocket_{side}_pair', g_, wall, '>=', f'paroi entre les 2 logements {side}'))
    worst('pocket_', 'port_', 'spring_pocket_vs_ports', 'paroi fond de logement / conduits')
    if 'compression_ratio_min' in p:  # G2 seulement : G1 n'avait aucun critère de compression
        raw, cal = chamber_volume_mm3(p), calibrated_chamber_volume_mm3(p)
        cr = _ratio(cal, p)
        detail = (f'PROXY, non bloquant : volume mort brut {raw / 1000:.1f} cm³ (toit, poches et bol), calibré '
                  f'×{p.get("chamber_proxy_calibration", 1.0):.3f} = {cal / 1000:.1f} cm³ pour les sièges, gorges et '
                  f'conduits qu\'il ignore ; taux brut {_ratio(raw, p):.2f}. Arête de toit {p["roof_ridge_height"]:.1f} mm, '
                  f'angles {p["intake_axis_angle"]:.1f}/{p["exhaust_axis_angle"]:.1f}°. '
                  f'Le juge est le taux BRep du rapport CAO.')
        out.append(_c('compression_ratio_proxy_min', cr, p['compression_ratio_min'], '>=', detail,
                      blocking=False, family='combustion'))
        out.append(_c('compression_ratio_proxy_max', cr, p['compression_ratio_max'], '<=', detail,
                      blocking=False, family='combustion'))
    if 'oil_gallery' in cyl:  # G2 seulement
        for other, name in (('pocket_', 'spring_pockets'), ('guide_', 'guides'), ('plug_', 'plugs'),
                            ('stud_', 'studs'), ('port_', 'ports')):
            worst('oil_', other, f'oil_gallery_vs_{name}', f'paroi galerie d\'huile / {name}', family='oil')
        a, b, r = cyl['oil_gallery']
        out.append(_c('oil_gallery_below_carrier_face', p['carrier_face_height'] - a[2] - r, wall, '>=',
                      'paroi entre galerie d\'huile et face porte-arbre', family='oil'))
    seat_z = max(head_centre(p, s, sy)[2] + axis_up(p, s)[2] * p[f'{s}_spring_seat_axial'] for s, sy in VALVES)
    out.append(_c('spring_seat_below_carrier_face', seat_z, p['carrier_face_height'], '<=',
                  'fond de logement sous la face porte-arbre 935'))
    # ressort
    lift = max(p['intake_max_lift'], p['exhaust_max_lift'])
    out.append(_c('lift_within_gsc5092_published', lift, p['spring_max_lift_published'], '<=',
                  'levée Swindon vs levée max publiée GSC5092', family='spring'))
    out.append(_c('spring_coil_bind_reserve', p['spring_installed_height'] - lift - p['spring_coil_bind_length'],
                  p['coil_bind_min_reserve'], '>=', 'hauteur montée − levée − longueur jointive (GSC5092 publiées)',
                  family='spring'))
    # centrage / chemise (deviennent limitants avec un grand alésage)
    liner_od = required_liner_od(p)
    out.append(_c('register_vs_required_liner_od', p['register_diameter'], liner_od, '>=',
                  f'Ø centrage culasse (candidat 935) vs Ø ext chemise requis = alésage + 2·paroi {p["liner_min_spigot_wall"]:g}'
                  f' + 2·jeu {p["liner_spigot_radial_clearance"]:g} = {liner_od:.2f}'))
    usable = 2 * (stud_r - r_stud)
    out.append(_c('liner_od_vs_stud_holes', usable, liner_od, '>=',
                  f'Ø libre entre trous de goujon = 2·(distance axe goujon–axe cylindre {stud_r:.2f} − rayon trou '
                  f'{r_stud:.2f}) vs Ø ext chemise requis ; paroi chemise vers goujons = {(usable - p["bore_diameter"]) / 2:.2f}'))
    out.append(not_computable('inter_cylinder_bridge', 'entraxe des cylindres M64 non sourcé dans le dépôt (seul un '
                              'entraxe 917/Type 912 de 118 mm, niveau C, existe : non transférable) ; pont entre '
                              'cylindres voisins non calculable'))
    # piston
    pockets = kin.piston_pockets(p)
    land = min(R - math.hypot(x, y) - r for x, y, r in pockets) if p['piston_pocket_depth'] > 0 else R
    out.append(_c('piston_pockets_within_crown', land, p['piston_ring_land_margin'], '>=',
                  'bord de poche en retrait de l\'alésage (sans objet si profondeur nulle)', family='piston'))
    out.append(_c('piston_pocket_depth_admissible', p['piston_pocket_depth'], p['piston_max_pocket_depth'], '<=',
                  'profondeur de poche', family='piston'))
    # arbres à cames
    ci, ce = cam_axis_point(p, 'intake'), cam_axis_point(p, 'exhaust')
    reach = {s: p['cam_base_circle_radius'] + p[f'{s}_max_lift'] for s in SIDES}
    out.append(_c('cam_lobe_clearance', float(np.linalg.norm(ci - ce)) - reach['intake'] - reach['exhaust'], wall, '>=',
                  'entraxe des arbres − rayons de came max', family='cam'))
    out.append(_c('cam_lobes_above_carrier_face', min(ci[2] - reach['intake'], ce[2] - reach['exhaust']),
                  p['carrier_face_height'], '>=', 'point bas des cames au-dessus de la face porte-arbre', family='cam'))
    laws, _ = kin.cam_laws(p)
    ph = np.radians(np.arange(0, 720, 0.5))
    e_max = max(2e3 * float(np.max(np.abs(laws[s].cam_derivatives(ph, 1)))) for s in SIDES)
    out.append(_c('bucket_follower_contact_within_pocket', p['spring_pocket_diameter'] / 2 - p['bucket_contact_margin'],
                  e_max, '>=', f'indicatif : un poussoir à coupelle exigerait un rayon ≥ {e_max:.1f} + marge '
                  '(commande retenue : culbuteur)', blocking=False, family='cam'))
    return out


def cycle_checks(p, step_deg):
    out = []
    phi, lifts = kin.lift_table(p, step_deg)
    best, where = math.inf, None
    for a in (1, -1):
        for b in (1, -1):
            mask = (lifts['intake'] > 0) | (lifts['exhaust'] > 0)
            d = kin.pair_distance_over_cycle(p, ('intake', a), ('exhaust', b), lifts['intake'][mask], lifts['exhaust'][mask])
            i = int(np.argmin(d))
            if d[i] < best:
                best, where = float(d[i]), float(phi[mask][i])
    k = int(np.argmin(np.abs(phi - where)))
    out.append(_c('valve_valve_clearance_cycle', best, p['min_valve_clearance'], '>=',
                  f'min sur 720° pas {step_deg:g}° ; pire φ={where:g}° (levées {lifts["intake"][k]:.2f} / '
                  f'{lifts["exhaust"][k]:.2f} mm)', family='kinematics'))
    for side in SIDES:
        g = min(kin.valve_piston_gap(p, side, sy, phi, lifts[side]) .min() for sy in (1, -1))
        gi = np.minimum(*(kin.valve_piston_gap(p, side, sy, phi, lifts[side]) for sy in (1, -1)))
        j = int(np.argmin(gi))
        out.append(_c(f'valve_piston_{side}', g, p[f'{side}_piston_clearance'], '>=',
                      f'jeu vertical face de tête / calotte (poches {p["piston_pocket_depth"]:.2f} mm) ; pire φ={phi[j]:g}°',
                      family='kinematics'))
    worst = math.inf
    for side, sy in VALVES:
        pts, _, u, _ = kin.head_cloud(p, side, sy, n=48)
        moved = pts - u * p[f'{side}_max_lift']
        below = moved[moved[:, 2] < p['register_depth']]
        if len(below):
            worst = min(worst, p['bore_diameter'] / 2 - float(np.max(np.hypot(below[:, 0], below[:, 1]))))
    worst = worst if math.isfinite(worst) else p['bore_diameter'] / 2
    out.append(_c('valve_head_vs_liner_at_full_lift', worst, p['min_bore_edge_margin'], '>=',
                  'rayon max des points de tête sous le haut de chemise, pleine levée', family='kinematics'))
    full = min(kin.pair_distance_over_cycle(p, ('intake', a), ('exhaust', b), np.array([p['intake_max_lift']]),
                                            np.array([p['exhaust_max_lift']]))[0] for a in (1, -1) for b in (1, -1))
    out.append(_c('valve_valve_both_full_lift_envelope', full, p['min_valve_clearance'], '>=',
                  'enveloppe pessimiste hors cinématique (11,5 et 9,6 simultanées)', blocking=False, family='kinematics'))
    return out


def summarize(checks, cycle_evaluated=True):
    blocking = [c for c in checks if c['blocking']]
    failed = [c['check'] for c in blocking if not c['passed']]
    worst = min(blocking, key=lambda c: c['slack'])
    return {'passed': sum(c['passed'] is True for c in checks), 'failed': sum(c['passed'] is False for c in checks),
            'not_computable': [c['check'] for c in checks if c['passed'] is None],
            'blocking_failed': failed, 'min_slack': worst['slack'], 'limiting_check': worst['check'],
            'cycle_evaluated': cycle_evaluated, 'accepted': cycle_evaluated and not failed}


def evaluate(p, step_deg, force_cycle=False):
    checks = static_checks(p)
    run_cycle = force_cycle or all(c['passed'] is True for c in checks if c['blocking'])
    if run_cycle:
        checks += cycle_checks(p, step_deg)
    return checks, summarize(checks, run_cycle)
