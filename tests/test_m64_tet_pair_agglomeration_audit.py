from collections import Counter
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/flowbench-intake/audit_tet_pair_agglomeration.py'
SPEC = importlib.util.spec_from_file_location('independent_pair_audit', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def fixture(pairs=((0, 1),), permutations=True):
    # Four tetrahedra inside one tetrahedron, plus a nonselected neighbour.
    # Merging (0,1) and (2,3) retains several distinct shared triangles.
    points = [tuple(map(float, p)) for p in ((0, 0, 0), (1, 0, 0), (0, 1, 0),
              (0, 0, 1), ('.25', '.25', '.25'), (0, 0, -1))]
    tets = ((4, 1, 2, 3), (0, 4, 2, 3), (0, 1, 4, 3), (0, 1, 2, 4), (0, 2, 1, 5))
    found = {}
    for cell, (a, b, c, d) in enumerate(tets):
        for face in ((b, c, d), (a, d, c), (a, b, d), (a, c, b)):
            key = tuple(sorted(face))
            if key in found:
                found[key][2] = cell
            else:
                found[key] = [face, cell, None]
    rows = [r for r in found.values() if r[2] is not None] + [r for r in found.values() if r[2] is None]
    internal = sum(r[2] is not None for r in rows)
    boundary = len(rows) - internal; sizes = (boundary - 2, 1, 1)
    cursor = internal; patches = []
    for name, size, kind in zip(('walls', 'receiver_outlet', 'inlet'), sizes, ('wall', 'patch', 'patch')):
        patches.append((name, cursor, size, {'type': kind, 'physicalType': 'patch'})); cursor += size
    source = {'points': points, 'faces': [r[0] for r in rows], 'owner': [r[1] for r in rows],
              'neighbour': [r[2] for r in rows[:internal]], 'cells': len(tets), 'patches': patches, 'zone': list(range(len(tets)))}
    requested = [next(i for i, r in enumerate(rows[:internal]) if (r[1], r[2]) == tuple(sorted(pair))) for pair in pairs]
    grouped = [set(pair) for pair in pairs]
    grouped += [{c} for c in range(len(tets)) if not any(c in pair for pair in pairs)]
    if permutations:
        grouped.reverse()
    cm = [max(g) for g in grouped]; old_new = [next(i for i, g in enumerate(grouped) if c in g) for c in range(len(tets))]
    pm = list(reversed(range(len(points)))) if permutations else list(range(len(points)))
    old_point_new = {old: new for new, old in enumerate(pm)}
    kept = [i for i in range(internal) if i not in requested]
    if permutations:
        kept.reverse()
    candidate_patches = []; cursor = len(kept)
    for name, start, size, fields in patches:
        indices = list(range(start, start + size))
        kept.extend(reversed(indices) if permutations else indices)
        candidate_patches.append((name, cursor, size, dict(fields))); cursor += size
    cfaces, owner, neighbour = [], [], []
    for f in kept:
        face = source['faces'][f]; a = old_new[source['owner'][f]]
        if f < internal:
            b = old_new[source['neighbour'][f]]
            if a > b:
                a, b, face = b, a, face[::-1]
            neighbour.append(b)
        cfaces.append(tuple(old_point_new[p] for p in face)); owner.append(a)
    candidate = {'points': [points[p] for p in pm], 'faces': cfaces, 'owner': owner,
                 'neighbour': neighbour, 'cells': len(grouped), 'patches': candidate_patches,
                 'zone': list(reversed(range(len(grouped))))}
    maps = dict(zip(audit.MAPS, (pm, kept, cm, old_new)))
    return source, candidate, requested, maps


def write_foam(path, cls, body):
    path.write_text('FoamFile\n{\n format ascii;\n class ' + cls + ';\n object test;\n}\n' + body + '\n')


def write_case(root, mesh):
    folder = root / 'constant/polyMesh'; folder.mkdir(parents=True)
    write_foam(folder / 'points', 'vectorField', str(len(mesh['points'])) + '\n(\n' +
               '\n'.join('(' + ' '.join(map(str, p)) + ')' for p in mesh['points']) + '\n)')
    write_foam(folder / 'faces', 'faceList', str(len(mesh['faces'])) + '\n(\n' +
               '\n'.join('3(' + ' '.join(map(str, p)) + ')' for p in mesh['faces']) + '\n)')
    for name in ('owner', 'neighbour'):
        write_foam(folder / name, 'labelList', str(len(mesh[name])) + '(' + ' '.join(map(str, mesh[name])) + ')')
    blocks = []
    for name, start, size, fields in mesh['patches']:
        blocks.append(name + '\n{\n' + '\n'.join(k + ' ' + v + ';' for k, v in fields.items()) +
                      '\nnFaces ' + str(size) + ';\nstartFace ' + str(start) + ';\n}')
    write_foam(folder / 'boundary', 'polyBoundaryMesh', '3\n(\n' + '\n'.join(blocks) + '\n)')
    write_foam(folder / 'cellZones', 'cellZoneList', '1\n(\nair\n{cellLabels List<label> ' +
               str(len(mesh['zone'])) + '(' + ' '.join(map(str, mesh['zone'])) + ');}\n)')


class TetPairAuditTests(unittest.TestCase):
    def check_rejected(self, expected, change, **kw):
        source, candidate, requested, maps = fixture(**kw)
        change(source, candidate, requested, maps)
        with self.assertRaisesRegex(ValueError, expected):
            audit.audit(source, candidate, requested, maps)

    def test_single_pair_with_reordered_nodes_faces_cells_and_owner_flips(self):
        result = audit.audit(*fixture())
        self.assertEqual(result['paired_cells'], 1)
        self.assertEqual(result['unchanged_singleton_cells'], 3)
        self.assertTrue(result['exact_rational_pair_volumes_and_total_conservation_by_partition'])
        self.assertFalse(result['global_source_self_intersection_absence_proven'])

    def test_multiple_shared_faces_between_new_cells_are_not_rejected(self):
        args = fixture(pairs=((0, 1), (2, 3)))
        self.assertGreater(max(Counter(zip(args[1]['owner'], args[1]['neighbour'])).values()), 1)
        self.assertEqual(audit.audit(*args)['paired_cells'], 2)

    def test_cell_map_may_select_either_parent_as_master(self):
        source, candidate, requested, maps = fixture()
        new = maps[audit.MAPS[3]][0]
        maps[audit.MAPS[2]][new] = 0
        self.assertTrue(audit.audit(source, candidate, requested, maps)['maps_independently_reproduced'])

    def test_one_binary64_ulp_coordinate_change_is_rejected(self):
        def change(s, c, r, m):
            i = m[audit.MAPS[0]].index(1)
            c['points'][i] = (math.nextafter(1., 2.), 0., 0.)
        self.check_rejected('exact_point', change)

    def test_signed_zero_bit_change_is_rejected(self):
        def change(s, c, r, m):
            i = m[audit.MAPS[0]].index(0)
            c['points'][i] = (-0., 0., 0.)
        self.check_rejected('exact_point', change)

    def test_12_to_17_digit_serialization_preserves_loaded_binary64(self):
        source, candidate, requested, maps = fixture()
        # Non-dyadic coordinates: decimal token identity is deliberately not
        # claimed, but every loaded binary64 must remain identical.
        source['points'] = [tuple(x/10 for x in p) for p in source['points']]
        candidate['points'] = [source['points'][i] for i in maps[audit.MAPS[0]]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, mesh, precision in (('source', source, 12), ('candidate', candidate, 17)):
                write_case(root/name, mesh)
                body = str(len(mesh['points'])) + '(' + ' '.join(
                    '(' + ' '.join(format(x, '.' + str(precision) + 'g') for x in p) + ')'
                    for p in mesh['points']) + ')'
                write_foam(root/name/'constant/polyMesh/points', 'vectorField', body)
            result = audit.audit(audit.read_mesh(root/'source'), audit.read_mesh(root/'candidate'), requested, maps)
            self.assertTrue(result['point_coordinates_bit_exact_binary64'])
            self.assertFalse(result['decimal_token_identity_claimed'])
            self.assertEqual(result['rational_coordinate_basis'], 'exact_rationals_of_loaded_binary64_values')

    def test_duplicate_point_map_rejected(self):
        self.check_rejected('point_map_not_bijective', lambda s,c,r,m: m[audit.MAPS[0]].__setitem__(0, m[audit.MAPS[0]][1]))

    def test_added_point_rejected(self):
        self.check_rejected('point_map_not_bijective', lambda s,c,r,m: c['points'].append(c['points'][0]))

    def test_duplicate_face_map_rejected(self):
        self.check_rejected('remove_only_requested', lambda s,c,r,m: m[audit.MAPS[1]].__setitem__(0, m[audit.MAPS[1]][1]))

    def test_overlapping_requested_pairs_rejected(self):
        def change(s,c,r,m):
            r.append(next(f for f,n in enumerate(s['neighbour']) if 0 in (s['owner'][f], n) and f not in r))
        self.check_rejected('pairs_must_be_disjoint', change)

    def test_duplicate_and_empty_requests_rejected(self):
        self.check_rejected('unique_requested', lambda s,c,r,m: r.append(r[0]))
        self.check_rejected('unique_requested', lambda s,c,r,m: r.clear())

    def test_boundary_face_cannot_be_removed(self):
        self.check_rejected('must_be_internal', lambda s,c,r,m: r.__setitem__(0, len(s['neighbour'])))

    def test_old_to_new_forgery_rejected(self):
        self.check_rejected('independently_reproduced', lambda s,c,r,m: m[audit.MAPS[3]].__setitem__(0, 0))

    def test_duplicate_cell_group_rejected(self):
        self.check_rejected('group_represented_twice', lambda s,c,r,m: m[audit.MAPS[2]].__setitem__(0, m[audit.MAPS[2]][1]))

    def test_owner_flip_without_triangle_reversal_rejected(self):
        self.check_rejected('orientation_changed|flip_inconsistent', lambda s,c,r,m: c['faces'].__setitem__(0, c['faces'][0][::-1]))

    def test_wrong_retained_triangle_rejected(self):
        self.check_rejected('orientation_changed|flip_inconsistent', lambda s,c,r,m: c['faces'].__setitem__(0, c['faces'][1]))

    def test_wrong_owner_rejected(self):
        self.check_rejected('flip_inconsistent', lambda s,c,r,m: c['owner'].__setitem__(0, (c['owner'][0]+1) % c['cells']))

    def test_patch_type_change_rejected(self):
        self.check_rejected('patch_label', lambda s,c,r,m: c['patches'][0][3].__setitem__('type', 'patch'))

    def test_native_wall_group_serialization_equivalence(self):
        source, candidate, requested, maps = fixture()
        candidate['patches'][0][3]['inGroups'] = 'List<word> 1(wall)'
        result = audit.audit(source, candidate, requested, maps)
        self.assertTrue(result['patch_groups_compared_as_native_wall_default_union_only'])

    def test_wall_custom_group_retained_alongside_native_default(self):
        source, candidate, requested, maps = fixture()
        source['patches'][0][3]['inGroups'] = '(custom)'
        candidate['patches'][0][3]['inGroups'] = 'List<word> 2(wall custom)'
        self.assertTrue(audit.audit(source, candidate, requested, maps)['each_pair_has_exact_six_face_union'])

    def test_extra_wall_group_rejected(self):
        self.check_rejected('patch_label', lambda s,c,r,m: c['patches'][0][3].__setitem__('inGroups', '2(wall added)'))

    def test_removed_wall_custom_group_rejected(self):
        def change(s,c,r,m):
            s['patches'][0][3]['inGroups'] = '2(wall custom)'
            c['patches'][0][3]['inGroups'] = '1(wall)'
        self.check_rejected('patch_label', change)

    def test_nonwall_group_is_not_given_wall_default(self):
        self.check_rejected('patch_label', lambda s,c,r,m: c['patches'][1][3].__setitem__('inGroups', '1(wall)'))

    def test_other_patch_metadata_stays_strict(self):
        self.check_rejected('patch_label', lambda s,c,r,m: c['patches'][0][3].__setitem__('physicalType', 'different'))

    def test_malformed_wall_group_count_rejected(self):
        self.check_rejected('invalid_wall_group', lambda s,c,r,m: c['patches'][0][3].__setitem__('inGroups', '2(wall)'))

    def test_duplicate_wall_group_rejected(self):
        self.check_rejected('invalid_wall_group', lambda s,c,r,m: c['patches'][0][3].__setitem__('inGroups', '2(wall wall)'))

    def test_patch_membership_change_rejected(self):
        def change(s,c,r,m):
            name, start, count, fields = c['patches'][0]
            c['patches'][0] = (name, start+1, count, fields)
        self.check_rejected('patch_label', change)

    def test_cell_zone_omission_rejected(self):
        self.check_rejected('cell_zone', lambda s,c,r,m: c['zone'].pop())

    def test_source_not_outward_rejected(self):
        self.check_rejected('source_tetrahedron', lambda s,c,r,m: s['faces'].__setitem__(0, s['faces'][0][::-1]))

    def test_source_cell_not_tetra_rejected(self):
        self.check_rejected('source_cell_not_a_tetrahedron', lambda s,c,r,m: s['faces'].__setitem__(0, s['faces'][1]))

    def test_actual_ASCII_reader_and_maps_accept_whitespace_layouts(self):
        source, candidate, requested, maps = fixture(pairs=((0, 1), (2, 3)))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); write_case(root/'source', source); write_case(root/'candidate', candidate)
            self.assertEqual(audit.read_mesh(root/'source'), source)
            result = audit.audit(audit.read_mesh(root/'source'), audit.read_mesh(root/'candidate'), requested, maps)
            self.assertTrue(result['each_pair_has_exact_six_face_union'])
            write_foam(root/'map', 'labelList', '3(2 0 1)')
            self.assertEqual(audit.labels(root/'map'), [2,0,1])

    def test_binary_and_directive_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'map'; write_foam(path, 'labelList', '1(0)')
            path.write_text(path.read_text().replace('ascii', 'binary'))
            with self.assertRaisesRegex(ValueError, 'ASCII_FOAM'):
                audit.labels(path)
            write_foam(path, 'labelList', '1(0)\n#include "other"')
            with self.assertRaisesRegex(ValueError, 'plain_FOAM'):
                audit.labels(path)

    def test_map_count_and_class_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'map'; write_foam(path, 'labelList', '2(0)')
            with self.assertRaisesRegex(ValueError, 'count_mismatch'):
                audit.labels(path)
            write_foam(path, 'faceSet', '1(0)')
            with self.assertRaisesRegex(ValueError, 'class_mismatch'):
                audit.labels(path)

    def test_additional_zone_or_duplicate_air_cell_rejected(self):
        source, _, _, _ = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); write_case(root, source)
            write_foam(root/'constant/polyMesh/pointZones', 'pointZoneList', '1(foo {})')
            with self.assertRaisesRegex(ValueError, 'unexpected_point_or_face_zone'):
                audit.read_mesh(root)
            write_foam(root/'constant/polyMesh/pointZones', 'pointZoneList', '0()')
            zone = root/'constant/polyMesh/cellZones'
            zone.write_text(zone.read_text().replace('0 1 2 3 4', '0 1 2 3 3'))
            with self.assertRaisesRegex(ValueError, 'every_cell_once'):
                audit.read_mesh(root)


if __name__ == '__main__':
    unittest.main()
