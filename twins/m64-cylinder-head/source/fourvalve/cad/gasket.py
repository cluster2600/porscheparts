"""Jumeau CAO synthétique : Joint dans la gorge du cylindre."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def gasket(p):
    R = p['bore_diameter'] / 2
    return _tube([0, 0, p['register_depth'] - p['gasket_thickness']], [0, 0, 1], p['gasket_thickness'], R + 1,
                 R + 1 + p['gasket_radial_width'])
