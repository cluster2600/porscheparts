"""Jumeau CAO synthétique : Piston à bol et poches."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def piston(p, phi_deg=0.0):
    crown = float(kin.piston_crown_z(p, np.array([phi_deg]))[0])
    R = p['bore_diameter'] / 2 - 0.2
    body = cq.Solid.makeCylinder(R, p['piston_compression_height'], V(0, 0, crown - p['piston_compression_height']))
    body = body.cut(cq.Solid.makeCylinder(p['piston_bowl_diameter'] / 2, p['piston_bowl_depth'] + 1,
                                          V(0, 0, crown - p['piston_bowl_depth'])))
    if p['piston_pocket_depth'] > 0:
        for x, y, r in kin.piston_pockets(p):
            body = body.cut(cq.Solid.makeCylinder(r, p['piston_pocket_depth'] + 1, V(x, y, crown - p['piston_pocket_depth'])))
    return body.clean()
