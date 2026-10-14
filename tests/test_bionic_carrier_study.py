"""Numerical bookkeeping must not fabricate loads or retain an old increment."""
import importlib.util
from pathlib import Path
import copy
import sys
import tempfile
import unittest

from _deps import require_modules
require_modules('numpy')
import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py'
spec = importlib.util.spec_from_file_location('bionic_study', SOURCE)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)
sys.path.insert(0, str(SOURCE.parent))
try:
    import print_simulation as printing
    import flat_build
finally:
    sys.path.pop(0)


class BionicStudyTests(unittest.TestCase):
    def test_flat_build_rejects_tilt_and_an_undersized_bed(self):
        c = np.sqrt(.5)
        orientation = {
            'rotation_matrix': [[c, -c, 0], [c, c, 0], [0, 0, 1]],
            'placed_bounds_mm': [[74, 74, 30], [526, 526, 70]],
            'machine_volume_mm': [600, 600, 600],
            'assumed_XY_margin_mm': 10,
            'assumed_platform_thickness_mm': 20,
            'assumed_min_support_height_mm': 10,
        }
        flat_build.validate_orientation(orientation)
        tilted = copy.deepcopy(orientation)
        tilted['rotation_matrix'] = [[1, 0, 0], [0, c, -c], [0, c, c]]
        with self.assertRaisesRegex(AssertionError, 'remain flat'):
            flat_build.validate_orientation(tilted)
        small = copy.deepcopy(orientation)
        small['machine_volume_mm'] = [450, 450, 600]
        with self.assertRaises(AssertionError):
            flat_build.validate_orientation(small)

    def test_von_mises_invariants(self):
        tensors = np.array([[7., 7, 7, 0, 0, 0], [-3., 0, 0, 0, 0, 0], [0., 0, 0, 2, 0, 0]])
        np.testing.assert_allclose(study.von_mises(tensors), [0, 3, 2*np.sqrt(3)])

    def test_resultants_and_virtual_work(self):
        study.selfcheck()

    def test_deposition_clock_keeps_old_layers_shrunk_and_new_layers_unstrained(self):
        printing.selfcheck()

    def test_print_reader_separates_stages_and_ignores_plastic_scalar_rows(self):
        text = '''displacements (vx,vy,vz) for set ALLN
1 0 0 1D-3
stresses (sxx,syy,szz,sxy,sxz,syz) for set BODY
1 1 10 0 0 0 0 0
equivalent plastic strain (elem,integ.pnt.,peeq) for set BODY
1 1 0.001
displacements (vx,vy,vz) for set ALLN
1 0 0 2D-3
stresses (sxx,syy,szz,sxy,sxz,syz) for set BODY
1 1 20 0 0 0 0 0
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'print.dat'; path.write_text(text)
            steps = printing.frames(path)
        self.assertEqual(len(steps), 2)
        np.testing.assert_allclose(steps[0]['displacements'], [[1, 0, 0, .001]])
        np.testing.assert_allclose(steps[1]['stresses'], [[1, 1, 20, 0, 0, 0, 0, 0]])

    def test_eigenvalue_table_does_not_include_nodal_rows(self):
        text = 'B U C K L I N G   F A C T O R   O U T P U T\n MODE FACTOR\n 1 8.0D+1\n 2 9.0E+1\n\n E I G E N V A L U E\n 1 99\n'
        np.testing.assert_allclose(study.eigenvalues(text, 'buckling'), [[1, 80], [2, 90]])

    def test_degenerate_attachment_layout_is_rejected(self):
        xyz = np.array([[-3., 0, 0], [-1., 0, 0], [1., 0, 0], [3., 0, 0]])
        with self.assertRaises(AssertionError):
            study.distribute(xyz, [np.array([i]) for i in range(4)], [0, 0, 1], [1, 0, 0])

    def test_dat_reader_keeps_last_increment_and_fortran_exponents(self):
        text = '''displacements (vx,vy,vz) for set ALLN
1 0 0 10
forces (fx,fy,fz) for set FIXED
1 0 0 20
stresses (sxx,syy,szz,sxy,sxz,syz) for set BODY
1 1 10 0 0 0 0 0
displacements (vx,vy,vz) for set ALLN
1 0 0 -1D-3
forces (fx,fy,fz) for set FIXED
1 0 0 2
stresses (sxx,syy,szz,sxy,sxz,syz) for set BODY
1 1 3 0 0 0 0 0
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'result.dat'; path.write_text(text)
            result = study.parse_dat(path)
        np.testing.assert_allclose(result['displacements'], [[1, 0, 0, -.001]])
        np.testing.assert_allclose(result['forces'], [[1, 0, 0, 2]])
        np.testing.assert_allclose(result['stresses'], [[1, 1, 3, 0, 0, 0, 0, 0]])
