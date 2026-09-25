"""Dérivations et primitives géométriques communes (repère : plan d'étanchéité, numpy seul)."""
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parents[3]
REPO_VALVETRAIN = REPO / 'twins/m64-cylinder-head/source/valvetrain/valvetrain.py'

DERIVED = ('intake_axis_angle', 'exhaust_axis_angle', 'intake_valve_y', 'exhaust_valve_y', 'intake_valve_x',
           'exhaust_valve_x', 'roof_ridge_height', 'intake_throat_diameter', 'exhaust_throat_diameter',
           'plug_1_tilt', 'plug_1_azimuth', 'plug_2_tilt', 'plug_2_azimuth', 'intake_spring_seat_axial',
           'exhaust_spring_seat_axial', 'spring_pocket_diameter')
SIDES = ('intake', 'exhaust')
VALVES = tuple((s, sy) for s in SIDES for sy in (1, -1))
PLUGS = (1, 2)


def derive(values, fixed=None):
    """Calcule les dérivés ; un nom présent dans ``fixed`` garde la valeur imposée (itération)."""
    p = dict(values)
    fixed = dict(fixed or {})
    p.update(fixed)

    def put(name, fn):
        if name not in fixed:
            p[name] = float(fn())

    L = p['min_ligament']
    put('intake_axis_angle', lambda: p['scan_valve_1_axis_angle'])
    put('exhaust_axis_angle', lambda: p['scan_valve_2_axis_angle'])
    for side, sign in (('intake', -1), ('exhaust', 1)):
        d = p[f'{side}_valve_head_diameter']
        th = math.radians(p[f'{side}_axis_angle'])
        put(f'{side}_valve_y', lambda d=d: d / 2 + L / 2 + p['valve_y_extra'] / 2)
        put(f'{side}_valve_x', lambda d=d, th=th, sign=sign: sign * (d / 2 * math.cos(th) + L / 2))
        put(f'{side}_throat_diameter', lambda d=d: p['throat_ratio'] * d)
        put(f'{side}_spring_seat_axial', lambda side=side: p[f'{side}_valve_length_993'] + p['valve_length_delta']
            - p['spring_installed_height'] - p['valve_tip_allowance'])

    def ridge():
        rise = []
        for side in SIDES:
            th = math.radians(p[f'{side}_axis_angle'])
            rise.append((abs(p[f'{side}_valve_x']) + p[f'{side}_valve_head_diameter'] / 2 * math.cos(th)) * math.tan(th))
        return p['register_depth'] + p['min_roof_edge_height'] + max(rise)

    put('roof_ridge_height', ridge)
    for k in PLUGS:
        put(f'plug_{k}_tilt', lambda k=k: 90.0 - p[f'plug_{k}_angle_to_plane'])

        def az(k=k):
            s = 1.0 if -p[f'plug_{k}_scan_uz'] > 0 else -1.0
            return math.degrees(math.atan2(-s * p[f'plug_{k}_scan_ux'], -s * p[f'plug_{k}_scan_uy']))

        put(f'plug_{k}_azimuth', az)
    put('spring_pocket_diameter', lambda: p['spring_outer_diameter'] + 2 * p['spring_pocket_radial_clearance'])
    return p


# ------------------------------------------------------------------ primitives
def axis_up(p, side):
    th = math.radians(p[f'{side}_axis_angle'])
    return np.array([(-1.0 if side == 'intake' else 1.0) * math.sin(th), 0.0, math.cos(th)])


def roof_z(p, x):
    h = p['roof_ridge_height']
    zi = h + x * math.tan(math.radians(p['intake_axis_angle']))
    ze = h - x * math.tan(math.radians(p['exhaust_axis_angle']))
    return max(p['register_depth'], min(zi, ze))


def head_centre(p, side, sy):
    x = p[f'{side}_valve_x']
    th = math.radians(p[f'{side}_axis_angle'])
    return np.array([x, sy * p[f'{side}_valve_y'], p['roof_ridge_height'] - abs(x) * math.tan(th)])


