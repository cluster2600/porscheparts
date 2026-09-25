"""G6 removable carrier candidate. No threads, bearing qualification or cam drive."""
import math

import cadquery as cq
import numpy as np

import layout
import rocker_geometry as rg
from cadcommon import _cyl, _v


def validate(p):
    for k, v in p.items():
        if k.startswith('carrier_') and (not math.isfinite(v) or v <= 0):
            raise ValueError('carrier dimensions must be finite and positive')
    if not (p['carrier_wall_thickness'] > 2 * p['carrier_oil_radius'] + 6 and
            p['carrier_end_y'] + p['carrier_wall_thickness'] / 2 <= p['head_block_width_y'] / 2 and
            p['carrier_mount_depth'] > 0 and p['carrier_journal_radial_clearance'] < 1):
        raise ValueError('carrier wall, head footprint or journal clearance invalid')


def axes(p):
    return {s: rg.frame(p, s, 1)[:2] for s in layout.SIDES}


def returns(p, sy):
    y, z = sy * p['carrier_end_y'], p['carrier_face_height']
    # One accessible oblique drilling connects to the existing transverse gallery.
    return _cyl([0, y, z + p['carrier_foot_height'] + 2],
                [p['oil_gallery_x'], y, p['oil_gallery_z'] - 1], p['carrier_return_radius'])


def modify_head(p, body):
    validate(p)
    z = p['carrier_face_height']
    for sy in (-1, 1):
        body = body.cut(returns(p, sy))
        for sx in (-1, 1):
            x, y = sx * p['carrier_mount_x'], sy * p['carrier_end_y']
            # Pilot envelope equals bolt major diameter, not a model of engaged threads.
            body = body.cut(_cyl([x, y, z - p['carrier_mount_depth']], [x, y, z + 1], 3.0))
    return body.clean()


def oil_tools(p, sy, side):
    pivot, cam = axes(p)[side]
    y, r = sy * p['carrier_end_y'], p['carrier_oil_radius']
    z = cam[2] - 25
    sign = -1 if side == 'intake' else 1
    outer = cam[0] + sign * (p['cam_base_circle_radius'] * .6 + 12)
    header = _cyl([outer, y, z], [pivot[0], y, z], r)
    for q in (pivot, cam):
        header = header.fuse(_cyl([q[0], y, z], [q[0], y, q[2]], r))
    return header.clean()


def parts(p):
    validate(p)
    out = {}
    ax = axes(p)
    z, foot, w = p['carrier_face_height'], p['carrier_foot_height'], p['carrier_wall_thickness']
    cam_r = p['cam_base_circle_radius'] * .6
    cap_halfwidth, cap_height = cam_r + 11, cam_r + 5
    xmin, xmax = ax['intake'][1][0] - cap_halfwidth, ax['exhaust'][1][0] + cap_halfwidth
    for sy in (-1, 1):
        tag, y = ('p' if sy > 0 else 'm'), sy * p['carrier_end_y']
        body = cq.Solid.makeBox(xmax - xmin, w, foot, cq.Vector(xmin, y - w / 2, z))
        window = p['carrier_centre_window_halfwidth']
        for side, (pivot, cam) in ax.items():
            x0, x1 = (xmin, -window) if side == 'intake' else (window, xmax)
            tower = cq.Solid.makeBox(x1 - x0, w, cam[2] + cap_height - z,
                                     cq.Vector(x0, y - w / 2, z))
            cap = cq.Solid.makeBox(2 * cap_halfwidth, w, cap_height,
                                  cq.Vector(cam[0] - cap_halfwidth, y - w / 2, cam[2]))
            tower = tower.cut(cap)
            for q, radius in ((pivot, p['rocker_pivot_radius']), (cam, cam_r)):
                bore = _cyl([q[0], y - w, q[2]], [q[0], y + w, q[2]], radius + p['carrier_journal_radial_clearance'])
                tower, cap = tower.cut(bore), cap.cut(bore)
            for dx in (-cam_r - 6, cam_r + 6):
                bx, bottom, top = cam[0] + dx, cam[2] - 12, cam[2] + cap_height
                tower = tower.cut(_cyl([bx, y, bottom], [bx, y, top], 2.5))
                cap = cap.cut(_cyl([bx, y, cam[2] - 1], [bx, y, top + 1], 2.75))
                bolt = _cyl([bx, y, bottom], [bx, y, top], 2.5).fuse(_cyl([bx, y, top], [bx, y, top + 5], 4.25))
                out[f'carrier_cap_bolt_{side}_{tag}_{"p" if dx > 0 else "m"}'] = bolt
            tower = tower.cut(oil_tools(p, sy, side))
            body = body.fuse(tower)
            out[f'carrier_cap_{side}_{tag}'] = cap.clean()
        # Head studs/nuts are installed before the carrier. This is their clearance,
        # not a claim that they remain vertically serviceable with the shafts in place.
        for sx in (-1, 1):
            xh, yh = sx * p['stud_span_x'] / 2, sy * p['stud_span_y'] / 2
            body = body.cut(_cyl([xh, yh, z - 1], [xh, yh, z + 20], 11))
            x = sx * p['carrier_mount_x']
            body = body.cut(_cyl([x, y, z - 1], [x, y, z + foot + 1], 3.3))
            body = body.cut(_cyl([x, y, z + foot], [x, y, z + 120], 7))
            bolt = _cyl([x, y, z - p['carrier_mount_depth']], [x, y, z + foot], 3)
            out[f'carrier_mount_bolt_{tag}_{sx:+d}'] = bolt.fuse(_cyl([x, y, z + foot], [x, y, z + foot + 6], 5))
        out[f'carrier_base_{tag}'] = body.cut(returns(p, sy)).clean()
    return out
