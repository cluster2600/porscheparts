"""Equal nominal metal-volume fin trees; prescribed convection, not head CFD."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path


def validate(design):
    if set(design) != {'id', 'depth_mm', 'pitch_mm', 'edges'}:
        raise ValueError('Unexpected design fields')
    for key in ('depth_mm', 'pitch_mm'):
        if not math.isfinite(design[key]) or not 0 < design[key] <= 100:
            raise ValueError('Invalid coupon dimensions')
    seen = {(0.0, 0.0)}
    incoming = set()
    if not 1 <= len(design['edges']) <= 15:
        raise ValueError('Invalid tree size')
    for e in design['edges']:
        if set(e) != {'a', 'b', 't0_mm', 't1_mm'}:
            raise ValueError('Unexpected edge fields')
        if any(len(e[p]) != 2 for p in ('a', 'b')):
            raise ValueError('Expected X/Z points')
        values = e['a'] + e['b'] + [e['t0_mm'], e['t1_mm']]
        if any(not math.isfinite(v) for v in values):
            raise ValueError('Non-finite edge')
        a, b = tuple(e['a']), tuple(e['b'])
        if a not in seen or b in incoming or b[1] <= a[1] or b[1] > 40:
            raise ValueError('Edges must form an ordered, upward rooted tree')
        if min(e['t0_mm'], e['t1_mm']) < 1.2 or max(e['t0_mm'], e['t1_mm']) > 8:
            raise ValueError('Unresolved or out-of-range thickness')
        if max(abs(a[0]) + e['t0_mm']/2, abs(b[0]) + e['t1_mm']/2) > design['pitch_mm']/2 - 1:
            raise ValueError('Neighbor clearance envelope violated')
        incoming.add(b)
        seen.add(b)
    return design


def length(edge):
    return math.dist(edge['a'], edge['b'])


def nominal_volume(design):
    return design['depth_mm'] * sum(length(e)*(e['t0_mm']+e['t1_mm'])/2 for e in design['edges'])


def conductance(design, k, h, cells=64):
    """Exact constant-section fin transfer, midpoint subdivision of taper.

    k: W/(m K), h: W/(m2 K), return: W/K at the root above ambient.
    shortcut: junction overlap and local flow are omitted, upgrade to 3-D CHT
    before ranking actual head variants.
    """
    validate(design)
    if not math.isfinite(k) or k <= 0 or not math.isfinite(h) or h < 0:
        raise ValueError('Invalid thermal boundary')
    if type(cells) is not int or not 2 <= cells <= 4096:
        raise ValueError('Invalid taper subdivision count')
    if h == 0:
        return 0.0
    children = {}
    for e in design['edges']:
        children.setdefault(tuple(e['a']), []).append(e)
    depth = design['depth_mm']/1000

    def edge_input(e):
        ends = children.get(tuple(e['b']), [])
        downstream = sum(edge_input(c) for c in ends) if ends else h*depth*e['t1_mm']/1000
        dl = length(e)/1000/cells
        for j in reversed(range(cells)):
            t = (e['t0_mm']+(e['t1_mm']-e['t0_mm'])*(j+.5)/cells)/1000
            area, perimeter = depth*t, 2*(depth+t)
            m = math.sqrt(h*perimeter/(k*area))
            characteristic = k*area*m
            th = math.tanh(m*dl)
            downstream = characteristic*(downstream+characteristic*th)/(characteristic+downstream*th)
        return downstream

    return sum(edge_input(e) for e in children[(0.0, 0.0)])


def edge(a, b, t0, t1):
    return dict(a=list(a), b=list(b), t0_mm=t0, t1_mm=t1)


def designs():
    base = dict(id='straight', depth_mm=60.0, pitch_mm=14.0,
                edges=[edge((0, 0), (0, 28), 3.0, 3.0)])
    yield base
    for root_ratio in (1.25, 1.5, 1.75):
        yield dict(base, id=f'taper-{root_ratio}',
                   edges=[edge((0, 0), (0, 28), 3*root_ratio, 3*(2-root_ratio))])
    for split, spread, root, tip in itertools.product((.25, .4, .55, .7), (2., 3.5, 5.), (1.4, 1.8, 2.2), (.45, .6, .75)):
        junction = (0, 28*split)
        edges = [edge((0, 0), junction, root, 1),
                 edge(junction, (-spread, 28), 1, tip),
                 edge(junction, (spread, 28), 1, tip)]
        d = dict(base, id=f'leaf-{split}-{spread}-{root}-{tip}', edges=edges)
        scale = nominal_volume(base)/nominal_volume(d)
        for e in edges:
            e['t0_mm'] *= scale
            e['t1_mm'] *= scale
        yield d


def run():
    candidates, rejected = [], []
    # These are sensitivities, not properties of a selected alloy or measured air.
    scenarios = [(k, h) for k in (12., 80., 160.) for h in (40., 100., 200.)]
    base = next(designs())
    reference = [conductance(base, k, h) for k, h in scenarios]
    for design in designs():
        try:
            validate(design)
        except ValueError as error:
            rejected.append(dict(id=design['id'], reason=str(error)))
            continue
        values = [conductance(design, k, h) for k, h in scenarios]
        candidates.append(dict(design=design, nominal_volume_mm3=nominal_volume(design),
                               conductance_W_K=values,
                               worst_ratio_to_straight=min(v/r for v, r in zip(values, reference))))
    leaf = max((c for c in candidates if c['design']['id'].startswith('leaf-')),
               key=lambda c: c['worst_ratio_to_straight'])
    best = max(candidates, key=lambda c: c['worst_ratio_to_straight'])
    selected = [c for c in candidates if c['design']['id'] in {'straight', best['design']['id'], leaf['design']['id']}]
    refinement = []
    for c in selected:
        d = c['design']
        errors = [abs(conductance(d, k, h, 128)/conductance(d, k, h, 256)-1) for k, h in scenarios]
        refinement.append(dict(id=d['id'], max_relative_128_vs_256=max(errors)))
    return dict(schema='m64-bionic-fin-study/v1', status='synthetic_prescribed_h_screen_only',
                objective='maximize_worst_conductance_ratio_at_equal_nominal_fin_volume',
                scenarios=[dict(k_W_mK=k, h_W_m2K=h) for k, h in scenarios],
                best_overall_id=best['design']['id'], best_bionic_id=leaf['design']['id'],
                candidates=candidates, rejected=rejected, refinement=refinement,
                assumptions=['isothermal_root', 'uniform_prescribed_h', 'constant_ambient',
                             'linear_taper_piecewise_constant', 'adiabatic_junction_tip_faces',
                             'junction_overlap_not_subtracted_from_nominal_volume',
                             'air_direction_parallel_to_extruded_Y_channels'],
                actual_alloy=None, manufacturing_process=None, engine_heat_flux_W=None,
                fan_curve=None, air_pressure_loss_Pa=None, head_max_temperature_K=None,
                real_head_optimized=False, manufacturing_authorized=False,
                study_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New output directory')
    args = parser.parse_args()
    report = run()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'study.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    selected = {'straight', report['best_overall_id'], report['best_bionic_id']}
    for c in report['candidates']:
        if c['design']['id'] in selected:
            (args.output/(c['design']['id']+'.json')).write_text(json.dumps(c['design'], indent=2)+'\n')
    print(json.dumps(dict(best_overall=report['best_overall_id'], best_bionic=report['best_bionic_id'],
                          candidates=len(report['candidates']), rejected=len(report['rejected']))))


if __name__ == '__main__':
    main()
