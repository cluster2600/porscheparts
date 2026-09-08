from decimal import Decimal, localcontext
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/flowbench-intake/audit_centroid_tet_trial.py'
SPEC = importlib.util.spec_from_file_location('centroid_independent_audit', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def render(points, tets, triangles=None):
    # Only synthetic exact integer/decimal witnesses; no real domain data.
    if triangles is None:
        faces = {}
        for nodes in tets.values():
            for face in audit.oriented_faces(nodes):
                faces.setdefault(tuple(sorted(face)), []).append(face)
        triangles = {i + 100: ((i % 3 + 1, i + 1), rows[0])
                     for i, rows in enumerate(v for v in faces.values() if len(v) == 1)}
    lines = ['$MeshFormat', '2.2 0 8', '$EndMeshFormat', '$PhysicalNames', '4',
             '2 1 "inlet"', '2 2 "receiver_outlet"', '2 3 "walls"', '3 100 "air"',
             '$EndPhysicalNames', '$Nodes', str(len(points))]
    lines.extend(str(n) + ' ' + ' '.join(map(str, xyz)) for n, xyz in sorted(points.items()))
    lines.extend(['$EndNodes', '$Elements', str(len(tets) + len(triangles))])
    lines.extend(' '.join(map(str, (tag, 2, len(labels), *labels, *nodes)))
                 for tag, (labels, nodes) in sorted(triangles.items()))
    lines.extend(' '.join(map(str, (tag, 4, 2, 100, 1, *nodes))) for tag, nodes in sorted(tets.items()))
    lines.extend(['$EndElements', ''])
    return '\n'.join(lines)


def fixture(cube=False):
    if cube:
        points = {1: (0, 0, 0), 2: (1, 0, 0), 3: (1, 1, 0), 4: (0, 1, 0),
                  5: (0, 0, 1), 6: (1, 0, 1), 7: (1, 1, 1), 8: (0, 1, 1)}
        tets = {1: (1, 2, 3, 7), 2: (1, 3, 4, 7), 3: (1, 4, 8, 7),
                4: (1, 8, 5, 7), 5: (1, 5, 6, 7), 6: (1, 6, 2, 7)}
    else:
        # Four retained children have degree3/4, attached to one degree1 tet.
        points = {1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1),
                  5: (0, 0, -1), 6: ('.25', '.25', '.25')}
        tets = {1: (6, 2, 3, 4), 2: (1, 6, 3, 4), 3: (1, 2, 6, 4),
                4: (1, 2, 3, 6), 5: (1, 3, 2, 5)}
    source = audit.parse_msh(render(points, tets))
    selected = {t: d for t, d in audit.topology(source)['degree'].items() if d <= 2}
    new_points = {n: list(tokens) for n, tokens in source['tokens'].items()}
    new_tets = {t: nodes for t, (_, nodes) in source['tets'].items() if t not in selected}
    rows = []; next_node = max(new_points) + 1; next_element = 1000
    for tid, degree in sorted(selected.items()):
        nodes = source['tets'][tid][1]
        with localcontext() as context:
            context.prec = 100
            center = [str(sum(Decimal(source['tokens'][n][i]) for n in nodes) / 4)
                      for i in range(3)]
        new_points[next_node] = center
        children = []
        for index in range(4):
            child = list(nodes); child[index] = next_node
            new_tets[next_element] = tuple(child); children.append(next_element)
            next_element += 1
        rows.append({'parent_element_id': tid, 'internal_face_count': degree,
                     'centroid_node_id': next_node, 'child_element_ids': children})
        next_node += 1
    candidate = audit.parse_msh(render(new_points, new_tets, source['triangles']))
    return source, candidate, rows


