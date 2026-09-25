"""Jumeau CAO synthétique : Soupapes, guides, sièges rapportés, coupelles."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401
from layout import seat_contact


def _revolve_profile(points, centre, axis):
    plane = cq.Plane(origin=_v(centre), xDir=V(axis[2], 0, -axis[0]), normal=V(0, -1, 0))
    return cq.Workplane(plane).polyline(points).close().revolve(360, (0, 0), (0, 1)).val()


def valve(p, side, sy, lift=0.0):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    base = c - u * lift
    r = p[f'{side}_valve_head_diameter'] / 2
    t = p['valve_head_thickness']
    if 'seat_face_angle' in p:
        r0, r1, z0, z1 = seat_contact(p, side)
        stem_r = p['guide_bore_diameter'] / 2 - 0.02
        return _revolve_profile([(0, 0), (r0, 0), (r0, z0), (r1, z1),
                                 (p['guide_bore_diameter'] / 2 + 1.5, t), (stem_r, t),
                                 (stem_r, valve_length(p, side)), (0, valve_length(p, side))], base, u)
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
    if 'seat_face_angle' in p:
        r0, r1, z0, z1 = seat_contact(p, side)
        h, outer = p['seat_insert_height'], r + p['seat_insert_radial_wall']
        return _revolve_profile([(r0 + p['seat_entry_radial_relief'], 0), (r0, z0), (r1, z1),
                                 (p[f'{side}_throat_diameter'] / 2, h), (outer, h), (outer, 0)], c, u)
    return _tube(c, u, p['seat_insert_height'], p[f'{side}_throat_diameter'] / 2, r + p['seat_insert_radial_wall'])


def retainer(p, side, sy, lift=0.0):
    c, u = head_centre(p, side, sy), axis_up(p, side)
    z = p[f'{side}_spring_seat_axial'] + p['spring_installed_height'] - lift
    return _tube(c + u * z, u, p['retainer_thickness'], p['guide_bore_diameter'] / 2, p['retainer_diameter'] / 2)
