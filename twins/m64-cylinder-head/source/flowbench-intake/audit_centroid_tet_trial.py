#!/usr/bin/env python3
"""Independent MSH2.2 central-subdivision audit; conversion/checkMesh only.

No producer code is imported. Decimal coordinates of the selected parents and
their children are checked as exact rational numbers. This is an integrity
audit, not a mesh-quality waiver, CFD run or new CAD/physical validation.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import time

SOURCE_MESH_SHA = 'c0cbb257619ce378a9c9274da305d6bf34ce55dd4913a55cf122649ec45326ca'
DOMAIN_SHA = 'fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
INHERITED_REVIEW_SHA = '48c9803b12330e3dd29fb4cd015772011cda83469f0b1ef566fec7d16d13380b'
PHYSICAL_NAMES = {(2, 1): 'inlet', (2, 2): 'receiver_outlet',
                  (2, 3): 'walls', (3, 100): 'air'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def parse_msh(text):
    """Strict independent reader retaining each original ASCII record."""
    sections = {}
    lines = iter(text.splitlines(keepends=True))
    for line in lines:
        name = line.strip()
        require(name.startswith('$') and not name.startswith('$End'), 'unexpected_MSH_line')
        name = name[1:]
        require(name not in sections, 'duplicate_MSH_section')
        rows = []
        for row in lines:
            if row.strip() == '$End' + name:
                break
            rows.append(row)
        else:
            raise ValueError('unterminated_MSH_section')
        sections[name] = rows
    require(set(sections) == {'MeshFormat', 'PhysicalNames', 'Nodes', 'Elements'},
            'only_four_pilot_MSH_sections_supported')
    require([r.strip() for r in sections['MeshFormat']] == ['2.2 0 8'], 'MSH22_ASCII_required')

    def counted(name):
        rows = sections[name]
        require(bool(rows) and int(rows[0]) == len(rows) - 1, 'MSH_count_mismatch')
        return rows[1:]

    names = {}
    for row in counted('PhysicalNames'):
        dim, tag, name = row.split(maxsplit=2)
        key = int(dim), int(tag)
        require(key not in names, 'duplicate_physical_name')
        names[key] = json.loads(name)
    require(names == PHYSICAL_NAMES, 'physical_names_contract_mismatch')
    points, tokens, node_lines = {}, {}, {}
    for row in counted('Nodes'):
        values = row.split()
        require(len(values) == 4, 'invalid_node_record')
        tag = int(values[0]); xyz = tuple(map(float, values[1:]))
        require(tag > 0 and tag not in points and all(map(math.isfinite, xyz)), 'invalid_node')
        points[tag], tokens[tag], node_lines[tag] = xyz, tuple(values[1:]), row
    elements, tets, triangles, element_lines = {}, {}, {}, {}
    for row in counted('Elements'):
        values = list(map(int, row.split()))
        require(len(values) >= 5, 'short_element_record')
        tag, kind, ntag = values[:3]
        require(tag > 0 and tag not in elements and ntag >= 2, 'invalid_element_id_or_tags')
        require(kind in (2, 4), 'unsupported_element_type')
        nodes = tuple(values[3 + ntag:]); labels = tuple(values[3:3 + ntag])
        require(len(nodes) == (3 if kind == 2 else 4) and len(set(nodes)) == len(nodes)
                and all(n in points for n in nodes), 'invalid_element_nodes')
        require(len(labels) == ntag and labels[1] > 0 and
                ((kind == 2 and labels[0] in (1, 2, 3)) or
                 (kind == 4 and labels[0] == 100)), 'unclassified_element')
        elements[tag] = (kind, labels, nodes)
        (triangles if kind == 2 else tets)[tag] = (labels, nodes)
        element_lines[tag] = row
    require(bool(tets) and bool(triangles), 'empty_mesh')
    used = {n for _, _, ns in elements.values() for n in ns}
    require(used == set(points), 'orphan_nodes')
    require({labels[0] for labels, _ in triangles.values()} == {1, 2, 3}, 'empty_patch')
    return {'points': points, 'tokens': tokens, 'node_lines': node_lines,
            'tets': tets, 'triangles': triangles, 'element_lines': element_lines,
            'fixed_sections': {n: sections[n] for n in ('MeshFormat', 'PhysicalNames')}}


def oriented_faces(nodes):
    a, b, c, d = nodes
    return ((b, c, d), (a, d, c), (a, b, d), (a, c, b))


def orientation(triangle):
    return -1 if sum(triangle[i] > triangle[j] for i in range(3)
                     for j in range(i + 1, 3)) % 2 else 1


def determinant6(vertices):
    a, b, c, d = vertices
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    w = tuple(d[i] - a[i] for i in range(3))
    return (u[0] * (v[1] * w[2] - v[2] * w[1])
            - u[1] * (v[0] * w[2] - v[2] * w[0])
            + u[2] * (v[0] * w[1] - v[1] * w[0]))


def topology(mesh):
    incidences, connectivity = {}, set()
    float_volumes = []
    for tid, (_, nodes) in mesh['tets'].items():
        key = tuple(sorted(nodes))
        require(key not in connectivity, 'duplicate_tetrahedron')
        connectivity.add(key)
        value = determinant6([mesh['points'][n] for n in nodes]) / 6
        require(math.isfinite(value) and value > 0, 'nonpositive_or_nonfinite_float_tetra_volume')
        float_volumes.append(value)
        for face in oriented_faces(nodes):
            key = tuple(sorted(face)); sign = orientation(face)
            if key not in incidences:
                incidences[key] = [1, sign, tid]
            else:
                record = incidences[key]
                record[0] += 1; record[1] += sign
                require(record[0] == 2 and record[1] == 0, 'internal_face_not_two_opposite_incidents')
    boundary = {key: record for key, record in incidences.items() if record[0] == 1}
    exterior = {}
    for _, (_, nodes) in mesh['triangles'].items():
        key = tuple(sorted(nodes))
        require(key not in exterior, 'duplicate_boundary_triangle')
        exterior[key] = orientation(nodes)
    require(set(exterior) == set(boundary) and
            all(exterior[k] == boundary[k][1] for k in exterior),
            'saved_triangles_not_true_outward_tetra_boundary')
    degree = {tid: 4 for tid in mesh['tets']}
    for _, _, tid in boundary.values():
        degree[tid] -= 1
    return {'degree': degree, 'unique_faces': len(incidences),
            'internal_faces': len(incidences) - len(boundary),
            'boundary_faces': len(boundary), 'float_volume_sum': math.fsum(float_volumes)}


def audit_transform(source, candidate, producer_rows):
    """Infer the parent/child mapping independently, then compare producer rows."""
    original = topology(source)
    selected = {tid for tid, degree in original['degree'].items() if degree <= 2}
    retained = set(source['tets']) - selected
    require(source['fixed_sections'] == candidate['fixed_sections'], 'fixed_MSH_sections_changed')
    require(set(source['points']) <= set(candidate['points']) and
            all(source['node_lines'][n] == candidate['node_lines'][n] for n in source['points']),
            'original_node_ASCII_record_changed_or_missing')
    require(source['triangles'] == candidate['triangles'] and
            all(source['element_lines'][e] == candidate['element_lines'][e] for e in source['triangles']),
            'original_boundary_element_record_changed')
    require(retained <= set(candidate['tets']) and all(
        source['element_lines'][e] == candidate['element_lines'][e] for e in retained),
        'nonselected_tetrahedron_changed_or_missing')
    new_nodes = set(candidate['points']) - set(source['points'])
    children = set(candidate['tets']) - retained
    require(len(new_nodes) == len(selected) and len(children) == 4 * len(selected),
            'centroid_or_child_count_mismatch')
    parents_by_nodes = {tuple(sorted(source['tets'][t][1])): t for t in selected}
    groups = defaultdict(list)
    for cid in children:
        nodes = candidate['tets'][cid][1]
        centers = set(nodes) & new_nodes
        require(len(centers) == 1, 'child_must_have_exactly_one_new_centroid')
        groups[next(iter(centers))].append(cid)
    require(set(groups) == new_nodes, 'unused_or_shared_centroid_mismatch')
    observed, parent_seen = [], set()
    rational_points = {}

    def rational(mesh, tag):
        key = id(mesh), tag
        if key not in rational_points:
            rational_points[key] = tuple(Fraction(t) for t in mesh['tokens'][tag])
        return rational_points[key]

    max_float_error, max_float_relative, max_centroid_float_error = 0., 0., 0.
    for center, child_ids in sorted(groups.items()):
        require(len(child_ids) == 4, 'centroid_does_not_have_four_children')
        old_triples = [tuple(sorted(n for n in candidate['tets'][c][1] if n != center))
                       for c in child_ids]
        union = tuple(sorted({n for triple in old_triples for n in triple}))
        require(union in parents_by_nodes, 'children_do_not_belong_to_one_selected_parent')
        pid = parents_by_nodes[union]
        require(pid not in parent_seen, 'selected_parent_represented_twice')
        parent_seen.add(pid)
        expected_triples = {tuple(n for n in union if n != missing) for missing in union}
        require(len(set(old_triples)) == 4 and set(old_triples) == expected_triples,
                'four_parent_faces_not_bijective')
        labels, parent_nodes = source['tets'][pid]
        require(all(candidate['tets'][c][0] == labels for c in child_ids), 'child_MSH_labels_not_inherited')
        coords = [rational(source, n) for n in parent_nodes]
        expected_center = tuple(sum(p[i] for p in coords) / 4 for i in range(3))
        require(rational(candidate, center) == expected_center, 'centroid_not_exact_decimal_mean')
        parent_v6 = determinant6(coords)
        require(parent_v6 > 0, 'nonpositive_exact_parent_volume')
        for cid in child_ids:
            nodes = candidate['tets'][cid][1]
            exact_v6 = determinant6([rational(candidate, n) for n in nodes])
            require(exact_v6 == parent_v6 / 4, 'child_exact_oriented_volume_not_parent_quarter')
            saved_float = determinant6([candidate['points'][n] for n in nodes]) / 6
            expected_float = float(parent_v6 / 24)
            require(saved_float > 0 and math.isfinite(saved_float), 'nonpositive_float_child_volume')
            error = abs(saved_float - expected_float)
            max_float_error = max(max_float_error, error)
            max_float_relative = max(max_float_relative, error / abs(expected_float))
        max_centroid_float_error = max(max_centroid_float_error, *(
            abs(candidate['points'][center][i] - float(expected_center[i])) for i in range(3)))
        observed.append({'parent_element_id': pid, 'internal_face_count': original['degree'][pid],
                         'centroid_node_id': center, 'child_element_ids': sorted(child_ids)})
    require(parent_seen == selected, 'selected_parent_coverage_incomplete')
    require(isinstance(producer_rows, list) and len(producer_rows) == len(observed), 'producer_mapping_count_mismatch')
    normalized = []
    for row in producer_rows:
        require(isinstance(row, dict) and all(type(row.get(k)) is int for k in
                ('parent_element_id', 'internal_face_count', 'centroid_node_id')) and
                isinstance(row.get('child_element_ids'), list) and
                all(type(v) is int for v in row['child_element_ids']), 'invalid_producer_mapping')
        normalized.append({k: sorted(row[k]) if k == 'child_element_ids' else row[k]
                           for k in observed[0]} if observed else {})
    require(sorted(normalized, key=lambda r: r['parent_element_id']) ==
            sorted(observed, key=lambda r: r['parent_element_id']), 'producer_mapping_differs_from_independent_mapping')
    after = topology(candidate)
    require(len(candidate['tets']) == len(source['tets']) + 3 * len(selected) and
            after['unique_faces'] == original['unique_faces'] + 6 * len(selected) and
            after['internal_faces'] == original['internal_faces'] + 6 * len(selected),
            'global_subdivision_topology_counts_mismatch')
    mapping_bytes = json.dumps(sorted(observed, key=lambda r: r['parent_element_id']),
                               sort_keys=True, separators=(',', ':')).encode()
    return {'selection': 'all_source_tetrahedra_with_internal_face_degree_le_2',
            'source_internal_face_degree_histogram': dict(sorted(Counter(original['degree'].values()).items())),
            'observed_selected_parents': len(selected),
            'observed_711_parents': len(selected) == 711,
            'source_tetrahedra': len(source['tets']), 'candidate_tetrahedra': len(candidate['tets']),
            'unchanged_tetrahedra': len(retained), 'children': len(children), 'new_centroid_nodes': len(new_nodes),
            'original_node_ASCII_records_unchanged': len(source['points']),
            'original_boundary_ASCII_records_unchanged': len(source['triangles']),
            'true_boundary_and_all_internal_face_orientations_verified': True,
            'source_faces': original['unique_faces'], 'candidate_faces': after['unique_faces'],
            'exact_rational_centroids_and_quarter_volumes': True,
            'exact_total_volume_conservation_by_partition_and_unchanged_tetrahedra': True,
            'maximum_child_float_volume_absolute_error_scan_units_cubed': max_float_error,
            'maximum_child_float_volume_relative_error': max_float_relative,
            'maximum_saved_centroid_float_delta_from_rounded_exact_mean': max_centroid_float_error,
            'source_float_volume_sum': original['float_volume_sum'],
            'candidate_float_volume_sum': after['float_volume_sum'],
            'float_volume_sum_delta': after['float_volume_sum'] - original['float_volume_sum'],
            'independent_mapping_sha256': hashlib.sha256(mapping_bytes).hexdigest(),
            'producer_mapping_independently_reproduced': True}


def validate_bindings(producer, inherited, source_sha, candidate_sha, inherited_sha):
    require(source_sha == SOURCE_MESH_SHA and inherited_sha == INHERITED_REVIEW_SHA,
            'source_mesh_or_inherited_review_pin_mismatch')
    require(producer.get('schema') == 'm64-native-tet-central-subdivision/v1' and
            producer.get('source_mesh_sha256') == source_sha and
            producer.get('candidate_mesh_sha256') == candidate_sha and
            producer.get('native_domain_sha256') == DOMAIN_SHA, 'producer_input_output_binding_mismatch')
    require(inherited.get('schema') == 'm64-intake-pilot-review/v1' and
            inherited.get('mesh_sha256') == source_sha and inherited.get('native_domain_sha256') == DOMAIN_SHA and
            inherited.get('approved_for_mesh_diagnostic') is True and
            inherited.get('boundary_assignment_accepted') is True and
            inherited.get('solver_execution_authorized') is False, 'inherited_boundary_authority_mismatch')


def main(args):
    started = time.monotonic()
    require(not args.output.exists(), 'new_review_output_required')
    paths = {'source_mesh': args.source_mesh, 'candidate_mesh': args.candidate_mesh,
             'producer_report': args.producer_report, 'inherited_review': args.inherited_review,
             'auditor_source': Path(__file__)}
    hashes = {name: sha(path) for name, path in paths.items()}
    review = {'schema': 'm64-intake-pilot-review/v1', 'status': 'rejected_or_incomplete',
              'approved_for_mesh_diagnostic': False, 'boundary_assignment_accepted': False,
              'approved_for_diagnostic_cfd': False, 'solver_executed': False,
              'solver_execution_authorized': False, 'CFD_executed': False, 'CFD_qualified': False,
              'manufacturing_authorized': False, 'mesh_sha256': hashes['candidate_mesh'],
              'native_domain_sha256': DOMAIN_SHA, 'inputs_sha256': hashes,
              'scope': 'Central subdivision integrity; conversion and checkMesh only. No source quality criteria waived.',
              'native_geometry_reread_or_changed': False,
              'quality_metrics_not_recomputed_or_accepted': True,
              'C0_interface_coverage_not_qualified_by_this_review': True,
              'source_4731_low_determinants_with_degree_3_or_4_not_repaired_by_this_transformation': True}
    try:
        producer = json.loads(args.producer_report.read_text())
        inherited = json.loads(args.inherited_review.read_text())
        validate_bindings(producer, inherited, hashes['source_mesh'], hashes['candidate_mesh'], hashes['inherited_review'])
        # read_text() would silently normalize line endings before exact checks.
        source = parse_msh(args.source_mesh.read_bytes().decode('ascii'))
        candidate = parse_msh(args.candidate_mesh.read_bytes().decode('ascii'))
        review['independent_transformation_audit'] = audit_transform(source, candidate, producer.get('parent_children_private'))
        review['inherited_source_quality_not_a_candidate_quality_measure'] = inherited['reported_MSH_reread_quality']
        review['producer_source_sha256_declared_not_executed_by_auditor'] = producer.get('source_sha256')
        review['all_inputs_unchanged'] = all(sha(path) == hashes[name] for name, path in paths.items())
        require(review['all_inputs_unchanged'], 'input_changed_during_audit')
        review.update(status='transformation_verified_conversion_diagnostic_only',
                      approved_for_mesh_diagnostic=True, boundary_assignment_accepted=True)
    except (ValueError, KeyError, TypeError, OSError) as error:
        review['error'] = str(error)
        review['all_inputs_unchanged'] = all(path.exists() and sha(path) == hashes[name] for name, path in paths.items())
    review['elapsed_seconds'] = time.monotonic() - started
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(review, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'status': review['status'], 'approved_for_mesh_diagnostic': review['approved_for_mesh_diagnostic'],
                      'review_sha256': sha(args.output)}))
    return 0 if review['approved_for_mesh_diagnostic'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-mesh', 'candidate-mesh', 'producer-report', 'inherited-review', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
