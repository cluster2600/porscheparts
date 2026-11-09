#!/usr/bin/env python3
"""Fresh S6 constitutive, curved-integration and oblique fiber-field controls."""
from copy import deepcopy
import argparse
import json
import math
from pathlib import Path
import solve


def rotated(p, oblique):
    if not oblique:
        return list(p)
    a, b = math.radians(30), math.radians(40)
    x, y, z = p
    x, y, z = x, math.cos(a)*y-math.sin(a)*z, math.sin(a)*y+math.cos(a)*z
    return [math.cos(b)*x-math.sin(b)*y, math.sin(b)*x+math.cos(b)*y, z]


def coupon(oblique=False):
    nodes, lookup, elements = {}, {}, []
    def node(p):
        p = rotated(p, oblique); key = tuple(round(x, 12) for x in p)
        if key not in lookup:
            lookup[key] = len(nodes)+1; nodes[lookup[key]] = list(key)
        return lookup[key]
    for i in range(20):
        for j in range(2):
            a, b, c, d = [[5*i, 5*j, 0], [5*(i+1), 5*j, 0],
                          [5*(i+1), 5*(j+1), 0], [5*i, 5*(j+1), 0]]
            for corners in [[a, b, c], [a, c, d]]:
                points = corners+[[.5*(x+y) for x, y in zip(corners[u], corners[v])]
                                   for u, v in [(0, 1), (1, 2), (2, 0)]]
                elements.append({'id': len(elements)+1, 'type': 'S6', 'nodes': [node(p) for p in points],
                                 'component': 'synthetic_coupon', 'surface_id': 'coupon',
                                 'fiber_reference': rotated([1, 0, 0], oblique),
                                 'normal_hint': rotated([0, 0, 1], oblique)})
    longitudinal = rotated([1, 0, 0], oblique)
    clamp = [n for n, p in nodes.items() if abs(solve.dot(p, longitudinal)) < 1e-8]
    tip = {}
    for element in elements:
        for edge in solve.edges(element):
            if all(abs(solve.dot(nodes[n], longitudinal)-100) < 1e-8 for n in edge):
                tip[solve.edge_key(edge)] = edge
    return {'units': 'mm', 'status': 'assumed', 'thickness_mm': 2., 'nodes': nodes, 'elements': elements,
            'node_sets': {'CLAMP': clamp}, 'edge_sets': {'TORSION_LEFT': list(tip.values()), 'TORSION_RIGHT': list(tip.values())},
            'element_sets': {'BENDING_FLOOR': [e['id'] for e in elements]}, 'join_contract': []}


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(); solve.require(not args.output.exists(), 'Fresh output required'); args.output.mkdir(parents=True)
    assumptions = json.loads((solve.HERE/'analysis-assumptions.json').read_text()); results = {}
    for name, isotropic, E, oblique in [('isotropic', True, 70000., False), ('isotropic-oblique', True, 70000., True), ('isotropic-eight-ply', False, 70000., False),
                                        ('UD-zero-oblique', False, 135000., True), ('UD-ninety-oblique', False, 10000., True)]:
        config = deepcopy(assumptions); card = config['laminate']
        card['poisson'] = {'nu12': 0., 'nu13': 0., 'nu23': 0.}
        if E == 70000.:
            card['engineering_constants_MPa'] = {k: 70000. if k.startswith('E') else 35000. for k in ['E1', 'E2', 'E3', 'G12', 'G13', 'G23']}
        else:
            card['ply_angles_deg'] = [0. if E == 135000. else 90.]*8
        mesh = coupon(oblique); nodes = mesh['nodes']
        weights = solve.edge_weights(nodes, mesh['edge_sets']['TORSION_LEFT'])
        normal = rotated([0, 0, 1], oblique)
        loads = {n: [-v*w for v in normal] for n, w in weights.items()}
        result = solve.run(mesh, config, args.output/name, 'bending', {}, benchmark=True,
                           isotropic=isotropic, override_loads=loads)
        measured = result['metrics']['endpoint_F_dot_U_Nmm']
        expected = 100**3/(3*E*(10*2**3/12))
        error = abs(measured/expected-1)
        expanded = result['metrics'].get('expanded_isotropic_control_balance')
        results[name] = {'analytic_Euler_Bernoulli_tip_mm': expected, 'actual_tip_mm': measured,
                         'relative_difference': error, 'limit': .01, 'passed': error < .01,
                         'expanded_isotropic_control_balance': expanded,
                         'original_node_RF_diagnostic': result['metrics']['original_node_RF_diagnostic'],
                         'actual_result_sha256': solve.sha(args.output/name/'result.json')}
        if expanded is not None:
            results[name]['passed'] = results[name]['passed'] and expanded['passed']
    equality = abs(results['isotropic-eight-ply']['actual_tip_mm']/results['isotropic']['actual_tip_mm']-1)
    report = {'classification': 'actual_fresh_S6_analytic_material_and_oblique_fiber_reference_controls',
              'results': results, 'layered_isotropic_relative_difference': equality, 'layered_equivalence_limit': 1e-4,
              'passed': all(x['passed'] for x in results.values()) and equality < 1e-4,
              'analytic_scope': '100x10x2mm,1N tip,nu0 slender cantilever; Euler-Bernoulli excludes transverse shear',
              'oblique_control': 'Rigid30degX then40degZ rotation; canonical longitudinal fiber_reference differs from projectedglobalX',
              'source_sha256': solve.sha(__file__), 'solver_sha256': solve.sha(solve.__file__),
              'policy_amendment': 'Initial oblique S6 UD control reproduced analytic displacement but original-node DAT clamp RF had a14.242N residual for1N. Expanded isotropic RF controls distinguish output incompleteness from load/fixture error. Composite reaction equilibrium remains unverified.',
              'physical_validation': False}
    (args.output/'benchmark.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report)); solve.require(report['passed'], 'Fresh S6 control failed')


if __name__ == '__main__':
    main()
