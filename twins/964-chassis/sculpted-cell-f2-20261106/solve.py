#!/usr/bin/env python3
"""Conditional CFRP shell analysis of a bound, conforming sculpted-cell mesh.

S6/S8R midsurfaces are supplied by the independent geometry lane. No scan or
Porsche contact coordinates are synthesized by this analysis. Raw data stay
in a caller-selected fresh private directory.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
F1 = HERE.parent / 'assumed-cell-20261106'
F1_SHA = 'ad70de944af810552a5bc3ce30fb9e0ac84aabc8d8cc1114c91637d533d076ae'
PARSER_SHA = '678860834ad394ef0a1973b090918948987ee1e5f4f285075ea12ad3334f9e79'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def load_support(name, expected):
    path = F1 / (name + '.py')
    require(sha(path) == expected, 'Frozen F1 support source changed: ' + name)
    spec = importlib.util.spec_from_file_location('f2_support_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


support = load_support('solve', F1_SHA)
parser = load_support('nonlinear_probe', PARSER_SHA)
G3 = [(-math.sqrt(3 / 5), 5 / 9), (0., 8 / 9), (math.sqrt(3 / 5), 5 / 9)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a)
    require(n > 1e-12, 'Degenerate direction')
    return [v / n for v in a]


def shape(kind, r, s):
    if kind == 'S6':
        q = 1 - r - s
        return ([q*(2*q-1), r*(2*r-1), s*(2*s-1), 4*q*r, 4*r*s, 4*s*q],
                [1-4*q, 4*r-1, 0., 4*(q-r), 4*s, -4*s],
                [1-4*q, 0., 4*s-1, -4*r, 4*r, 4*(q-s)])
    require(kind == 'S8R', 'Unsupported element type: ' + kind)
    N, dr, ds = [], [], []
    for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        N.append(.25*(1+a*r)*(1+b*s)*(a*r+b*s-1))
        dr.append(.25*a*(1+b*s)*(2*a*r+b*s))
        ds.append(.25*b*(1+a*r)*(a*r+2*b*s))
    return (N + [.5*(1-r*r)*(1-s), .5*(1+r)*(1-s*s),
                 .5*(1-r*r)*(1+s), .5*(1-r)*(1-s*s)],
            dr + [-r*(1-s), .5*(1-s*s), -r*(1+s), -.5*(1-s*s)],
            ds + [-.5*(1-r*r), -(1+r)*s, .5*(1-r*r), -(1-r)*s])


def quadrature(kind):
    if kind == 'S6':
        # Duffy map from [0,1]^2: (r,s)=(u,(1-u)v), Jacobian 1-u.
        return [((a+1)/2, (1-(a+1)/2)*(b+1)/2, wa*wb/4*(1-(a+1)/2))
                for a, wa in G3 for b, wb in G3]
    return [(a, b, wa*wb) for a, wa in G3 for b, wb in G3]


def evaluate(nodes, element, r, s):
    N, dr, ds = shape(element['type'], r, s)
    points = [nodes[n] for n in element['nodes']]
    x = [sum(w*p[k] for w, p in zip(N, points)) for k in range(3)]
    a = [sum(w*p[k] for w, p in zip(dr, points)) for k in range(3)]
    b = [sum(w*p[k] for w, p in zip(ds, points)) for k in range(3)]
    return N, x, a, b, cross(a, b)


def edges(element):
    triples = [(0, 1, 3), (1, 2, 4), (2, 0, 5)] if element['type'] == 'S6' else [(0, 1, 4), (1, 2, 5), (2, 3, 6), (3, 0, 7)]
    return [tuple(element['nodes'][i] for i in triple) for triple in triples]


def edge_key(edge):
    return min(edge[0], edge[1]), max(edge[0], edge[1]), edge[2]


def orientation(nodes, element):
    c = (1/3, 1/3) if element['type'] == 'S6' else (0., 0.)
    normal = unit(evaluate(nodes, element, *c)[4])
    explicit = element.get('fiber_reference')
    reference = unit(explicit) if explicit is not None else [1., 0., 0.]
    tangent = [a-dot(reference, normal)*b for a, b in zip(reference, normal)]
    fallback = explicit is None and norm(tangent) < .1
    if fallback:
        reference = [0., 1., 0.]
        tangent = [a-dot(reference, normal)*b for a, b in zip(reference, normal)]
    a = unit(tangent)
    require(explicit is None or norm(tangent) > .1, 'Canonical fiber reference is nearly normal to its shell')
    return a, unit(cross(normal, a)), normal, fallback


def canonical_mesh(raw):
    require(raw['units'] == 'mm' and raw['status'] == 'assumed', 'Require explicit assumed mm mesh')
    nodes = {int(n): [float(x) for x in p] for n, p in raw['nodes'].items()}
    require(all(n > 0 and len(p) == 3 and all(math.isfinite(v) for v in p)
                for n, p in nodes.items()), 'Invalid node ID/coordinate')
    elements = raw['elements']
    require(elements and len({e['id'] for e in elements}) == len(elements), 'Duplicate/empty element IDs')
    for e in elements:
        require(e['type'] in ('S6', 'S8R') and len(e['nodes']) == (6 if e['type'] == 'S6' else 8), 'Bad shell connectivity')
        require(len(set(e['nodes'])) == len(e['nodes']) and set(e['nodes']) <= set(nodes), 'Repeated/unknown node')
        require(e['component'] and e['surface_id'], 'Missing component/surface identity')
    require({n for e in elements for n in e['nodes']} == set(nodes), 'Unused/unbound mesh nodes')
    return nodes, elements


def audit(raw, assumptions, require_upper=True):
    nodes, elements = canonical_mesh(raw)
    limits = assumptions['numerical_admission']
    all_edges, corner_pairs, surface_edges = defaultdict(list), {}, defaultdict(list)
    seen_faces, coordinates = set(), set()
    for n, p in nodes.items():
        key = tuple(round(v, 8) for v in p)
        require(key not in coordinates, 'Coincident unmerged source nodes')
        coordinates.add(key)
    minima = {'scaled_jacobian': 1., 'normal_dot': 1.}
    maximum_aspect, area, component_area, fallback_count = 1., 0., defaultdict(float), 0
    element_data = {}
    for e in elements:
        corner_count = 3 if e['type'] == 'S6' else 4
        key = tuple(sorted(e['nodes'][:corner_count]))
        require(key not in seen_faces, 'Duplicate shell face')
        seen_faces.add(key)
        a, b, normal, fallback = orientation(nodes, e)
        fallback_count += int(fallback)
        hint = e.get('normal_hint')
        if hint is not None:
            require(dot(normal, unit(hint)) > 0, 'Canonical normal hint contradicts winding')
        samples = quadrature(e['type'])
        boundaries = [(0., 0.), (1., 0.), (0., 1.), (.5, 0.), (.5, .5), (0., .5)] if e['type'] == 'S6' else [(r, s) for r in [-1., 0., 1.] for s in [-1., 0., 1.]]
        for r, s, _ in samples + [(r, s, 0.) for r, s in boundaries]:
            _, _, du, dv, jac = evaluate(nodes, e, r, s)
            j, la, lb = norm(jac), norm(du), norm(dv)
            require(min(j, la, lb) > 1e-12, 'Degenerate curved element')
            scaled, agreement = j/(la*lb), dot(unit(jac), normal)
            minima['scaled_jacobian'] = min(minima['scaled_jacobian'], scaled)
            minima['normal_dot'] = min(minima['normal_dot'], agreement)
            maximum_aspect = max(maximum_aspect, la/lb, lb/la)
            require(scaled >= limits['minimum_sampled_scaled_jacobian'], 'Sampled skewed/folded shell')
            require(agreement >= limits['minimum_sampled_normal_dot_centre_normal'], 'Sampled normal reversal/excess curvature')
            require(max(la/lb, lb/la) <= limits['maximum_sampled_tangent_aspect_ratio'], 'Excessive sampled aspect ratio')
        element_area = sum(weight*norm(evaluate(nodes, e, r, s)[4]) for r, s, weight in samples)
        area += element_area
        component_area[e['component']] += element_area
        element_data[e['id']] = {'area_mm2': element_area, 'zero_axis': a, 'second_axis': b, 'normal': normal}
        for edge in edges(e):
            key = edge_key(edge)
            pair = key[:2]
            require(pair not in corner_pairs or corner_pairs[pair] == key[2], 'Nonconforming quadratic midside')
            corner_pairs[pair] = key[2]
            all_edges[key].append(e)
            surface_edges[(e['surface_id'], key)].append(edge)
    for same_surface in surface_edges.values():
        if len(same_surface) == 2:
            require(same_surface[0][:2] == same_surface[1][1::-1], 'Inconsistent winding within canonical sheet')
        require(len(same_surface) <= 2, 'Nonmanifold edge within one canonical sheet')
    neighbours = defaultdict(set)
    orientation_changes = {'same_surface_max_angle_deg': 0., 'junction_max_angle_deg': 0.}
    joined_surfaces, joined_components = defaultdict(int), defaultdict(int)
    for incident in all_edges.values():
        for i, e in enumerate(incident):
            for other in incident[i+1:]:
                neighbours[e['id']].add(other['id']); neighbours[other['id']].add(e['id'])
                cosine = min(1., abs(dot(element_data[e['id']]['zero_axis'], element_data[other['id']]['zero_axis'])))
                angle = math.degrees(math.acos(cosine))
                field = 'same_surface_max_angle_deg' if e['surface_id'] == other['surface_id'] else 'junction_max_angle_deg'
                orientation_changes[field] = max(orientation_changes[field], angle)
                if e['surface_id'] != other['surface_id']:
                    joined_surfaces[tuple(sorted((str(e['surface_id']), str(other['surface_id']))))] += 1
                if e['component'] != other['component']:
                    joined_components[tuple(sorted((e['component'], other['component'])))] += 1
    visited, todo = set(), [elements[0]['id']]
    while todo:
        n = todo.pop()
        if n not in visited:
            visited.add(n); todo.extend(neighbours[n]-visited)
    require(len(visited) == len(elements), 'Shell is not fully connected through complete quadratic edges')
    verified_joins = []
    for join in raw.get('join_contract', []):
        if 'surface_a' in join:
            key = tuple(sorted((str(join['surface_a']), str(join['surface_b']))))
            count = joined_surfaces[key]
        else:
            key = tuple(sorted((join['component_a'], join['component_b'])))
            count = joined_components[key]
        require(count >= join.get('minimum_shared_edges', 1), 'Declared canonical junction is unjoined: '+join['id'])
        verified_joins.append({'id': join['id'], 'shared_quadratic_edges': count})
    upper = set(raw.get('upper_structure_components', []))
    if require_upper:
        require(upper and upper <= set(component_area), 'Full-cell upper structure is undeclared/missing')
        require(raw.get('join_contract'), 'Canonical upper/lower junction contract is missing')
        require(any(bool(set(pair) & upper) and bool(set(pair)-upper) for pair in joined_components), 'Upper structure has no complete-edge connection to lower cell')
    clamp = set(raw['node_sets']['CLAMP'])
    require(clamp and clamp <= set(nodes), 'Clamp is empty or outside mesh')
    for name in ['TORSION_LEFT', 'TORSION_RIGHT']:
        group = raw['edge_sets'][name]
        require(group and len({edge_key(e) for e in group}) == len(group), 'Duplicate/empty fixture edge set')
        require(all(edge_key(e) in all_edges for e in group), 'Fixture is not on actual source edges')
    floor = raw['element_sets']['BENDING_FLOOR']
    require(floor and len(set(floor)) == len(floor) and set(floor) <= set(element_data), 'Invalid bending floor set')
    support.validate_material(assumptions['laminate'])
    result = {'classification': 'upstream_sampled_mesh_and_hypothesis_method_admission',
              'verdict': 'admitted_for_conditional_global_shell_response_only',
              'nodes': len(nodes), 'elements': len(elements), 'element_types': sorted({e['type'] for e in elements}),
              'shared_edge_connected_components': 1, 'sampled_min_scaled_jacobian': minima['scaled_jacobian'],
              'sampled_min_normal_dot_centre': minima['normal_dot'], 'sampled_max_tangent_aspect': maximum_aspect,
              'area_mm2': area, 'component_area_mm2': dict(component_area),
              'zero_axis_Y_fallback_elements': fallback_count, 'canonical_joins_verified': verified_joins,
              'explicit_canonical_fiber_reference_elements': sum('fiber_reference' in e for e in elements),
              'adjacent_material_axis_field': orientation_changes,
              'continuous_drape_or_fiber_steering_qualified': False,
              'open_quadratic_edges': sum(len(v) == 1 for v in all_edges.values()),
              'branching_quadratic_edges': sum(len(v) > 2 for v in all_edges.values()),
              'upper_structure_components': sorted(upper), 'all_elements_included_mechanically': True,
              'normal_stack_convention': 'Canonical winding local normal; stack runs negative to positive normal, not global Z',
              'quality_scope': 'Sampled Jacobians, topology and material compliance; no continuous interval or physical qualification',
              'physical_validation': False, 'manufacturing_authorized': False}
    return result, nodes, elements, element_data


def edge_weights(nodes, group):
    values = defaultdict(float)
    for i, j, m in group:
        points = [nodes[i], nodes[j], nodes[m]]
        for s, weight in G3:
            N, dN = [.5*s*(s-1), .5*s*(s+1), 1-s*s], [s-.5, s+.5, -2*s]
            tangent = [sum(w*p[k] for w, p in zip(dN, points)) for k in range(3)]
            for n, w in zip((i, j, m), N):
                values[n] += w*weight*norm(tangent)
    length = sum(values.values())
    require(length > 0, 'Zero fixture edge length')
    return {n: value/length for n, value in values.items()}


def make_loads(raw, nodes, elements, case, assumptions):
    loads, groups = defaultdict(lambda: [0., 0., 0.]), {}
    fixture = assumptions['fixtures']
    if case == 'torsion':
        for name, force in zip(fixture['torsion_edge_sets'], fixture['torsion_vertical_resultants_N']):
            groups[name] = edge_weights(nodes, raw['edge_sets'][name])
            for n, w in groups[name].items():
                loads[n][2] += force*w
    else:
        require(case == 'bending', 'Unknown fixture case')
        floor = set(raw['element_sets'][fixture['bending_element_set']])
        area = 0.
        for e in elements:
            if e['id'] not in floor:
                continue
            for r, s, weight in quadrature(e['type']):
                N, _, _, _, jac = evaluate(nodes, e, r, s)
                da = weight*norm(jac); area += da
                for n, w in zip(e['nodes'], N):
                    loads[n][2] += w*da
        require(area > 0, 'No actual curved floor area')
        total = fixture['bending_total_vertical_force_N']
        loads = {n: [0., 0., f[2]*total/area] for n, f in loads.items()}
    return dict(loads), groups


def write_deck(path, raw, nodes, elements, element_data, loads, card, isotropic=False, nonlinear=False):
    text = ['*HEADING', 'Explicit hypothetical sculpted cell; no fit or strength qualification', '*NODE,NSET=NALL']
    text += [f'{n},'+','.join(f'{v:.12g}' for v in p) for n, p in sorted(nodes.items())]
    for kind in sorted({e['type'] for e in elements}):
        text.append(f'*ELEMENT,TYPE={kind},ELSET=ALL_{kind}')
        text += [f"{e['id']},"+','.join(str(n) for n in e['nodes']) for e in elements if e['type'] == kind]
    text += ['*NSET,NSET=CLAMP']
    fixed = sorted(raw['node_sets']['CLAMP'])
    text += [','.join(map(str, fixed[i:i+12])) for i in range(0, len(fixed), 12)]
    text.append('*MATERIAL,NAME=UD')
    if isotropic:
        text += ['*ELASTIC', '70000.,0.']
    else:
        E, p = card['engineering_constants_MPa'], card['poisson']
        text += ['*ELASTIC,TYPE=ENGINEERING CONSTANTS', ','.join(str(v) for v in [E['E1'], E['E2'], E['E3'], p['nu12'], p['nu13'], p['nu23'], E['G12'], E['G13']]), str(E['G23'])]
    groups = defaultdict(list)
    for e in elements:
        data = element_data[e['id']]
        t = float(e.get('thickness_mm', raw.get('thickness_mm', 0)))
        require(t > 0, 'Canonical physical shell thickness is missing')
        key = (t, tuple(round(v, 12) for v in data['zero_axis']+data['second_axis']))
        groups[key].append(e['id'])
    for index, ((t, vectors), ids) in enumerate(groups.items()):
        name = 'SEC'+str(index)
        text += [f'*ELSET,ELSET={name}']
        text += [','.join(map(str, ids[i:i+12])) for i in range(0, len(ids), 12)]
        if isotropic:
            text += [f'*SHELL SECTION,ELSET={name},MATERIAL=UD', str(t)]
        else:
            a, b = vectors[:3], vectors[3:]
            for k, angle in enumerate(card['ply_angles_deg']):
                c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                aa = [c*x+s*y for x, y in zip(a, b)]; bb = [-s*x+c*y for x, y in zip(a, b)]
                text += [f'*ORIENTATION,NAME=O{index}_{k}', ','.join(f'{v:.12g}' for v in aa+bb)]
            text.append(f'*SHELL SECTION,COMPOSITE,ELSET={name}')
            text += [f"{t/len(card['ply_angles_deg']):.12g},,UD,O{index}_{k}" for k in range(len(card['ply_angles_deg']))]
    text += ['*BOUNDARY', 'CLAMP,1,6', '*STEP,NLGEOM,INC=60' if nonlinear else '*STEP', '*STATIC']
    if nonlinear:
        text += ['0.1,1.,1.e-5,0.25']
    text += ['*CLOAD']
    for n, f in sorted(loads.items()):
        for k, v in enumerate(f, 1):
            if v:
                text.append(f'{n},{k},{v:.14g}')
    text += ['*NODE PRINT,NSET=NALL', 'U', '*NODE PRINT,NSET=CLAMP,TOTALS=YES', 'RF', '*NODE FILE,OUTPUT=3D', 'U,RF' if isotropic else 'U', '*END STEP']
    path.write_text('\n'.join(text)+'\n')


def expanded_isotropic_balance(path, nodes, loads):
    fields = {'coordinates': {}, 'FORC': {}}
    block = None
    for line in path.read_text().splitlines():
        if line.startswith('    2C'):
            block = 'coordinates'
        elif line.startswith(' -4'):
            block = line.split()[1]
        elif line.startswith(' -3'):
            block = None
        elif line.startswith(' -1') and block in fields:
            n = int(line[3:13]); require(n not in fields[block], 'Duplicate expanded FRD node')
            fields[block][n] = [float(line[13+12*k:25+12*k]) for k in range(3)]
    points, forces = fields['coordinates'], fields['FORC']
    require(points and points.keys() == forces.keys(), 'Expanded coordinate/RF coverage mismatch')
    total = [sum(f[k] for f in forces.values()) for k in range(3)]
    moment = [sum(cross(points[n], f)[k] for n, f in forces.items()) for k in range(3)]
    fs = sum(norm(f) for f in loads.values())
    ms = sum(norm(cross(nodes[n], f)) for n, f in loads.items())
    require(fs > 0 and ms > 0, 'Expanded control reference scale is empty')
    fr, mr = norm(total)/fs, norm(moment)/ms
    return {'scope': 'Noncomposite isotropic expanded FRD control only; RF includes all external loads and reactions',
            'expanded_nodes': len(points), 'global_force_sum_N': total,
            'global_moment_sum_Nmm': moment, 'force_relative_residual': fr,
            'moment_relative_residual': mr, 'limit': 1e-4, 'passed': max(fr, mr) < 1e-4}


def run(raw, assumptions, output, case, input_hashes, nonlinear=False, benchmark=False, isotropic=False, override_loads=None):
    require(not output.exists(), 'Use a fresh private output path')
    audit_result, nodes, elements, data = audit(raw, assumptions, not benchmark)
    loads, groups = make_loads(raw, nodes, elements, case, assumptions)
    if override_loads is not None:
        loads, groups = override_loads, {}
    require(all(sha(p) == expected for p, expected in input_hashes.items()), 'Preflight source hash mismatch')
    output.mkdir(parents=True)
    write_deck(output/'model.inp', raw, nodes, elements, data, loads, assumptions['laminate'], isotropic, nonlinear)
    preflight = {'classification': 'preflight_assumed_sculpted_cell_global_response', 'mesh_audit': audit_result,
                 'solver_source_sha256': sha(__file__), 'F1_runtime_source_sha256': F1_SHA,
                 'final_time_parser_sha256': PARSER_SHA, 'input_hashes': input_hashes,
                 'deck_sha256': sha(output/'model.inp'), 'case': case, 'nonlinear_geometry': nonlinear,
                 'material': 'isotropic_control' if isotropic else 'eight_ply_orthotropic_assumed_CFRP',
                 'geometry_sha256': raw.get('geometry_sha256'), 'nominal_h_mm': raw.get('nominal_h_mm'),
                 'physical_validation': False, 'manufacturing_authorized': False, 'donor_transform': None}
    (output/'preflight.json').write_text(json.dumps(preflight, indent=2)+'\n')
    elapsed = support.run_solver(output, 8, 600)
    final, RF, times = parser.final_dat(output/'model.dat')
    U = final['U']; require(set(U) == set(nodes), 'Original node output does not match bound mesh')
    require(all(sha(p) == expected for p, expected in input_hashes.items()), 'Source input changed during solve')
    if nonlinear:
        require('Nonlinear geometric effects are taken into account' in (output/'stdout.log').read_text(), 'Nonlinear solver witness missing')
    resultant = [sum(f[k] for f in loads.values()) for k in range(3)]
    moment = [sum(cross(nodes[n], f)[k] for n, f in loads.items()) for k in range(3)]
    product = sum(dot(f, U[n]) for n, f in loads.items()); require(product > 0, 'Nonpositive endpoint force-displacement product')
    metrics = {'applied_resultant_N': resultant, 'applied_moment_about_origin_Nmm': moment,
               'endpoint_F_dot_U_Nmm': product, 'endpoint_product_is_path_work_or_energy': False,
               'maximum_displacement_norm_mm': max(norm(p) for p in U.values()),
               'maximum_clamp_displacement_mm': max(norm(U[n]) for n in raw['node_sets']['CLAMP']),
               'final_time': final['time'], 'final_RF_time': RF['time'], 'actual_output_times': times}
    force_diagnostic = support.force_balance(nodes, loads, raw['node_sets']['CLAMP'], RF['RF'])
    force_diagnostic['original_node_DAT_screen_passed'] = force_diagnostic.pop('translational_force_balance_verified')
    force_diagnostic['scope'] = 'Oblique S6 controls do not close this RF balance; documented MPC-force omission is a possible cause. This diagnostic does not admit global equilibrium.'
    metrics['original_node_RF_diagnostic'] = force_diagnostic
    if isotropic:
        metrics['expanded_isotropic_control_balance'] = expanded_isotropic_balance(output/'model.frd', nodes, loads)
    if not benchmark and case == 'torsion':
        a, b = assumptions['fixtures']['torsion_edge_sets']
        ya, yb = [sum(w*nodes[n][1] for n, w in groups[g].items()) for g in (a, b)]
        ua, ub = [sum(w*U[n][2] for n, w in groups[g].items()) for g in (a, b)]
        require(abs(ya-yb) > 1 and (ua-ub)/(ya-yb) > 0, 'Invalid hypothetical torsion lever/twist')
        angle = (ua-ub)/(ya-yb)
        metrics.update(force_weighted_lever_y_mm=[ya, yb], force_weighted_band_Uz_mm=[ua, ub],
                       secant_twist_rad=angle, secant_twist_deg=math.degrees(angle),
                       fixture_stiffness_Nm_per_deg=(moment[0]/1000)/math.degrees(angle))
    elif not benchmark:
        force = abs(assumptions['fixtures']['bending_total_vertical_force_N'])
        metrics.update(force_weighted_floor_deflection_mm=product/force,
                       fixture_stiffness_N_per_mm=force*force/product)
    component_U = defaultdict(list)
    for e in elements:
        component_U[e['component']].extend(norm(U[n]) for n in e['nodes'])
    metrics['component_maximum_displacement_norm_mm'] = {k: max(v) for k, v in component_U.items()}
    result = dict(preflight, classification='executed_conditional_sculpted_cell_shell_response', metrics=metrics,
                  elapsed_seconds=elapsed, reaction_moment_equilibrium_verified=False,
                  global_reaction_force_equilibrium_verified=False,
                  independent_energy_verified=False, stiffness_scope='Finite-load geometric-nonlinear secant' if nonlinear else 'Zero-load linear tangent of the assumed ideal assembly',
                  stress_strength_buckling_crash_or_fatigue_qualified=False,
                  DAT_sha256=sha(output/'model.dat'), FRD_sha256=sha(output/'model.frd'))
    (output/'displacements.json').write_text(json.dumps(U, separators=(',', ':'))+'\n')
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mesh', type=Path, required=True)
    ap.add_argument('--geometry', type=Path, required=True)
    ap.add_argument('--geometry-audit', type=Path, required=True)
    ap.add_argument('--assumptions', type=Path, default=HERE/'analysis-assumptions.json')
    ap.add_argument('--case', choices=['torsion', 'bending'], required=True)
    ap.add_argument('--nonlinear', action='store_true')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    raw = json.loads(args.mesh.read_text()); assumptions = json.loads(args.assumptions.read_text())
    require(raw['geometry_sha256'] == sha(args.geometry), 'Mesh is not bound to canonical geometry')
    geometry_audit = json.loads(args.geometry_audit.read_text())
    require(geometry_audit['geometry_sha256'] == sha(args.geometry) and geometry_audit['admitted_for_hypothesis_study'], 'Independent canonical geometry audit did not admit this input')
    paths = [args.mesh, args.geometry, args.geometry_audit, args.assumptions]
    result = run(raw, assumptions, args.output, args.case, {str(p): sha(p) for p in paths}, args.nonlinear)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
