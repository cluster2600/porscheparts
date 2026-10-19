import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    import shapely
    from shapely.geometry import Polygon, box
except ImportError:
    shapely = None

if shapely is not None:
    path = (Path(__file__).resolve().parents[1]/
            'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_band_union.py')
    spec = importlib.util.spec_from_file_location('carrier_exact_band_union', path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


@unittest.skipUnless(shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles'),
                     'Optional Shapely constrained-triangulation runtime required')
class ExactBandUnion(unittest.TestCase):
    def test_collective_sweep_coverage_preserves_holes_and_refuses_outside_material(self):
        free = Polygon(box(0, 1, 4, 5).exterior.coords, [box(1, 2, 3, 4).exterior.coords])
        self.assertTrue(audit.prove_band_covered(free, free, .2)['passed'])
        self.assertFalse(audit.prove_band_covered(box(0, 1, 4, 5), free, .2)['passed'])
        self.assertFalse(audit.prove_band_covered(box(-.01, 1, 4, 5), free, .2)['passed'])

    def test_plate_clip_is_exact_and_does_not_allow_below_zero(self):
        free = box(0, 0, 2, 1)
        self.assertTrue(audit.prove_band_covered(box(0, 0, 2, 1.1), free, .2)['passed'])
        self.assertFalse(audit.prove_band_covered(box(0, -.01, 2, 1), free, .2)['passed'])

    def test_positive_triangle_chain_must_equal_the_original_boundary(self):
        free = box(0, 1, 2, 3)
        incomplete = shapely.GeometryCollection([Polygon([(0, 1), (2, 1), (2, 3)])])
        with patch.object(shapely, 'constrained_delaunay_triangles', return_value=incomplete):
            with self.assertRaisesRegex(ValueError, 'chain differs'):
                audit.prove_band_covered(free, free, .2)
        triangles = list(shapely.get_parts(shapely.constrained_delaunay_triangles(free)))
        with patch.object(shapely, 'constrained_delaunay_triangles',
                          return_value=shapely.GeometryCollection(triangles+triangles)):
            with self.assertRaisesRegex(ValueError, 'chain differs'):
                audit.prove_band_covered(free, free, .2)
        duplicate = shapely.GeometryCollection([free, free])
        with patch.object(shapely, 'constrained_delaunay_triangles', return_value=duplicate):
            with self.assertRaisesRegex(ValueError, 'non-triangle'):
                audit.prove_band_covered(free, free, .2)

    def test_invalid_geometry_and_penetration_are_refused(self):
        for amount in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                audit.prove_band_covered(box(0, 1, 2, 3), box(0, 1, 2, 3), amount)
        with self.assertRaises(ValueError):
            audit.prove_band_covered(Polygon(), box(0, 1, 2, 3), .2)

    def test_actual_unchanged_left_sheet_is_covered_by_sweeps_despite_rounded_overlay(self):
        fixture = path.parent/'band-union-evidence/left-grid.json'
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),
                         'fed9e3d93fbc588124995fc0c930a811ff38fd6ffd44068a42a7e19f24ec9c12')
        data = json.loads(fixture.read_text())
        geometries = {k: shapely.from_wkb(bytes.fromhex(v)) for k, v in data['geometry_wkb_hex'].items()}
        self.assertFalse(audit._COVERAGE.prove_polygon_covered(geometries['free'], geometries['allowed'])['passed'])
        self.assertFalse(audit._COVERAGE.prove_polygon_covered(geometries['result'], geometries['allowed'])['passed'])
        self.assertTrue(audit._COVERAGE.prove_polygon_covered(geometries['free'], geometries['result'])['passed'])
        before = geometries['result'].wkb
        receipt = audit.prove_band_covered(geometries['result'], geometries['free'], data['penetration_mm'])
        saved = json.loads(fixture.with_name('left-grid-assessment.json').read_text())
        self.assertEqual(receipt, saved['receipt'])
        self.assertTrue(receipt['passed'])
        self.assertEqual(receipt['source_geometry_sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(geometries['result'].wkb, before)
        self.assertEqual(receipt['material_triangulation']['triangles'], 102)
        self.assertEqual(receipt['intended_convex_primitives'], 95)
        self.assertEqual(receipt['polygon_overlay_operations'], 0)
