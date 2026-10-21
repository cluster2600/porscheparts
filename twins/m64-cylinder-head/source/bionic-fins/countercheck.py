"""2-D finite-volume check of fused fin sections with prescribed convection."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

import study


def polygons(design):
    result = []
    for e in design['edges']:
        a, b = np.array(e['a']), np.array(e['b'])
        delta = b-a
        normal = np.array([delta[1], -delta[0]])/np.linalg.norm(delta)
        result.append([a-normal*e['t0_mm']/2, b-normal*e['t1_mm']/2,
                       b+normal*e['t1_mm']/2, a+normal*e['t0_mm']/2])
    return result


def union_area(design):
    """Integrate piecewise-linear merged scanline intervals, including forks."""
    lines, breaks = [], set()
    for polygon in polygons(design):
        for a, b in zip(polygon, polygon[1:]+polygon[:1]):
            breaks.update((float(a[1]), float(b[1])))
            if a[1] != b[1]:
                slope = (b[0]-a[0])/(b[1]-a[1])
                lines.append((slope, a[0]-slope*a[1], min(a[1], b[1]), max(a[1], b[1])))
    for i, first in enumerate(lines):
        for second in lines[i+1:]:
            if abs(first[0]-second[0]) > 1e-12:
                z = (second[1]-first[1])/(first[0]-second[0])
                if max(first[2], second[2]) < z < min(first[3], second[3]):
                    breaks.add(float(z))

    def width(z):
        intervals = []
        for polygon in polygons(design):
            crossings = []
            for a, b in zip(polygon, polygon[1:]+polygon[:1]):
                if min(a[1], b[1]) < z < max(a[1], b[1]):
                    crossings.append(a[0]+(b[0]-a[0])*(z-a[1])/(b[1]-a[1]))
            if crossings:
                intervals.append((min(crossings), max(crossings)))
        total, right = 0.0, -math.inf
        for a, b in sorted(intervals):
            total += max(0.0, b-max(a, right))
            right = max(right, b)
        return total

    ordered = sorted(breaks)
    return sum((b-a)*width((a+b)/2) for a, b in zip(ordered, ordered[1:]))


def normalize(design, target=84.0):
    d = copy.deepcopy(design)
    if abs(union_area(d)-target) < 1e-9:
        study.validate(d)
        return d
    left, right = .5, 2.0
    for _ in range(45):
        scale = (left+right)/2
        for orig, new in zip(design['edges'], d['edges']):
            for key in ('t0_mm', 't1_mm'):
                new[key] = orig[key]*scale
        if union_area(d) < target:
            left = scale
        else:
            right = scale
    study.validate(d)
    if abs(union_area(d)/target-1) > 1e-9:
        raise ValueError('Equal fused volume normalization failed')
    return d


def exterior_segments(design):
    """Clip each trapezoid boundary by other trapezoids; keep exposed lengths."""
    shapes = polygons(design)
    def inside(point, polygon):
        signs = [(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
                 for a, b in zip(polygon, polygon[1:]+polygon[:1])]
        return all(s > 1e-9 for s in signs) or all(s < -1e-9 for s in signs)
    result = []
    for i, polygon in enumerate(shapes):
        for a, b in zip(polygon, polygon[1:]+polygon[:1]):
            delta = b-a
            breaks = {0., 1.}
            for j, other in enumerate(shapes):
                if j == i:
                    continue
                for c, d in zip(other, other[1:]+other[:1]):
                    matrix = np.column_stack((delta, c-d))
                    if abs(np.linalg.det(matrix)) < 1e-12:
                        continue
                    t, u = np.linalg.solve(matrix, c-a)
                    if 0 < t < 1 and 0 <= u <= 1:
                        breaks.add(float(t))
            values = sorted(breaks)
            for left, right in zip(values, values[1:]):
                middle = a+delta*(left+right)/2
                if not any(inside(middle, other) for j, other in enumerate(shapes) if i != j):
                    start, end = a+delta*left, a+delta*right
                    if max(start[1], end[1]) > 1e-9:
                        result.append((start, end))
    return result


def mask(design, step):
    if not math.isfinite(step) or step < .05 or step > .5 or abs(round(14/step)-14/step) > 1e-6:
        raise ValueError('Invalid grid step')
    # Align the straight 3-mm reference with cell faces, never cell centres.
    xorigin = -7+(0 if round(3/step) % 2 else step/2)
    x, z = np.meshgrid(np.arange(xorigin, 7, step), np.arange(step/2, 32, step))
    solid = np.zeros(x.shape, dtype=bool)
    for e in design['edges']:
        a, b = np.array(e['a']), np.array(e['b'])
        delta = b-a
        length = np.linalg.norm(delta)
        axis = delta/length
        s = (x-a[0])*axis[0]+(z-a[1])*axis[1]
        n = (x-a[0])*axis[1]-(z-a[1])*axis[0]
        thick = e['t0_mm']+(e['t1_mm']-e['t0_mm'])*s/length
        solid |= (s >= 0) & (s <= length) & (np.abs(n) <= thick/2)
    return solid


def solve(design, k, h, step=.2):
    study.validate(design)
    if not math.isfinite(k) or k <= 0 or not math.isfinite(h) or h < 0:
        raise ValueError('Invalid thermal boundary')
    solid = mask(design, step)
    count = int(solid.sum())
    ids = np.full(solid.shape, -1, dtype=int)
    ids[solid] = np.arange(count)
    depth, dx = design['depth_mm']/1000, step/1000
    diagonal = np.full(count, 2*h*dx*dx)
    sink = diagonal.copy()
    rhs, root_g = np.zeros(count), np.zeros(count)
    rows, cols, values = [], [], []
    conduct = k*depth
    boundary = exterior_segments(design)
    starts = np.array([a for a, b in boundary])
    deltas = np.array([b-a for a, b in boundary])
    lengths2 = (deltas*deltas).sum(axis=1)
    normal_metric = np.sqrt(lengths2)/np.abs(deltas).sum(axis=1)
    convection_area = 2*count*dx*dx
    xorigin = -7+(0 if round(3/step) % 2 else step/2)
    for iz, ix in zip(*np.where(solid)):
        i = ids[iz, ix]
        for dz, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nz, nx = iz+dz, ix+dy
            if nz < 0:
                root_g[i] += 2*conduct
                rhs[i] += 2*conduct
                diagonal[i] += 2*conduct
            elif 0 <= nz < solid.shape[0] and 0 <= nx < solid.shape[1] and solid[nz, nx]:
                rows.append(i); cols.append(ids[nz, nx]); values.append(-conduct)
                diagonal[i] += conduct
            else:
                # Correct staircase face measure to the nearest exposed polygon normal.
                point = np.array([xorigin+(ix+dy/2)*step, (iz+.5+dz/2)*step])
                t = np.clip(((point-starts)*deltas).sum(axis=1)/lengths2, 0, 1)
                distances = ((point-starts-t[:, None]*deltas)**2).sum(axis=1)
                metric = normal_metric[np.argmin(distances)]
                face_area = depth*dx*metric
                convection_area += face_area
                convection = face_area/(dx/(2*k)+1/h) if h else 0.0
                diagonal[i] += convection
                sink[i] += convection
    if not root_g.any():
        raise ValueError('Root is disconnected')
    rows.extend(range(count)); cols.extend(range(count)); values.extend(diagonal)
    matrix = coo_matrix((values, (rows, cols)), shape=(count, count)).tocsr()
    temperature = spsolve(matrix, rhs)
    qbase = float(root_g @ (1-temperature))
    qair = float(sink @ temperature)
    balance = abs(qbase-qair)/max(abs(qair), 1e-12)
    if not np.isfinite(temperature).all() or temperature.min() < -1e-8 or temperature.max() > 1+1e-8 or balance > 1e-8:
        raise ValueError('Temperature bounds or heat balance failed')
    return dict(conductance_W_K=qair, relative_heat_imbalance=balance,
                raster_volume_mm3=count*step*step*design['depth_mm'], cells=count,
                step_mm=step, minimum_normalized_temperature=float(temperature.min()),
                convection_area_mm2=float(convection_area*1e6))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screen', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source = json.loads(args.screen.read_text())
    scenarios = source['scenarios']
    candidates, rejected = [], []
    base = next(study.designs())
    ref = [solve(base, s['k_W_mK'], s['h_W_m2K'])['conductance_W_K'] for s in scenarios]
    for row in source['candidates']:
        try:
            d = normalize(row['design'])
        except ValueError as error:
            rejected.append(dict(id=row['design']['id'], reason=str(error)))
            continue
        values = [solve(d, s['k_W_mK'], s['h_W_m2K']) for s in scenarios]
        candidates.append(dict(design=d, fused_section_volume_mm3=union_area(d)*d['depth_mm'],
                               scenarios=values, worst_ratio_to_straight=min(v['conductance_W_K']/r for v, r in zip(values, ref))))
    best = max(candidates, key=lambda c: c['worst_ratio_to_straight'])
    leaf = max((c for c in candidates if c['design']['id'].startswith('leaf-')), key=lambda c: c['worst_ratio_to_straight'])
    selected = {'straight', best['design']['id'], leaf['design']['id'], source['best_bionic_id']}
    refinement = []
    for row in candidates:
        if row['design']['id'] not in selected:
            continue
        levels = []
        for step in (.2, .1, .05):
            levels.append([solve(row['design'], s['k_W_mK'], s['h_W_m2K'], step) for s in scenarios])
        refinement.append(dict(id=row['design']['id'], levels=levels,
            max_relative_0p1_vs_0p05=max(abs(a['conductance_W_K']/b['conductance_W_K']-1) for a, b in zip(levels[1], levels[2]))))
    result = dict(schema='m64-bionic-fin-fv/v1', status='synthetic_2d_prescribed_h_not_head_cht',
                  screen_sha256=hashlib.sha256(args.screen.read_bytes()).hexdigest(),
                  countercheck_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scenarios=scenarios, candidates=candidates, rejected=rejected,
                  best_overall_id=best['design']['id'], best_bionic_id=leaf['design']['id'], refinement=refinement,
                  real_head_optimized=False, pressure_loss_calculated=False, manufacturing_authorized=False,
                  assumptions=['2d_extrusion_uniform_Y_temperature', 'uniform_prescribed_h', 'isothermal_root',
                               'constant_ambient', 'fused_union_no_internal_convection',
                               'raster_boundary_with_exposed_polygon_normal_area_correction'])
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'countercheck.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    for c in candidates:
        if c['design']['id'] in selected:
            (args.output/(c['design']['id']+'.json')).write_text(json.dumps(c['design'], indent=2)+'\n')
    print(json.dumps(dict(best_overall=best['design']['id'], best_bionic=leaf['design']['id'],
                         worst_ratio=leaf['worst_ratio_to_straight'], candidates=len(candidates))))


if __name__ == '__main__':
    main()
