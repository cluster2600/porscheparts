"""Culbuteur oscillant, patin sphérique et came à galet synthétisée par inversion.

Coordonnées locales (x,z) : x du pivot vers la soupape, z le long de son axe.
La loi V1 est réutilisée avec son jeu ; aucun déplacement indépendant imposé au galet.
Méthode de référence : CMU, Introduction to Mechanisms, chapitre 6.5.2–6.5.3.
"""
import math

import numpy as np

import kinematics as kin
import layout


def validate(p):
    keys = ('valve_arm', 'cam_arm', 'pad_radius', 'roller_radius', 'roller_width', 'width',
            'plate_thickness', 'plate_height', 'pivot_radius', 'boss_radius', 'pin_radius',
            'radial_clearance', 'tip_edge_margin', 'pressure_angle_limit')
    if any(not math.isfinite(p['rocker_' + k]) or p['rocker_' + k] <= 0 for k in keys):
        raise ValueError('rocker dimensions must be finite and positive')
    gap = p['rocker_radial_clearance']
    if not (p['rocker_cam_arm'] < p['rocker_valve_arm'] and
            p['cam_lobe_width'] < p['rocker_roller_width'] < p['rocker_width'] - 2 * p['rocker_plate_thickness'] and
            p['rocker_pivot_radius'] + gap < p['rocker_boss_radius'] and
            p['rocker_pin_radius'] + gap < min(p['rocker_roller_radius'], p['rocker_plate_height'] / 2) and
            p['rocker_plate_height'] / math.sqrt(2) <= p['rocker_pad_radius'] and
            p['rocker_pressure_angle_limit'] < 90):
        raise ValueError('inconsistent rocker arms, fork, bearings or pressure angle')
    laws, _ = kin.cam_laws(p)
    for s, law in laws.items():
        if p['rocker_valve_arm'] <= p[f'{s}_max_lift'] + law.lash_m * 1000:
            raise ValueError('rocker valve arm must exceed gross lift')


