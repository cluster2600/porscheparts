"""Jumeau CAO synthétique : Soupapes, guides, sièges rapportés, coupelles."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def valve(p, side, sy, lift=0.0):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    base = c - u * lift
    r = p[f'{side}_valve_head_diameter'] / 2
    t = p['valve_head_thickness']
    headpart = cq.Solid.makeCone(r, p['guide_bore_diameter'] / 2 + 1.5, t, _v(base), _v(u))
    stem = cq.Solid.makeCylinder(p['guide_bore_diameter'] / 2 - 0.02, valve_length(p, side) - t + 0.5,
                                 _v(base + u * (t - 0.5)), _v(u))
    return headpart.fuse(stem).clean()


def guide(p, side, sy):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    top = p[f'{side}_spring_seat_axial'] + p['guide_protrusion']
    length = p[f'{side}_guide_length']
    return _tube(c + u * (top - length), u, length, p['guide_bore_diameter'] / 2, p['guide_outer_diameter'] / 2)


def seat_insert(p, side, sy):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    r = p[f'{side}_valve_head_diameter'] / 2
    return _tube(c, u, p['seat_insert_height'], p[f'{side}_throat_diameter'] / 2, r + p['seat_insert_radial_wall'])


def retainer(p, side, sy, lift=0.0):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    z = p[f'{side}_spring_seat_axial'] + p['spring_installed_height'] - lift
    return _tube(c + u * z, u, p['retainer_thickness'], p['guide_bore_diameter'] / 2, p['retainer_diameter'] / 2)
