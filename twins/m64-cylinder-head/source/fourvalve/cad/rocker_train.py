"""Pièces articulées candidates G5 ; paliers/supports, graissage et fixation non qualifiés."""
import math

import cadquery as cq
import numpy as np

import layout
import rocker_geometry as rg
from cadcommon import _cyl, _tube, _v


def camshaft(p, side, phi_deg, crank_step_deg=0.5):
    _, centre, v, u = rg.frame(p, side, 1)
    centre[1] = 0
    xy = rg.rotate(rg.profile(p, side, crank_step_deg)['points'], math.radians(phi_deg / 2))
    width = p['cam_lobe_width']
    shaft = _cyl(centre + [0, -p['head_block_width_y'] / 2, 0],
                 centre + [0, p['head_block_width_y'] / 2, 0], p['cam_base_circle_radius'] * 0.6)
    for sy in (1, -1):
        origin = centre + [0, sy * p[f'{side}_valve_y'] - width / 2, 0]
        # Une face construite dans le repère physique évite d'inverser z sur l'autre côté.
        wire = cq.Wire.makePolygon([_v(origin + x * v + z * u) for x, z in xy], close=True)
        lobe = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, width, 0))
        shaft = shaft.fuse(lobe)
    return shaft.clean()


def moving_parts(p, side, sy, phi_deg):
    pivot, _, v, u = rg.frame(p, side, sy)
    beta = float(rg.state(p, side, phi_deg)['beta'][0])
    direction = math.cos(beta) * v - math.sin(beta) * u
    normal = math.sin(beta) * v + math.cos(beta) * u
    a, b = p['rocker_valve_arm'], p['rocker_cam_arm']
    width, thickness = p['rocker_width'], p['rocker_plate_thickness']
    halfheight, gap = p['rocker_plate_height'] / 2, p['rocker_radial_clearance']
    roller_centre, pad = pivot + b * direction, pivot + a * direction
    body = _tube(pivot + [0, -width / 2, 0], [0, 1, 0], width,
                 p['rocker_pivot_radius'] + gap, p['rocker_boss_radius'])
    for y in (-width / 2, width / 2 - thickness):
        origin = pivot + [0, y, 0]
        points = [origin + x * direction + z * normal for x, z in
                  ((0, -halfheight), (a, -halfheight), (a, halfheight), (0, halfheight))]
        wire = cq.Wire.makePolygon([_v(q) for q in points], close=True)
        body = body.fuse(cq.Solid.extrudeLinear(wire, [], cq.Vector(0, thickness, 0)))
    # Traverse reliant les joues au patin ; sa section reste dans le disque du patin.
    origin = pad + [0, -width / 2, 0]
    wire = cq.Wire.makePolygon([_v(origin + x * direction + z * normal) for x, z in
                               ((-halfheight, -halfheight), (halfheight, -halfheight),
                                (halfheight, halfheight), (-halfheight, halfheight))], close=True)
    body = body.fuse(cq.Solid.extrudeLinear(wire, [], cq.Vector(0, width, 0)))
    body = body.fuse(cq.Solid.makeSphere(p['rocker_pad_radius'], _v(pad), angleDegrees1=-90))
    # Les joues fusionnées ne doivent pas reboucher les deux axes.
    body = body.cut(_cyl(pivot + [0, -width, 0], pivot + [0, width, 0], p['rocker_pivot_radius'] + gap))
    body = body.cut(_cyl(roller_centre + [0, -width, 0], roller_centre + [0, width, 0], p['rocker_pin_radius'] + gap))
    rw = p['rocker_roller_width']
    roller = _tube(roller_centre + [0, -rw / 2, 0], [0, 1, 0], rw,
                   p['rocker_pin_radius'] + gap, p['rocker_roller_radius'])
    pin = _cyl(roller_centre + [0, -width / 2, 0], roller_centre + [0, width / 2, 0], p['rocker_pin_radius'])
    return {'rocker': body.clean(), 'roller': roller, 'roller_pin': pin}


def parts(p, phi_deg):
    rg.validate(p)
    out = {}
    for side in layout.SIDES:
        out[f'camshaft_{side}'] = camshaft(p, side, phi_deg)
        pivot = rg.frame(p, side, 1)[0]
        pivot[1] = 0
        out[f'rocker_shaft_{side}'] = _cyl(pivot + [0, -p['head_block_width_y'] / 2, 0],
                                          pivot + [0, p['head_block_width_y'] / 2, 0], p['rocker_pivot_radius'])
        for sy in (1, -1):
            tag = f'{side}_{"p" if sy > 0 else "m"}'
            out.update({f'{name}_{tag}': shape for name, shape in moving_parts(p, side, sy, phi_deg).items()})
    return out
