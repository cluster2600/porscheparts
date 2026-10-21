"""Freeze six-vertex-order source-expression binary64 ranges; never run CGAL."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PINS = {
    'twins/962-cylinder-head-f0/source/analysis-cgal/atomic_cavity_002.cpp': 'e2dfe8417b77aaf8fb2e44bf98aa26232170c80c0bb2c69af0b551d695c8b11a',
    'twins/962-cylinder-head-f0/source/analysis-cgal/quality_patch.cpp': '6a56acf7a1d7a4882251044f9331ff0e4590042a4d1d15f0b4599e0ab241d9ee',
    'work/962-engineering/atomic-cavity-fixtures-prep-001/expectations.json': '2a6993b704a007da882fa8d48bbe9aa6c04a42831b520e77d7e3dd26246baa1e',
    'work/962-engineering/atomic-cavity-fixtures-prep-001/fixture-freeze.json': '9584ca30708a08f738ce909bd479d3fdc52fb6581d4e3afbb630477ecbbd4ca2',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_quality(a, b, c):
    # quality_patch.cpp triangle_quality: preserve binary64 operation grouping.
    u = tuple(float(b[i])-float(a[i]) for i in range(3))
    w = tuple(float(c[i])-float(a[i]) for i in range(3))
    sq = lambda v: (v[0]*v[0]+v[1]*v[1])+v[2]*v[2]
    cross = (u[1]*w[2]-u[2]*w[1], u[2]*w[0]-u[0]*w[2], u[0]*w[1]-u[1]*w[0])
    delta = tuple(w[i]-u[i] for i in range(3))
    total = (sq(u)+sq(w))+sq(delta)
    result = ((2.0*math.sqrt(3.0))*math.sqrt(sq(cross)))/total
    if not math.isfinite(result) or result <= 0:
        raise ValueError('Finite positive source-expression quality required')
    return result


def ranges(points, faces, expected_poor):
    orders = list(itertools.permutations(range(3)))
    rows = []
    for index, ids in enumerate(faces):
        values = [source_quality(*(points[ids[i]] for i in order)) for order in orders]
        poor = {value < 2.0/29.0 for value in values}
        if len(poor) != 1:
            raise ValueError('Vertex-order-dependent threshold classification')
        rows.append(dict(reference_face_row=index, reference_vertex_IDs=ids,
                         quality_by_vertex_order=values, minimum=min(values), maximum=max(values),
                         below_necessary_bound=poor.pop()))
    poor_count = sum(row['below_necessary_bound'] for row in rows)
    if poor_count != expected_poor:
        raise ValueError('Frozen poor count and source expression differ')
    return dict(vertices=len(points), faces=len(faces), poor_count=poor_count,
                global_minimum_reserved_interval=[min(r['minimum'] for r in rows), min(r['maximum'] for r in rows)],
                face_rows=rows)


def run():
    expected = dict(PINS); expected[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
    before = {name: sha(ROOT/name) for name in expected}
    if before != expected or sys.float_info.mant_dig != 53 or sys.float_info.radix != 2:
        raise ValueError('Frozen sources/fixtures and binary64 host required')
    literal = json.loads((ROOT/next(n for n in PINS if n.endswith('expectations.json'))).read_text())
    cases = []
    for case in literal['cases']:
        before_range = ranges(case['input_points'], case['input_oriented_faces'], case['before']['poor_faces'])
        after_range = ranges(case['expected_points'], case['expected_oriented_faces'], case['expected_after']['poor_faces'])
        reject = case['name'] == 'all-fixed'
        cases.append(dict(name=case['name'], before=before_range, expected_reference_after=after_range,
            expected_native_quality_checked=not reject,
            expected_native_minimum_quality='null_before_fixed_group_refusal' if reject else after_range['global_minimum_reserved_interval'],
            all_fixed_after_range_scope='Unchanged reference arrays only; native candidate/quality is unrun on early refusal.' if reject else None))
    after = {name: sha(ROOT/name) for name in expected}
    if before != after:
        raise ValueError('Bound source or literal changed during pure arithmetic')
    return dict(schema='962-atomic-cavity-declared-six-order-quality-reference/v1',
        status='frozen_before_native_compile_or_fixture_execution',
        vertex_orders=[list(x) for x in itertools.permutations(range(3))],
        range_definition='Per face min/max over all6literal vertex orders; global minimum interval is [min face minima,min face maxima]. No slack, epsilon, nextafter or fitted tolerance.',
        arithmetic_definition='Binary64 source-expression reference for quality_patch.cpp triangle_quality; explicit subtract/cross/squared-length/add/multiply/divide grouping and host math.sqrt. This is not native CGAL execution or a compiler/FMA attestation.',
        native_comparison_rule='All actual literal coordinates/orientedfaces/origins/masks/topology/volume/counts must match the full frozen reference first. Compare reported finite candidate minimum only within this reserved interval; preserve any mismatch without widening it.',
        cases=cases, pins_before=before, pins_after=after, all_inputs_unchanged=True,
        runtime=dict(python=platform.python_version(), mantissa_bits=sys.float_info.mant_dig),
        native_compiler_SSH_Git_calls=0, fixture_execution_authorized=False,
        manufacturing_authorized=False)


if __name__ == '__main__':
    result = run()
    with (OUT/'quality-ranges.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({r['name']: {'before': r['before']['global_minimum_reserved_interval'],
                                 'reference_after': r['expected_reference_after']['global_minimum_reserved_interval'],
                                 'native_quality_checked': r['expected_native_quality_checked']} for r in result['cases']}, indent=2))
