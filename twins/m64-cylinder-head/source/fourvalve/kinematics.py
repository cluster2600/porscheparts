"""Cinématique 720° de l'assemblage : levées V1, piston bielle-manivelle, distances analytiques."""
import copy
import importlib.util
import math
import sys

import numpy as np

from layout import REPO_VALVETRAIN, axis_up, head_centre  # noqa: F401  (REPO_VALVETRAIN défini ci-dessous)


def _load_v1():
    name = 'm64_valvetrain_v1'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, REPO_VALVETRAIN)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def v1():
    return _load_v1()


def cam_laws(p):
    vt = v1()
    params = vt.default_parameters()
    laws = {}
    for side in ('intake', 'exhaust'):
        vp = copy.deepcopy(params[side])
        vp['max_lift_mm']['value'] = p[f'{side}_max_lift']
        vp['centreline_crank_deg']['value'] = vp['centreline_crank_deg']['value'] - p[f'{side}_cam_advance']
        laws[side] = vt.CamLaw.from_params(vp)
    return laws, params


def lift_table(p, step_deg):
    phi = np.arange(0.0, 720.0, step_deg)
    laws, _ = cam_laws(p)
    return phi, {s: laws[s].valve_lift(np.radians(phi)) * 1e3 for s in laws}


def piston_crown_z(p, phi_deg):
    drop = v1().piston_drop(np.radians(phi_deg), p['crank_stroke'] * 1e-3, p['conrod_length'] * 1e-3) * 1e3
    return p['register_depth'] - p['deck_clearance'] - drop


def head_cloud(p, side, sy, rings=(1.0, 0.66, 0.33), n=24, levels=None):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    e1 = np.array([u[2], 0.0, -u[0]])
    e2 = np.cross(u, e1)
    r = p[f'{side}_valve_head_diameter'] / 2
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    levels = (0.0, p['valve_head_thickness']) if levels is None else levels
    pts = [c + u * lv + (np.outer(np.cos(t), e1) + np.outer(np.sin(t), e2)) * r * f for lv in levels for f in rings]
    pts += [(c + u * lv)[None, :] for lv in levels]
    return np.vstack(pts), c, u, r


def _penetrates(pts, c, u, r, h, w):
    """pts (N,3) déplacés de -w_k (K,3) relativement au cylindre (c,u,r,h) : bool (K,)."""
    rel = (pts - c)[None, :, :] - w[:, None, :]
    ax = rel @ u
    rad2 = np.einsum('kni,kni->kn', rel, rel) - ax ** 2
    return np.any((ax >= 0) & (ax <= h) & (rad2 <= r * r), axis=1)


def pair_distance_over_cycle(p, a, b, la, lb, chunk=120):
    """Distance minimale tête a / tête b pour chaque angle (0 si pénétration). la, lb : levées (K,)."""
    # 36 points par cercle, 4 rayons : l'écart d'échantillonnage est recoupé par la distance BRep (run.py).
    pa, ca, ua, ra = head_cloud(p, *a, rings=(1.0, 0.75, 0.5, 0.25), n=36)
    pb, cb, ub, rb = head_cloud(p, *b, rings=(1.0, 0.75, 0.5, 0.25), n=36)
    h = p['valve_head_thickness']
    w = np.outer(la, ua) - np.outer(lb, ub)          # déplacement relatif de a par rapport à b
    delta = (pa[:, None, :] - pb[None, :, :]).reshape(-1, 3)
    d0 = np.einsum('ij,ij->i', delta, delta)
    out = np.empty(len(la))
    for s in range(0, len(la), chunk):
        wk = w[s:s + chunk]
        d2 = d0[:, None] - 2 * delta @ wk.T + np.einsum('ij,ij->i', wk, wk)[None, :]
        out[s:s + chunk] = np.sqrt(np.maximum(d2.min(axis=0), 0.0))
    # pénétration : points de a dans b (a déplacé de -la·ua, b de -lb·ub)
    pen = _penetrates(pa, cb, ub, rb, h, w) | _penetrates(pb, ca, ua, ra, h, -w)
    out[pen] = 0.0
    return out


def piston_pockets(p):
    """Poches du piston : liste (x, y, rayon) ; centre = axe de soupape au plan de calotte au PMH."""
    z_tdc = p['register_depth'] - p['deck_clearance']
    out = []
    for side, sy in (('intake', 1), ('intake', -1), ('exhaust', 1), ('exhaust', -1)):
        c, u = head_centre(p, side, sy), axis_up(p, side)
        t = (z_tdc - c[2]) / u[2]
        q = c + u * t
        out.append((q[0], q[1], p[f'{side}_valve_head_diameter'] / 2 + p['piston_pocket_radial_clearance']))
    return out


def crown_depression(p, xy):
    depth = np.zeros(xy.shape[:-1])
    if p['piston_pocket_depth'] > 0:
        for x, y, r in piston_pockets(p):
            inside = (xy[..., 0] - x) ** 2 + (xy[..., 1] - y) ** 2 <= r * r
            depth = np.where(inside, np.maximum(depth, p['piston_pocket_depth']), depth)
    inside = xy[..., 0] ** 2 + xy[..., 1] ** 2 <= (p['piston_bowl_diameter'] / 2) ** 2
    return np.where(inside, np.maximum(depth, p['piston_bowl_depth']), depth)


def valve_piston_gap(p, side, sy, phi, lift):
    """Jeu vertical minimal face de tête / calotte (avec poches et bol) pour chaque angle."""
    pts, _, u, _ = head_cloud(p, side, sy, rings=(1.0, 0.8, 0.6, 0.4, 0.2), n=48, levels=(0.0,))
    moved = pts[None, :, :] - np.outer(lift, u)[:, None, :]
    surface = piston_crown_z(p, phi)[:, None] - crown_depression(p, moved[..., :2])
    return (moved[..., 2] - surface).min(axis=1)
