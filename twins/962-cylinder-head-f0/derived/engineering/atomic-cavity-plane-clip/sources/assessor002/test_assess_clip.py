"""Pure synthetic oracle tests, prepared unrun; no CGAL/NumPy import or process."""
from collections import Counter
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('literal_plane_assessor', HERE/'assess_clip.py')
M = importlib.util.module_from_spec(spec)
old = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    spec.loader.exec_module(M)
finally:
    sys.dont_write_bytecode = old


class LiteralOracleTests(unittest.TestCase):
    def data(self, name):
        case = next(c for c in json.loads((M.PREP/'fixture-expectations.json').read_text())['cases'] if c['name'] == name)
        source = M.read(M.ROOT/case['input_relative'])
        points = [tuple(F(v) for v in p) for p in case['points']]
        if name != 'above-noop':
            points = [(x, y, max(z, F(0))) for x, y, z in points]
        rows = [struct.pack('<ddd', *p) for p in points]
        lookup = {r: i for i, r in enumerate(source[0])}
        ids = [lookup.get(r, M.MAX_ID) for r in rows]
        expected = dict(case['expected_output'], Euler=case['expected_output_Euler'])
        return source, rows, points, source[2], ids, expected

    def audit(self, name, data=None):
        source, rows, points, faces, ids, expected = data or self.data(name)
        return M.audit_geometry(name, *source, rows, points, faces, ids, expected)

    def test_exact_half_cube_and_annulus(self):
        # Synthetic valid alternate triangulations, never predicted native output.
        for name, volume, cap, euler in [('cube-cut', 1755904, 23104, 2), ('through-hole', 12, 12, 0)]:
            with self.subTest(name=name):
                result = self.audit(name)
                self.assertEqual(F(result['exact_signed_volume_mm3']), volume)
                self.assertEqual(F(result['exact_cap_area_mm2']), cap)
                self.assertEqual(result['Euler'], euler)

    def test_noop_reindex_faceorder_and_cyclic_start(self):
        source, rows, points, faces, ids, expected = self.data('above-noop')
        order = list(reversed(range(len(rows))))
        inverse = {v: i for i, v in enumerate(order)}
        moved = [tuple(inverse[v] for v in t[1:]+t[:1]) for t in reversed(faces)]
        result = self.audit('above-noop', (source, [rows[i] for i in order], [points[i] for i in order], moved, [ids[i] for i in order], expected))
        self.assertEqual(result['constructed'], 0)

    def test_exact_intersection_detects_hole_crossing_without_inner_vertices(self):
        triangle = [(-2, 0), (2, 0), (0, 2)]
        self.assertTrue(all(not (-1 < x < 1 and -1 < y < 1) for x, y in triangle))
        self.assertEqual(M.area(M.intersection(triangle, M.rectangle((-1, -1), (1, 1)))), F(2))
        with self.assertRaisesRegex(ValueError, 'hole'):
            M.cover([triangle], (-2, -2), (2, 2), 4, ((-1, -1), (1, 1)))

    def test_boundary_hole_contact_has_zero_area(self):
        triangle = [(1, -1), (2, -1), (1, 1)]
        self.assertEqual(M.area(M.intersection(triangle, M.rectangle((-1, -1), (1, 1)))), 0)

    def test_sum_area_does_not_hide_overlap_or_gap(self):
        t = [(0, 0), (1, 0), (0, 1)]
        self.assertEqual(sum(M.area(x) for x in [t, t]), 1)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            M.cover([t, t], (0, 0), (1, 1), 1)

    def test_incorrect_origin_marker_rejected(self):
        data = list(self.data('cube-cut'))
        data[4] = list(data[4]); data[4][0] = 0
        with self.assertRaisesRegex(ValueError, 'coordinate-match IDs'):
            self.audit('cube-cut', data)

    def test_reversed_cap_and_changed_above_point_rejected(self):
        data = list(self.data('cube-cut'))
        data[3] = list(data[3]); data[3][0] = tuple(reversed(data[3][0]))
        with self.assertRaises(ValueError):
            self.audit('cube-cut', data)
        data = list(self.data('cube-cut'))
        data[1] = list(data[1]); data[2] = list(data[2])
        data[2][8] = (F(1, 2), F(0), F(76))
        data[1][8] = struct.pack('<ddd', *data[2][8])
        data[4] = list(data[4]); data[4][8] = M.MAX_ID
        with self.assertRaisesRegex(ValueError, 'off-plane'):
            self.audit('cube-cut', data)

    def test_noncyclic_vertex_link_rejected(self):
        # Two closed tetrahedra touching only at one vertex: edges alone pass.
        points = [(F(x), F(y), F(z)) for x, y, z in [(0,0,0),(1,0,0),(0,1,0),(0,0,1),(-1,0,0),(0,-1,0),(0,0,-1)]]
        faces = [(0,2,1),(0,1,3),(1,2,3),(2,0,3),(0,4,5),(0,6,4),(4,6,5),(5,6,0)]
        with self.assertRaisesRegex(ValueError, 'vertex link'):
            M.topology(points, faces, 3)

    def test_empty_refusal_and_unexpected_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            report = dict(status='rejected_empty_result', plane=[0,0,-1,0], clip_volume=True,
                          candidate_file_present=False, point_id_file_present=False,
                          head_surface_admitted=False, physics_validated=False, manufacturing_authorized=False)
            (d/'report.json').write_text(json.dumps(report))
            self.assertTrue(M.assess_case('empty-refusal', d)['report_only_empty_refusal'])
            (d/'candidate.bin').write_bytes(b'not a mesh')
            with self.assertRaisesRegex(ValueError, 'closure'):
                M.assess_case('empty-refusal', d)


if __name__ == '__main__':
    unittest.main()
