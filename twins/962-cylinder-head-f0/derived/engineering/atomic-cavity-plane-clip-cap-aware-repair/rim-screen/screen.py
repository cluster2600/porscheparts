"""One bounded exact stored-coordinate necessary rim-edge screen; no geometry change."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import signal
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def dyadic(points):
    ratios = [[value.as_integer_ratio() for value in point] for point in points]
    denominator = max(d for point in ratios for _, d in point)
    if denominator & (denominator-1):
        raise ValueError('Binary64 dyadic denominator required')
    return [tuple(n*(denominator//d) for n,d in point) for point in ratios], denominator


def score(a, b, c):
    ux,uy = b[0]-a[0],b[1]-a[1]
    vx,vy = c[0]-a[0],c[1]-a[1]
    determinant = ux*vy-uy*vx
    total = ux*ux+uy*uy+vx*vx+vy*vy+(vx-ux)**2+(vy-uy)**2
    return determinant*determinant, total*total


def selfcheck():
    triangles = [((0.,0.),(1.,0.),(0.,1.)),
        ((0.,0.),(1.,0.),(0.,2.**-20)),
        ((0.,0.),(2.**-600,0.),(0.,2.**-599)),
        ((-76.,1./8.),(76.,1./4.),(-75.,3./8.))]
    outcomes = []
    for triangle in triangles:
        integers,_ = dyadic(triangle); num,den = score(*integers)
        a,b,c = [tuple(Fraction.from_float(x) for x in p) for p in triangle]
        u = (b[0]-a[0],b[1]-a[1]); v = (c[0]-a[0],c[1]-a[1])
        cross = u[0]*v[1]-u[1]*v[0]
        total = sum(x*x for x in u)+sum(x*x for x in v)+sum((v[i]-u[i])**2 for i in range(2))
        if Fraction(num,den) != cross*cross/(total*total):
            raise ValueError('Exact dyadic/Fraction identity failed')
        passed = 2523*num >= den
        if passed != (12*cross*cross/(total*total) >= Fraction(4,841)):
            raise ValueError('Exact quality-threshold identity failed')
        outcomes.append(passed)
    return dict(literal_triangles=4, dyadic_score_equals_Fraction=True,
        threshold_squared_identity=True, passing_literals=outcomes)


def run(expected):
    path = HERE/'frozen-contract.json'
    if digest(path) != expected:
        raise ValueError('Exact screen contract required')
    contract = json.loads(path.read_text())
    if (contract['analysis_authorized'] is not True or contract['wall_seconds'] != 45
            or contract['quality_threshold'] != '2/29'
            or digest(Path(__file__)) != contract['source_sha256']
            or (HERE/'result.json').exists() or (HERE/'result.json').is_symlink()):
        raise ValueError('Fresh exact authorized screen required')
    def verify():
        return (digest(path) == expected and digest(Path(__file__)) == contract['source_sha256']
            and all(digest(ROOT/name) == value for name,value in contract['input_sha256'].items()))
    if not verify():
        raise ValueError('Screen source/input drift')
    literals = selfcheck()
    reference = json.loads((ROOT/contract['reference']).read_text())
    cap = reference['cap']['components'][0]
    loops = cap['topology']['oriented_boundary_cycles']
    if [len(loop) for loop in loops] != [1482,2026]:
        raise ValueError('Frozen cap-loop identities changed')
    ids = cap['topology']['boundary_vertices']
    if len(ids) != 3508 or len(set(ids)) != 3508:
        raise ValueError('All 3508 existing cap vertices required')
    edges = sorted(tuple(sorted((loops[1][i],loops[1][(i+1)%len(loops[1])]))) for i in range(len(loops[1])))
    if len(set(edges)) != 2026:
        raise ValueError('All 2026 distinct retained rim1 constraints required')
    xy = []
    with (ROOT/contract['candidate']).open('rb') as stream:
        header = stream.read(24)
        if header[:8] != b'962SURF1' or struct.unpack_from('<QQ',header,8) != (869355,1739126):
            raise ValueError('Frozen d2af surface required')
        for vertex in ids:
            stream.seek(24+24*vertex); point = struct.unpack('<ddd',stream.read(24))
            if point[2] != 0. or not all(math.isfinite(x) for x in point):
                raise ValueError('Finite exact z0 cap coordinates required')
            xy.append(point[:2])
    integer_points,denominator = dyadic(xy)
    points = dict(zip(ids,integer_points)); rows = []; comparisons = 0
    started = time.monotonic(); stop_reason = None
    previous = signal.getsignal(signal.SIGALRM)
    def timeout(*_):
        raise TimeoutError('Declared45s saved-row screen deadline')
    try:
        signal.signal(signal.SIGALRM,timeout); signal.alarm(45)
        for a,b in edges:
            best_num = -1; best_den = 1; witness = None
            for vertex,p in zip(ids,integer_points):
                if vertex in (a,b):
                    continue
                num,den = score(points[a],points[b],p); comparisons += 1
                if num*best_den > best_num*den:
                    best_num,best_den,witness = num,den,vertex
            exact = Fraction(12*best_num,best_den)
            rows.append(dict(edge=[a,b],maximizing_existing_vertex=witness,
                exact_maximum_quality_squared=dict(numerator=str(exact.numerator),denominator=str(exact.denominator)),
                approximate_maximum_quality=math.sqrt(float(exact)),
                any_existing_cap_vertex_meets_2_over_29=2523*best_num>=best_den))
    except TimeoutError as exc:
        stop_reason = str(exc)
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM,previous)
    if not verify():
        raise ValueError('Screen source/input drift after calculation')
    complete = len(rows)==len(edges) and stop_reason is None
    failed = [row['edge'] for row in rows if not row['any_existing_cap_vertex_meets_2_over_29']]
    result = dict(schema='962-retained-rim-source-subset-necessary-screen/v1',
        status='complete_necessary_screen_only' if complete else 'partial_deadline_no_full_conclusion',
        contract_sha256=expected,source_sha256=contract['source_sha256'],input_sha256=contract['input_sha256'],
        literal_selfcheck=literals,threshold='2/29',exact_squared_test='2523*det_xy^2 >= (AB_squared+AC_squared+BC_squared)^2',
        arithmetic='Exact common dyadic integer representation of stored binary64 coordinates; no geometry grid, snapping, rounding, or coordinate change.',
        full_query_completed=complete,stop_reason=stop_reason,wall_seconds=time.monotonic()-started,
        wall_limit_seconds=45,complete_cap_vertices=3508,retained_rim1_edges=2026,
        complete_edge_rows=len(rows),third_vertex_comparisons=comparisons,
        dyadic_denominator_power_of_two=denominator.bit_length()-1,
        completed_edges_without_any_quality_feasible_existing_cap_vertex=len(failed),failed_completed_edge_ids=failed,
        edge_results=rows,relaxed_constraints=['Visibility','Annulus domain and nonoverlap','Normal orientation','Fixed-face constraints','Local envelope','Neighbor policy'],
        interpretation='Each complete row is the exact maximum over the 3506 nonendpoint cap vertices. A below-threshold maximum rules out source-subset cap retriangulation retaining that edge. A passing maximum is necessary only; no triangulation or keeper policy is constructed.',
        no_full_conclusion_if_partial=not complete,all_bound_inputs_unchanged=True,
        geometry_or_coordinate_files_written=0,scientific_imports_native_Docker_network_API_Git_calls=0,
        repair_or_surface_volume_physics_or_manufacturing_admitted=False)
    with (HERE/'result.json').open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=result['status'],edges=len(rows),failed=len(failed),wall_seconds=result['wall_seconds'],result_sha256=digest(HERE/'result.json'))))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract-sha256',required=True)
    run(parser.parse_args().contract_sha256)
