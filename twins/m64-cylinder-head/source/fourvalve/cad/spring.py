"""Jumeau CAO synthétique : Ressort GSC5092 (enveloppe)."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def spring(p, side, sy, lift=0.0):
    """Enveloppe du ressort conique GSC5092 (Ø ext supposé, conicité supposée)."""
    c, u = head_centre(p, side, sy), axis_up(p, side)
    seat = c + u * p[f'{side}_spring_seat_axial']
    height = p['spring_installed_height'] - lift
    r0 = p['spring_outer_diameter'] / 2
    r1 = p['retainer_diameter'] / 2
    outer = cq.Solid.makeCone(r0, r1, height, _v(seat), _v(u))
    inner = cq.Solid.makeCone(r0 - 3.5, r1 - 3.5, height, _v(seat), _v(u))
    return outer.cut(inner)
