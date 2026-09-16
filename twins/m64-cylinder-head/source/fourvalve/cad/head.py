"""Jumeau CAO synthétique : Culasse 4 soupapes / 2 bougies."""
from cadcommon import *  # noqa: F401,F403
from cadcommon import V, _cyl, _halfspace, _tube, _v, cq, math, np, kin  # noqa: F401
from layout import PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length  # noqa: F401


def head(p):
    top, w = p['carrier_face_height'], p['head_block_width_y']
    x0, x1 = p['intake_flange_x'], p['exhaust_flange_x']
    body = cq.Solid.makeBox(x1 - x0, w, top, V(x0, -w / 2, 0))
    body = body.cut(cq.Solid.makeCylinder(p['register_diameter'] / 2, p['register_depth'] + 1, V(0, 0, -1)))
    h = p['roof_ridge_height']
    chamber = cq.Solid.makeCylinder(p['bore_diameter'] / 2, h + 2, V(0, 0, -1))
    chamber = chamber.intersect(_halfspace(-p['intake_axis_angle'], h)).intersect(_halfspace(p['exhaust_axis_angle'], h))
    body = body.cut(chamber)
    cyl = cylinders(p)
    for side, sy in VALVES:
        c, u = head_centre(p, side, sy), axis_up(p, side)
        r_ins = p[f'{side}_valve_head_diameter'] / 2 + p['seat_insert_radial_wall']
        body = body.cut(cq.Solid.makeCylinder(r_ins, p['seat_insert_height'] + 1, _v(c - u), _v(u)))
        tag = f'{side}_{"p" if sy > 0 else "m"}'
        body = body.cut(cq.Solid.makeCylinder(p[f'{side}_throat_diameter'] / 2, p['throat_axial_offset'] + 2, _v(c), _v(u)))
        if f'port_{tag}' in cyl:
            start, flange, r = cyl[f'port_{tag}']
            d = flange - start
            body = body.cut(_cyl(start, flange + d / np.linalg.norm(d) * 10, r))
        else:
            # G2 : tronçons allongés d'un rayon à chaque bout, fusionnés en UN outil, puis une seule
            # découpe. Les sphères de jonction laissaient deux éclats (129 mm³ et 0) ; un loft de
            # cercles s'inversait (volume négatif) ; couper tronçon par tronçon donnait 10 solides.
            tool = None
            for name in sorted(k for k in cyl if k.startswith(f'port_{tag}_')):
                a, b, r = cyl[name]
                d = (b - a) / np.linalg.norm(b - a)
                piece = _cyl(a - d * r, b + d * r, r)
                tool = piece if tool is None else tool.fuse(piece)
            body = body.cut(tool.clean())
        g0, g1, rg = cyl[f'guide_{tag}']
        body = body.cut(_cyl(g0, g1, rg)).cut(_cyl(c, g0, p['guide_bore_diameter'] / 2 + 0.5))
        k0, k1, rk = cyl[f'pocket_{tag}']
        body = body.cut(_cyl(k0, k1, rk))
    ex = np.array([1.0, 0, 0])
    body = body.cut(_cyl([x1 - 15, 0, p['exhaust_port_z']], [x1 + 5, 0, p['exhaust_port_z']], p['exhaust_flange_port_diameter'] / 2))
    body = body.cut(_cyl([x0 + 15, 0, p['intake_port_z']], [x0 - 5, 0, p['intake_port_z']], p['intake_throat_diameter'] / 2))
    del ex
    for k in PLUGS:
        a, b, r = cyl[f'plug_{k}']
        body = body.cut(_cyl(a, b, r))
    for name, (a, b, r) in cyl.items():
        if name.startswith('stud_'):
            body = body.cut(_cyl(a, b, r))
    if 'oil_gallery' in cyl:
        body = body.cut(_cyl(*cyl['oil_gallery']))
    import features
    for x, y, z, dx, dy, dz in features.fin_boxes(p):
        body = body.fuse(cq.Solid.makeBox(dx, dy, dz, V(x, y, z)))
    return body.clean()
