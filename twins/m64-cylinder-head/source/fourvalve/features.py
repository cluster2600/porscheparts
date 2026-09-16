"""G2 : conduits courbes, galerie d'huile et ailettes de la culasse (numpy seul).

Activé seulement si le jeu de paramètres G2 est chargé (``port_bezier_segments`` > 0) :
sans lui, ``layout.cylinders`` et la CAO G1 restent inchangés et leurs preuves reproductibles.
Toutes ces formes sont des hypothèses de conception, jamais une géométrie maître.
"""
import numpy as np

from layout import VALVES, axis_up, head_centre


def enabled(p):
    return int(p.get('port_bezier_segments', 0)) > 0


def port_controls(p, side, sy):
    """Points de contrôle : départ tangent à l'axe de soupape, arrivée perpendiculaire à la bride."""
    c, u = head_centre(p, side, sy), axis_up(p, side)
    sign = -1.0 if side == 'intake' else 1.0
    p0 = c + u * p['throat_axial_offset']
    p3 = np.array([p[f'{side}_flange_x'], sy * p['port_flange_y_offset'], p[f'{side}_port_z']])
    p1 = p0 + u * p[f'{side}_port_start_tangent']
    p2 = p3 - np.array([sign, 0.0, 0.0]) * p[f'{side}_port_end_tangent']
    return p0, p1, p2, p3


def port_path(p, side, sy):
    """Bézier cubique de la gorge (axe de soupape) à la bride (axe x) : points et rayons."""
    n = int(p['port_bezier_segments'])
    p0, p1, p2, p3 = port_controls(p, side, sy)
    t = np.linspace(0.0, 1.0, n + 1)[:, None]
    pts = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
    r0 = p[f'{side}_throat_diameter'] / 2
    # Bride d'admission : contour non mesurable sur le scan, on garde le rayon de gorge.
    r1 = p['exhaust_flange_port_diameter'] / 2 if side == 'exhaust' else r0
    return pts, r0 + (r1 - r0) * t[:, 0]


def feature_cylinders(p, cyl):
    """Remplace chaque conduit droit par ses segments (rayon majorant) et ajoute la galerie d'huile."""
    for side, sy in VALVES:
        tag = f'{side}_{"p" if sy > 0 else "m"}'
        del cyl[f'port_{tag}']
        pts, radii = port_path(p, side, sy)
        for i in range(len(pts) - 1):
            cyl[f'port_{tag}_{i:02d}'] = (pts[i], pts[i + 1], float(max(radii[i], radii[i + 1])))
    if p.get('oil_gallery_diameter', 0) > 0:
        w = p['head_block_width_y']
        a = np.array([p['oil_gallery_x'], -w / 2 - 1.0, p['oil_gallery_z']])
        cyl['oil_gallery'] = (a, a + np.array([0.0, w + 2.0, 0.0]), p['oil_gallery_diameter'] / 2)
    return cyl


def fin_boxes(p):
    """Ailettes horizontales sur les faces ±y : (x, y, z, dx, dy, dz) par ailette."""
    boxes = []
    if int(p.get('fin_count', 0)) <= 0:
        return boxes
    x0 = p['intake_flange_x'] + p['fin_x_margin']
    x1 = p['exhaust_flange_x'] - p['fin_x_margin']
    w = p['head_block_width_y']
    for side in (-1, 1):
        for k in range(int(p['fin_count'])):
            z = p['fin_z_start'] + k * p['fin_pitch']
            if z + p['fin_thickness'] > p['carrier_face_height']:
                break
            y = w / 2 if side > 0 else -w / 2 - p['fin_depth']
            boxes.append((x0, y, z, x1 - x0, p['fin_depth'], p['fin_thickness']))
    return boxes
