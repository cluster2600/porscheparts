"""Jumeau CAO synthétique : Arbres à cames (loi V1) et commande simplifiée."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def camshaft(p, side, phi_deg=0.0):
    laws, _ = kin.cam_laws(p)
    axis = cam_axis_point(p, side)
    u = axis_up(p, side)
    down = -u
    base = p['cam_base_circle_radius']
    width = p['cam_lobe_width']
    w = p['head_block_width_y']
    shaft = cq.Solid.makeCylinder(base * 0.6, w, _v(axis + np.array([0, -w / 2, 0])), V(0, 1, 0))
    psi = np.linspace(0, 2 * math.pi, 60, endpoint=False)
    lift = laws[side].cam_derivatives(np.radians(phi_deg) + 2 * psi) * 1e3
    pts = [(float((base + l) * math.cos(a)), float((base + l) * math.sin(a))) for a, l in zip(psi, lift)]
    out = shaft
    for sy in (1, -1):
        origin = axis + np.array([0, sy * p[f'{side}_valve_y'] - width / 2, 0])
        plane = cq.Plane(origin=tuple(float(x) for x in origin), xDir=tuple(float(x) for x in down), normal=(0, 1, 0))
        lobe = cq.Workplane(plane).polyline(pts).close().extrude(width).val()
        out = out.fuse(lobe)
    return out.clean()


def follower(p, side, sy, lift=0.0):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    tip = valve_length(p, side) - lift
    return cq.Solid.makeCylinder(6.0, p['follower_stack_axial'], _v(c + u * tip), _v(u))
