"""Jumeau CAO synthétique : Goujons de culasse (motif 935)."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def studs(p):
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(cq.Solid.makeCylinder(p['stud_rod_diameter'] / 2, p['liner_length'] + p['carrier_face_height'] + 10,
                                             V(sx * p['stud_span_x'] / 2, sy * p['stud_span_y'] / 2, -p['liner_length'])))
    return cq.Compound.makeCompound(out)