class CentroidIndependentAuditTests(unittest.TestCase):
    def test_degree_one_with_nonselected_neighbors_passes(self):
        source, candidate, rows = fixture()
        result = audit.audit_transform(source, candidate, rows)
        self.assertEqual(result['observed_selected_parents'], 1)
        self.assertEqual(result['unchanged_tetrahedra'], 4)
        self.assertEqual(result['candidate_tetrahedra'], 8)
        self.assertEqual(result['candidate_faces'] - result['source_faces'], 6)
        self.assertTrue(result['exact_rational_centroids_and_quarter_volumes'])
        self.assertFalse(result['observed_711_parents'])

    def test_all_degree_two_parents_selected_and_no_hanging_faces(self):
        source, candidate, rows = fixture(cube=True)
        result = audit.audit_transform(source, candidate, list(reversed(rows)))
        self.assertEqual(result['source_internal_face_degree_histogram'], {2: 6})
        self.assertEqual(result['observed_selected_parents'], 6)
        self.assertEqual(result['candidate_tetrahedra'], 24)
        self.assertEqual(result['float_volume_sum_delta'], 0.)
        self.assertTrue(result['true_boundary_and_all_internal_face_orientations_verified'])

    def test_same_float_but_changed_original_ASCII_is_rejected(self):
        source, candidate, rows = fixture()
        candidate['node_lines'][1] = '1 0.0 0 0\n'
        with self.assertRaisesRegex(ValueError, 'ASCII_record'):
            audit.audit_transform(source, candidate, rows)

    def test_boundary_record_or_labels_change_rejected(self):
        source, candidate, rows = fixture()
        tag = next(iter(candidate['triangles']))
        candidate['element_lines'][tag] += ' '
        with self.assertRaisesRegex(ValueError, 'boundary_element_record'):
            audit.audit_transform(source, candidate, rows)

    def test_retained_tet_record_change_rejected(self):
        source, candidate, rows = fixture()
        candidate['element_lines'][1] += ' '
        with self.assertRaisesRegex(ValueError, 'nonselected_tetrahedron'):
            audit.audit_transform(source, candidate, rows)

    def test_centroid_that_rounds_to_same_float_but_is_not_exact_rejected(self):
        source, candidate, rows = fixture()
        center = rows[0]['centroid_node_id']
        candidate['tokens'][center] = ('0.250000000000000000000000001', '.25', '-.25')
        self.assertEqual(float(candidate['tokens'][center][0]), candidate['points'][center][0])
        with self.assertRaisesRegex(ValueError, 'exact_decimal_mean'):
            audit.audit_transform(source, candidate, rows)

    def test_child_inversion_rejected(self):
        source, candidate, rows = fixture()
        child = rows[0]['child_element_ids'][0]
        labels, (a, b, c, d) = candidate['tets'][child]
        candidate['tets'][child] = (labels, (b, a, c, d))
        with self.assertRaisesRegex(ValueError, 'oriented_volume'):
            audit.audit_transform(source, candidate, rows)

    def test_child_physical_or_geometric_tags_not_inherited_rejected(self):
        source, candidate, rows = fixture()
        child = rows[0]['child_element_ids'][0]
        candidate['tets'][child] = ((100, 2), candidate['tets'][child][1])
        with self.assertRaisesRegex(ValueError, 'labels_not_inherited'):
            audit.audit_transform(source, candidate, rows)

    def test_omitted_parent_and_forged_mapping_rejected(self):
        source, candidate, rows = fixture(cube=True)
        with self.assertRaisesRegex(ValueError, 'mapping_count'):
            audit.audit_transform(source, candidate, rows[:-1])
        rows[0]['internal_face_count'] = 1
        with self.assertRaisesRegex(ValueError, 'mapping_differs'):
            audit.audit_transform(source, candidate, rows)

    def test_omitted_transformation_cannot_pass_with_empty_producer_mapping(self):
        source, _, _ = fixture(cube=True)
        with self.assertRaisesRegex(ValueError, 'centroid_or_child_count'):
            audit.audit_transform(source, source, [])

    def test_line_endings_are_not_silently_normalized(self):
        source, candidate, rows = fixture()
        candidate['node_lines'][1] = candidate['node_lines'][1].replace('\n', '\r\n')
        with self.assertRaisesRegex(ValueError, 'ASCII_record'):
            audit.audit_transform(source, candidate, rows)

    def test_duplicate_child_face_cannot_replace_missing_child(self):
        source, candidate, rows = fixture()
        one, two = rows[0]['child_element_ids'][:2]
        candidate['tets'][two] = candidate['tets'][one]
        with self.assertRaisesRegex(ValueError, 'faces_not_bijective'):
            audit.audit_transform(source, candidate, rows)

    def test_source_boundary_must_be_real_tetra_exterior(self):
        source, candidate, rows = fixture()
        triangle = next(iter(source['triangles']))
        labels, (a, b, c) = source['triangles'][triangle]
        source['triangles'][triangle] = (labels, (b, a, c))
        with self.assertRaisesRegex(ValueError, 'true_outward'):
            audit.audit_transform(source, candidate, rows)

    def test_bindings_reject_cross_domain_or_source_or_inherited_review(self):
        producer = {'schema': 'm64-native-tet-central-subdivision/v1',
                    'source_mesh_sha256': audit.SOURCE_MESH_SHA, 'candidate_mesh_sha256': 'a' * 64,
                    'native_domain_sha256': audit.DOMAIN_SHA}
        inherited = {'schema': 'm64-intake-pilot-review/v1', 'mesh_sha256': audit.SOURCE_MESH_SHA,
                     'native_domain_sha256': audit.DOMAIN_SHA, 'approved_for_mesh_diagnostic': True,
                     'boundary_assignment_accepted': True, 'solver_execution_authorized': False}
        audit.validate_bindings(producer, inherited, audit.SOURCE_MESH_SHA, 'a' * 64, audit.INHERITED_REVIEW_SHA)
        for field in ('source_mesh_sha256', 'candidate_mesh_sha256', 'native_domain_sha256'):
            changed = dict(producer); changed[field] = 'b' * 64
            with self.assertRaises(ValueError):
                audit.validate_bindings(changed, inherited, audit.SOURCE_MESH_SHA, 'a' * 64, audit.INHERITED_REVIEW_SHA)
        with self.assertRaisesRegex(ValueError, 'pin_mismatch'):
            audit.validate_bindings(producer, inherited, audit.SOURCE_MESH_SHA, 'a' * 64, 'b' * 64)
        changed = dict(inherited); changed['boundary_assignment_accepted'] = False
        with self.assertRaisesRegex(ValueError, 'authority_mismatch'):
            audit.validate_bindings(producer, changed, audit.SOURCE_MESH_SHA, 'a' * 64, audit.INHERITED_REVIEW_SHA)

    def test_reader_rejects_duplicate_id_and_nonfinite_coordinates(self):
        text = render({1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1)},
                      {1: (1, 2, 3, 4)})
        with self.assertRaisesRegex(ValueError, 'invalid_node'):
            audit.parse_msh(text.replace('2 1 0 0\n', '1 1 0 0\n'))
        with self.assertRaisesRegex(ValueError, 'invalid_node'):
            audit.parse_msh(text.replace('2 1 0 0\n', '2 nan 0 0\n'))


if __name__ == '__main__':
    unittest.main()