def rotate(points, angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.stack((c * points[..., 0] - s * points[..., 1],
                     s * points[..., 0] + c * points[..., 1]), axis=-1)


def quarter_turn(points):
    return np.stack((-points[..., 1], points[..., 0]), axis=-1)


def frame(p, side, sy):
    law = kin.cam_laws(p)[0][side]
    u = layout.axis_up(p, side)
    sign = -1 if side == 'intake' else 1
    v = sign * np.array([u[2], 0.0, -u[0]])
    tip = layout.head_centre(p, side, sy) + u * layout.valve_length(p, side)
    pivot = tip - v * p['rocker_valve_arm'] + u * (p['rocker_pad_radius'] + law.lash_m * 1000)
    cam = pivot + v * p['rocker_cam_arm'] + u * (p['cam_base_circle_radius'] + p['rocker_roller_radius'])
    return pivot, cam, v, u


def state(p, side, phi_deg):
    """Angle exact : a sin(beta) = déplacement brut ; dérivées par radian de came."""
    validate(p)
    phi = np.radians(np.atleast_1d(np.asarray(phi_deg, dtype=float)))
    if not np.all(np.isfinite(phi)):
        raise ValueError('crank angles must be finite')
    law = kin.cam_laws(p)[0][side]
    a, b = p['rocker_valve_arm'], p['rocker_cam_arm']
    s = 1000 * law.cam_derivatives(phi)
    ds, dds = 2000 * law.cam_derivatives(phi, 1), 4000 * law.cam_derivatives(phi, 2)
    root = np.sqrt(a * a - s * s)
    beta, db, ddb = np.arcsin(s / a), ds / root, dds / root + s * ds * ds / root ** 3
    co, si = np.cos(beta), np.sin(beta)
    roller = b * np.stack((co, -si), axis=-1)
    speed = b * np.stack((-si * db, -co * db), axis=-1)
    accel = b * np.stack((-co * db * db - si * ddb, si * db * db - co * ddb), axis=-1)
    return {'beta': beta, 'gross_displacement_mm': s, 'valve_lift_mm': 1000 * law.valve_lift(phi),
            'lash_mm': law.lash_m * 1000, 'tip_walk_mm': a * (1 - co),
            'roller': roller, 'roller_dtheta': speed, 'roller_ddtheta': accel}


def profile(p, side, crank_step_deg=0.5):
    if not math.isfinite(crank_step_deg) or not 0 < crank_step_deg <= 2:
        raise ValueError('profile crank step must be in (0, 2] degrees')
    count = math.ceil(720 / crank_step_deg)
    phi = np.linspace(0, 720, count, endpoint=False)
    theta = np.radians(phi / 2)
    s = state(p, side, phi)
    c = s['roller'] - np.array([p['rocker_cam_arm'], p['cam_base_circle_radius'] + p['rocker_roller_radius']])
    q = rotate(c, -theta)
    dq = rotate(s['roller_dtheta'] - quarter_turn(c), -theta)
    ddq = rotate(s['roller_ddtheta'] - 2 * quarter_turn(s['roller_dtheta']) - c, -theta)
    speed = np.linalg.norm(dq, axis=1)
    if np.any(speed < 1e-9):
        raise ValueError('singular pitch curve')
    normal = quarter_turn(dq) / speed[:, None]  # parcours horaire, normale extérieure
    curvature = (dq[:, 0] * ddq[:, 1] - dq[:, 1] * ddq[:, 0]) / speed ** 3
    if np.any(1 + p['rocker_roller_radius'] * curvature <= 0):
        raise ValueError('roller offset undercuts the pitch curve')
    tangent = rotate(np.stack((-np.sin(s['beta']), -np.cos(s['beta'])), axis=-1), -theta)
    pressure = np.degrees(np.arccos(np.clip(np.abs(np.sum(normal * tangent, axis=1)), 0, 1)))
    return {'phi_deg': phi, 'pitch': q, 'normal': normal, 'points': q - p['rocker_roller_radius'] * normal,
            'pressure_deg': pressure, 'pitch_curvature': curvature, 'state': s}


def point_to_polygon_distance(points, polygon):
    """Distance indépendante aux segments du profil ; boucle bornée, sans nouveau solveur."""
    start, edge = polygon, np.roll(polygon, -1, axis=0) - polygon
    length2 = np.sum(edge * edge, axis=1)
    if np.any(length2 <= 0):
        raise ValueError('duplicate polygon vertices')
    out = []
    for point in points:
        t = np.clip(np.sum((point - start) * edge, axis=1) / length2, 0, 1)
        out.append(np.linalg.norm(point - start - t[:, None] * edge, axis=1).min())
    return np.asarray(out)


def recover_valve_lift(p, side, phi_deg, polygon):
    """Résout le contact sur le polygone tournant, sans utiliser la levée imposée à cet angle."""
    validate(p)
    a, b, r = p['rocker_valve_arm'], p['rocker_cam_arm'], p['rocker_roller_radius']
    lash = kin.cam_laws(p)[0][side].lash_m * 1000
    upper = min(math.asin((p[f'{side}_max_lift'] + lash) / a) + .05, math.pi / 2 - 1e-6)
    following = np.roll(polygon, -1, axis=0)
    lifts = []
    for phi in np.atleast_1d(phi_deg):
        if not math.isfinite(phi):
            raise ValueError('crank angles must be finite')
        def gap(beta):
            centre = [b * math.cos(beta) - b, -b * math.sin(beta) - p['cam_base_circle_radius'] - r]
            q = rotate(np.asarray(centre), -math.radians(phi / 2))
            crossing = (polygon[:, 1] > q[1]) != (following[:, 1] > q[1])
            pa, pb = polygon[crossing], following[crossing]
            x = pa[:, 0] + (q[1] - pa[:, 1]) * (pb[:, 0] - pa[:, 0]) / (pb[:, 1] - pa[:, 1])
            inside = int(np.sum(x > q[0])) % 2
            distance = point_to_polygon_distance([q], polygon)[0]
            return (-distance if inside else distance) - r
        lo, hi = 0.0, upper
        if gap(lo) < 0:
            if gap(hi) <= 0:
                raise ValueError('cam contact cannot be bracketed')
            for _ in range(40):
                mid = (lo + hi) / 2
                if gap(mid) < 0:
                    lo = mid
                else:
                    hi = mid
        else:
            hi = 0.0
        lifts.append(max(a * math.sin((lo + hi) / 2) - lash, 0.0))
    return np.asarray(lifts)


def cam_body_clearances(p, profile):
    """Distances au contour complet : bossage et sphère majorant patin + traverse."""
    theta = np.radians(profile['phi_deg'] / 2)
    beta = profile['state']['beta']
    offset = np.array([p['rocker_cam_arm'], p['cam_base_circle_radius'] + p['rocker_roller_radius']])
    pivot = rotate(np.broadcast_to(-offset, (len(theta), 2)), -theta)
    pad = rotate(p['rocker_valve_arm'] * np.stack((np.cos(beta), -np.sin(beta)), axis=-1) - offset, -theta)
    return {'pivot_boss_mm': float(point_to_polygon_distance(pivot, profile['points']).min() - p['rocker_boss_radius']),
            'pad_and_crossbar_mm': float(point_to_polygon_distance(pad, profile['points']).min() - p['rocker_pad_radius']),
            'fork_axial_mm': (p['rocker_width'] - 2 * p['rocker_plate_thickness'] - p['cam_lobe_width']) / 2}
