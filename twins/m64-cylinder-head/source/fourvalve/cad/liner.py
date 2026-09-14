"""Jumeau CAO synthétique : Cylindre / chemise."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def liner(p):
    R = p['bore_diameter'] / 2
    stud_r = math.hypot(p['stud_span_x'] / 2, p['stud_span_y'] / 2) - p['stud_hole_diameter'] / 2
    r_out = min(stud_r, p['register_diameter'] / 2) - p['liner_spigot_radial_clearance']
    top = p['register_depth']
    body = _tube([0, 0, top - p['liner_length']], [0, 0, 1], p['liner_length'], R, r_out)
    groove = _tube([0, 0, top - p['gasket_thickness']], [0, 0, 1], p['gasket_thickness'] + 1, R + 1,
                   R + 1 + p['gasket_radial_width'])
    return body.cut(groove)
