#!/usr/bin/env python3
"""G6 actual CAD plus reduced thermal/mechanical screens. Writes a NEW output folder."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]
import assembly
import cadquery as cq
import carrier
import components as comp
import g6_screen
import layout
from cadcommon import _cyl


def closed_voids(shape):
    """Exact CAD exterior complement. Does NOT fill away enclosed cavities first."""
    b = shape.BoundingBox()
    outer = cq.Solid.makeBox(b.xlen + 10, b.ylen + 10, b.zlen + 10,
                            cq.Vector(b.xmin - 5, b.ymin - 5, b.zmin - 5))
    void = outer.cut(shape)
    if not assembly.brep_valid(void):
        raise ValueError('invalid BRep exterior complement')
    seed = cq.Vector(b.xmin - 4, b.ymin - 4, b.zmin - 4)
    regions = void.Solids()
    exterior = [s for s in regions if s.isInside(seed, 1e-7)]
    if len(exterior) != 1:
        raise ValueError('exterior void not uniquely identified')
    enclosed = [s.Volume() for s in regions if not s.isInside(seed, 1e-7)]
    return {'method': 'BRep_complement_connected_solids_not_voxel_fill', 'enclosed_void_volumes_mm3': enclosed,
            'no_enclosed_void_detected': not enclosed, 'powder_transport_or_support_removal_validated': False}


def overlap(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if any(getattr(ba, axis+'max') < getattr(bb, axis+'min') or getattr(bb, axis+'max') < getattr(ba, axis+'min') for axis in ('x','y','z')):
        return 0.0
    return abs(a.intersect(b).Volume())


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    p, config = g6_screen.inputs()
    shapes = assembly.parts(p, 0)
    old_head = shapes['head']
    shapes['head'] = carrier.modify_head(p, old_head)
    mounts = carrier.parts(p)
    collisions = []
    for n, s in mounts.items():
        for m, t in shapes.items():
            volume = overlap(s, t)
            if volume > 1e-5:
                collisions.append({'a': n, 'b': m, 'intersection_mm3': volume})
    names = list(mounts)
    for i, n in enumerate(names):
        for m in names[i+1:]:
            volume = overlap(mounts[n], mounts[m])
            if volume > 1e-5:
                collisions.append({'a': n, 'b': m, 'intersection_mm3': volume})
    shapes.update(mounts)
    print(json.dumps({'stage': 'CAD', 'collisions': collisions}), flush=True)
    motion_edge = max(p[s+'_valve_y'] + max(p['rocker_width']/2, p['spring_outer_diameter']/2, p[s+'_valve_head_diameter']/2) for s in layout.SIDES)
    axial_gap = p['carrier_end_y'] - p['carrier_wall_thickness']/2 - motion_edge
    voids = {n: closed_voids(shapes[n]) for n in ('head','carrier_base_p','carrier_cap_intake_p','carrier_cap_exhaust_p')}
    returns = []
    gallery = _cyl(*layout.cylinders(p)['oil_gallery'])
    for sy in (-1,1):
        returns.append({'sy':sy, 'connection_to_gallery_mm3': overlap(carrier.returns(p, sy), gallery),
                        'residual_solid_in_return_mm3': overlap(carrier.returns(p, sy), shapes['head'])})
    with patch.object(comp, 'head', return_value=shapes['head']):
        compression = assembly.compression_ratio(p)
    # Export only new geometry here. Assembly G5 geometry remains reconstructible.
    exports = ['head','carrier_base_p','carrier_cap_intake_p','carrier_cap_exhaust_p']
    for n in exports:
        cq.exporters.export(cq.Workplane().add(shapes[n]), str(out / (n+'.step')))
        cq.exporters.export(cq.Workplane().add(shapes[n]), str(out / (n+'.stl')), tolerance=.05, angularTolerance=.15)
    assembly._export(list(shapes.values()), out / 'assembly.step')
    half = cq.Solid.makeBox(1000,1000,1000,cq.Vector(-500,p['intake_valve_y'],-500))
    cut = cq.Compound.makeCompound([s.cut(half) for s in shapes.values()]).rotate((0,0,0),(1,0,0),-90)
    cq.exporters.export(cq.Workplane().add(cut), str(out/'section.svg'), opt={'projectionDir':(0,0,-1), 'showHidden':False,'strokeWidth':.15,'width':1100,'height':None})
    (out/'section.svg').write_text('\n'.join(x.rstrip() for x in (out/'section.svg').read_text().splitlines())+'\n')
    cq.exporters.export(cq.Workplane().add(cq.Compound.makeCompound(list(shapes.values()))), str(out/'assembly.svg'),
                        opt={'projectionDir':(1,-1,-.8),'showHidden':False,'strokeWidth':.25,'width':1100,'height':800})
    (out/'assembly.svg').write_text('\n'.join(x.rstrip() for x in (out/'assembly.svg').read_text().splitlines())+'\n')
    print(json.dumps({'stage':'thermal_and_mechanical'}),flush=True)
    result = {'classification':'G6_candidate_not_engine_validation', 'manufacturing_authorized':False, 'engine_start_authorized':False,
              'configuration':config, 'values':p, 'CAD_collisions':collisions,
              'BRep_valid':{n:assembly.brep_valid(s) for n,s in shapes.items()},
              'solid_counts':{n:len(s.Solids()) for n,s in shapes.items()},
              'head_volume_mm3':shapes['head'].Volume(),
              'carrier_base_volume_mm3':mounts['carrier_base_p'].Volume(),
              'head_bounds_unchanged':all(abs(getattr(shapes['head'].BoundingBox(),a)-getattr(old_head.BoundingBox(),a))<1e-6 for a in ('xmin','xmax','ymin','ymax','zmin','zmax')),
              'moving_parts_y_clearance_mm':axial_gap, 'motion_scope':'end supports separated in y from lobes/rockers/valves at every phase; journal cylinder rotation invariant',
              'oil_return_connections':returns, 'closed_void_checks':voids, 'compression':compression,
              'thermal':g6_screen.thermal(p,config),'mechanics':g6_screen.mechanics(p,config),'hot_fit_sensitivity':g6_screen.hot_fits(p),
              'limitations':['no engine-compatible chain drive or thrust/axial retention', 'carrier stiffness, cap preload, bearing films and thread pullout not qualified',
                             'no sealed cover or oil-return hoses', 'no full-head CHT/FEA or melt-pool/residual-stress simulation'],
              'software':{'cadquery':cq.__version__}}
    paths = list(HERE.glob('*.py')) + list((HERE/'cad').glob('*.py')) + [HERE/'g6-inputs.json', layout.REPO_VALVETRAIN, g6_screen.springs.CANDIDATES, Path(g6_screen.springs.__file__)]
    paths.extend(Path(result['hot_fit_sensitivity'][k]) for k in ('source_path','helper_path'))
    for k in ('source_path','helper_path'):
        result['hot_fit_sensitivity'][k]=str(Path(result['hot_fit_sensitivity'][k]).relative_to(layout.REPO))
    result['source_sha256']={str(f.relative_to(layout.REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
    result['files_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir()}
    (out/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'stage':'done','components':len(shapes),'thermal_deficit_W':result['thermal']['smallest_deficit_W']}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    run(parser.parse_args().output)
