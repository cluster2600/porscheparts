import json
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'twins/935-horizontal-cooling-system-f0/source'))
try:
    import numpy as np
    from export_inspection_assembly import FLAGS, cylinder_candidates, export, placement_error, radial_minimum, triangles
except ImportError:
    np = None


class InspectionReceiptTests(unittest.TestCase):
    def test_public_execution_pins_sources_and_keeps_installation_unverified(self):
        path = ROOT/'docs/research/935-horizontal-cooling/inspection-assembly-20261012.json'
        record = json.loads(path.read_text())
        for source, expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(), expected, source)
        for flag in ('scale_verified','interfaces_verified','mechanism_dynamics_validated',
                     'historical_installation_verified','manufacturing_authorized','physical_validation','vast_rental_used'):
            self.assertIs(record[flag], False)
        self.assertEqual(record['engine_context_family'], '917_scan_comparative_only_not_935')
        self.assertEqual(len(record['components']), 4)
        self.assertTrue(record['export_triangles_preserved'])
        self.assertFalse(record['render']['display_decimation'])
        self.assertGreater(record['rotor_shroud_360_degree_radial_separation_mm_hypothesis'], 0)


@unittest.skipIf(np is None, 'Scientific mesh dependencies unavailable')
class InspectionAssemblyTests(unittest.TestCase):
    def test_column_matrix_rotation_scale_translation_and_order(self):
        source = np.array([[[1,2,3], [4,5,6], [7,8,9]]], dtype=np.float32)
        matrix = np.array([[0,-.5,0,10],[.5,0,0,20],[0,0,.5,30],[0,0,0,1]])
        placed = source @ matrix[:3,:3].T + matrix[:3,3]
        self.assertEqual(placement_error(source, placed, matrix), 0)
        with self.assertRaisesRegex(ValueError, 'column-vector'):
            placement_error(source, placed[:, ::-1], matrix)
        with self.assertRaisesRegex(ValueError, 'count'):
            placement_error(source, np.zeros((2,3,3)), matrix)

    def test_radial_clearance_checks_edge_interiors_and_triangle_interior(self):
        face = np.array([[[3,-4,0],[3,4,0],[5,0,1]]])
        self.assertEqual(radial_minimum(face), 3)
        self.assertEqual(radial_minimum(np.array([[[-1,-1,0],[1,-1,0],[0,1,0]]])), 0)
        self.assertEqual(radial_minimum(np.array([[[3,-1,0],[3,1,0],[3,1,0]]])), 3)
        with self.assertRaises(ValueError):
            radial_minimum(np.full((1,3,3), np.nan))

    def test_binary_stl_rejects_truncation_and_empty_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bad.stl'
            path.write_bytes(bytes(80)+struct.pack('<I', 1))
            with self.assertRaises(ValueError): triangles(path)
            path.write_bytes(bytes(84))
            with self.assertRaises(ValueError): triangles(path)

    def test_cylinder_screen_includes_spanning_triangles_and_rejects_separation(self):
        faces = np.array([[[-20,-20,0], [20,-20,0], [0,20,0]],
                          [[30,0,0], [31,1,0], [32,0,0]],
                          [[0,0,10], [1,0,10], [0,1,10]]], dtype=float)
        self.assertEqual(cylinder_candidates(faces, -1, 1, 0, 2), 1)
        self.assertEqual(cylinder_candidates(faces[1:], -1, 1, 0, 2), 0)

    def test_inspection_export_cannot_promote_physical_claims(self):
        try:
            from pxr import Usd
        except ImportError:
            self.skipTest('USD unavailable')
        from run_reconstruction import sha
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory)/'native'; native.mkdir()
            case_path = native/'case.json'; case_path.write_text(json.dumps({'scale_verified':False}))
            record = {'status':'PicoGK_inspection_assembly_not_verified_installation',
                      'case_sha256':sha(case_path), **{key:False for key in FLAGS}}
            for flag in FLAGS:
                wrong = dict(record); wrong[flag] = True
                (native/'receipt.json').write_text(json.dumps(wrong))
                output = Path(directory)/flag
                with self.assertRaisesRegex(ValueError, 'inspection receipt'):
                    export(native, output)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