def ellipse_points(cx, cy, semi_x, semi_y, n=240):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.column_stack((cx + semi_x * np.cos(t), cy + semi_y * np.sin(t)))


def head_projection(p, side, sy, n=240):
    d = p[f'{side}_valve_head_diameter']
    th = math.radians(p[f'{side}_axis_angle'])
    return ellipse_points(p[f'{side}_valve_x'], sy * p[f'{side}_valve_y'], d / 2 * math.cos(th), d / 2, n)


def plug_direction(p, k):
    t, a = math.radians(p[f'plug_{k}_tilt']), math.radians(p[f'plug_{k}_azimuth'])
    return np.array([math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t)])


def plug_opening(p, k):
    """Intersection de l'axe de bougie (point au plan d'étanchéité) avec le toit de chambre."""
    p0 = np.array([p[f'plug_{k}_px'], p[f'plug_{k}_py'], 0.0])
    d = plug_direction(p, k)
    lo, hi = 0.0, 400.0
    for _ in range(60):
        mid = (lo + hi) / 2
        q = p0 + d * mid
        lo, hi = (mid, hi) if q[2] < roof_z(p, q[0]) else (lo, mid)
    return p0 + d * hi, d


def plug_open_radius(p, k):
    """Rayon de l'empreinte du puits sur le toit (majoré par 1/cos de l'inclinaison)."""
    return p['spark_plug_bore_diameter'] / 2 / max(math.cos(math.radians(p[f'plug_{k}_tilt'])), 0.2)


def plug_envelope_cylinders(p, k):
    """Enveloppes communes CAO/contrôles ; l'hexagone est majoré par son cercle circonscrit."""
    o, d = plug_opening(p, k)
    reach = p['plug_thread_reach']
    seal_top = reach + p['plug_seal_height']
    hex_top = seal_top + p['plug_hex_height']
    spans = {'thread': (0, reach, p['spark_plug_bore_diameter']),
             'seal': (reach, seal_top, p['plug_seal_diameter']),
             'hex': (seal_top, hex_top, p['plug_hex_across_flats'] / math.cos(math.pi / 6)),
             'insulator': (hex_top, hex_top + p['plug_insulator_height'], p['plug_insulator_diameter']),
             'tip': (-p['plug_tip_projection'], 0, p['plug_tip_diameter'])}
    return {name: (o + d * a, o + d * b, dia / 2) for name, (a, b, dia) in spans.items()}


def valve_length(p, side):
    return p[f'{side}_valve_length_993'] + p['valve_length_delta']


def seat_contact(p, side):
    """Rayons et positions axiales communs aux deux faces concordantes, sans ajustement caché."""
    angle, z0 = p['seat_face_angle'], p['valve_margin_height']
    w, relief = p[f'{side}_seat_contact_radial_width'], p['seat_entry_radial_relief']
    if not all(math.isfinite(v) for v in (angle, z0, w, relief)) or not 0 < angle < 90 or min(z0, w, relief) <= 0:
        raise ValueError('seat contact dimensions must be finite and positive, angle strictly between 0 and 90')
    r0 = p[f'{side}_valve_head_diameter'] / 2
    r1, z1 = r0 - w, z0 + w * math.tan(math.radians(angle))
    if (z1 >= min(p['seat_insert_height'], p['valve_head_thickness']) or
            r1 <= max(p[f'{side}_throat_diameter'] / 2, p['guide_bore_diameter'] / 2 + 1.5) or
            relief >= p['seat_insert_radial_wall']):
        raise ValueError('seat contact exceeds the head, throat or insert envelope')
    return r0, r1, z0, z1


def cam_axis_point(p, side):
    if 'rocker_valve_arm' in p:
        import rocker_geometry
        centre = rocker_geometry.frame(p, side, 1)[1]
        centre[1] = 0.0
        return centre
    c = head_centre(p, side, 1)
    c[1] = 0.0
    return c + axis_up(p, side) * (valve_length(p, side) + p['follower_stack_axial'] + p['cam_base_circle_radius'])


