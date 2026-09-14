import unittest
import numpy as np
import importlib.util
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/physicsnemo-mesh'

def load(name):
    spec = importlib.util.spec_from_file_location('m64_pm_' + name, SOURCE_DIR / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

reference = load('cpu_reference').reference
exact_index = load('prepare_surface').exact_index


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.p = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        self.t = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]], dtype=np.int64)

    def test_oriented_tetra(self):
        r = reference(self.p, self.t)
        self.assertAlmostEqual(r['signed_volume_contributions'].sum(), 1/6)
        self.assertAlmostEqual(r['areas'].sum(), 1.5 + np.sqrt(3)/2)
        np.testing.assert_allclose(np.linalg.norm(r['unit_normals'],axis=1), 1)

    def test_reverse(self):
        a = reference(self.p,self.t)
        b = reference(self.p,self.t[:,::-1])
        np.testing.assert_array_equal(a['areas'],b['areas'])
        np.testing.assert_array_equal(a['unit_normals'],-b['unit_normals'])
        self.assertAlmostEqual(b['signed_volume_contributions'].sum(),-1/6)

    def test_degenerate_not_masked(self):
        r=reference(self.p,np.array([[0,0,1]],dtype=np.int64))
        self.assertEqual(r['areas'][0],0)
        self.assertTrue(np.isnan(r['unit_normals']).all())

    def test_exact_index_signed_zero(self):
        xyz=self.p[self.t].copy()
        xyz[0,0,0]=-0.0
        p,t=exact_index(xyz)
        self.assertEqual(p[t].tobytes(),xyz.tobytes())

    def test_bad_index(self):
        with self.assertRaisesRegex(ValueError,'index_out_of_range'):
            reference(self.p,np.array([[0,1,4]],dtype=np.int64))

    def test_nonfinite(self):
        self.p[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'finite_geometry'):
            reference(self.p,self.t)


if __name__=='__main__':
    unittest.main()
