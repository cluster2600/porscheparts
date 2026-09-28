import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))
from run_junction_mesh_trial import local_size


class JunctionTests(unittest.TestCase):
    @unittest.skipUnless(all(importlib.util.find_spec(p) for p in ('trimesh','rtree','scipy')), 'optional voxel/ray runtime')
    def test_closed_cavity_is_not_mistaken_for_filled_material(self):
        try:
            import scipy.sparse
        except ImportError:
            self.skipTest('compiled sparse module unavailable; run in Linux')
        import trimesh
        from screen_powder_connectivity import classify_voids
        outer=trimesh.creation.box(extents=[10.,10.,10.])
        inner=trimesh.creation.box(extents=[4.,4.,4.]);inner.invert()
        hollow=trimesh.util.concatenate([outer,inner])
        result=classify_voids(hollow,1.)
        self.assertEqual(result['candidate_void_regions'],1)
        self.assertGreater(result['candidate_void_volume_scan_units3'],0)
        self.assertEqual(result['ambiguous_regions'],0)
        self.assertEqual(classify_voids(outer,1.)['candidate_void_regions'],0)
        self.assertFalse(result['physical_powder_removal_validated'])

    def test_partial_final_layer_and_missing_layer_refusal(self):
        from screen_junction_am import integrate_layers
        rows=[dict(part_area_mm2=6.,support_area_mm2=3.)]*3
        part,support=integrate_layers(rows,.25,.1)
        self.assertAlmostEqual(part,1.5)
        self.assertAlmostEqual(support,.75)
        with self.assertRaises(ValueError):integrate_layers(rows[:-1],.25,.1)
        with self.assertRaises(ValueError):integrate_layers(rows,float('nan'),.1)

    def test_size_is_local_bounded_and_rejects_nonfinite_inputs(self):
        self.assertEqual(local_size(0, 6, .005), .005)
        self.assertEqual(local_size(.1, 6, .02), .02)
        self.assertEqual(local_size(100, .5, .02), 1.)
        self.assertEqual(local_size(100, 6, .02), 6.)
        for values in ((float('nan'), 6, .02), (0, -1, .02), (0, 6, .001)):
            with self.assertRaises(ValueError):
                local_size(*values)

    @unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'), 'optional native CAD runtime')
    def test_native_box_section_and_material_chord(self):
        import numpy as np
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from audit_pinched_junction import locate, section_edges, line_chords
        shape = BRepPrimAPI_MakeBox(2., 3., 4.).Shape()
        centre = np.array([1., 1.5, 2.])
        near = locate(shape, centre, 1.1)
        self.assertEqual(len(near), 2)
        self.assertTrue(all(abs(row['distance']-1.) < 1e-10 for row in near))
        curves = section_edges(shape, centre)
        self.assertEqual(len(curves), 4)
        self.assertTrue(all(np.allclose(curve[:,1], 1.5) for curve in curves))
        chord = line_chords(shape, centre, [1,0,0], span=3.)['material_chords']
        self.assertEqual(len(chord), 1)
        self.assertAlmostEqual(chord[0]['length'], 2.)
        self.assertTrue(chord[0]['contains_centre'])
        with self.assertRaises(ValueError):
            line_chords(shape, centre, [0,0,0])


if __name__ == '__main__':
    unittest.main()