def segment_distance(p1, q1, p2, q2):
    """Distance minimale entre segments 3D (Ericson, Real-Time Collision Detection §5.1.9)."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = float(d1 @ d1), float(d2 @ d2), float(d2 @ r)
    if a <= 1e-12 and e <= 1e-12:
        return float(np.linalg.norm(r))
    if a <= 1e-12:
        s, t = 0.0, min(max(f / e, 0.0), 1.0)
    else:
        c = float(d1 @ r)
        if e <= 1e-12:
            t, s = 0.0, min(max(-c / a, 0.0), 1.0)
        else:
            b = float(d1 @ d2)
            denom = a * e - b * b
            s = min(max((b * f - c * e) / denom, 0.0), 1.0) if denom > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, min(max(-c / a, 0.0), 1.0)
            elif t > 1:
                t, s = 1.0, min(max((b - c) / a, 0.0), 1.0)
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def cylinders(p):
    """Cylindres fonctionnels de la culasse : nom -> (p, q, rayon)."""
    top = p['carrier_face_height']
    cyl = {}
    for side, sy in VALVES:
        tag = f'{side}_{"p" if sy > 0 else "m"}'
        c, u = head_centre(p, side, sy), axis_up(p, side)
        seat = p[f'{side}_spring_seat_axial']
        radius = p['spring_pocket_diameter'] / 2
        # Tout le disque terminal doit dépasser la face, pas seulement son centre.
        axial_top = max(seat + 1.0, (top + 5 + radius * math.hypot(*u[:2]) - c[2]) / u[2])
        cyl[f'pocket_{tag}'] = (c + u * seat, c + u * axial_top, radius)
        g_top = seat + p['guide_protrusion']
        cyl[f'guide_{tag}'] = (c + u * (g_top - p[f'{side}_guide_length']), c + u * seat,
                               p['guide_head_bore_diameter'] / 2)
        start = c + u * p['throat_axial_offset']
        flange = np.array([p[f'{side}_flange_x'], 0.0, p[f'{side}_port_z']])
        cyl[f'port_{tag}'] = (start, flange, p[f'{side}_throat_diameter'] / 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            xy = (sx * p['stud_span_x'] / 2, sy * p['stud_span_y'] / 2)
            cyl[f'stud_{sx:+d}{sy:+d}'] = (np.array([*xy, -5.0]), np.array([*xy, top + 5]), p['stud_hole_diameter'] / 2)
    for k in PLUGS:
        o, d = plug_opening(p, k)
        s_top = max((top + 5 - o[2]) / max(d[2], 0.2), 1.0)
        cyl[f'plug_{k}'] = (o - d * 1.0, o + d * s_top, p['spark_plug_bore_diameter'] / 2)
        if 'plug_thread_reach' in p:
            dimensions = [v for name, v in p.items() if name.startswith('plug_') and
                          name.split('_')[1] in ('thread', 'hex', 'seal', 'insulator', 'tip', 'socket')]
            if any(not math.isfinite(v) or v <= 0 for v in dimensions):
                raise ValueError('spark plug envelope dimensions must be finite and positive')
            if p['plug_thread_reach'] >= s_top or p['plug_seal_diameter'] <= p['spark_plug_bore_diameter']:
                raise ValueError('spark plug seat must lie within the well and surround its thread')
            if p['plug_socket_diameter'] <= max(p['plug_seal_diameter'], p['plug_insulator_diameter'],
                                                p['plug_hex_across_flats'] / math.cos(math.pi / 6)):
                raise ValueError('spark plug socket must clear the seal, hex corners and insulator')
            cyl[f'plug_{k}_socket'] = (o + d * p['plug_thread_reach'], o + d * s_top,
                                      p['plug_socket_diameter'] / 2)
    if int(p.get('port_bezier_segments', 0)) > 0:
        import features  # G2 seulement : G1 garde ses conduits droits et ses preuves
        cyl = features.feature_cylinders(p, cyl)
    return cyl
