import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

try:import numpy as np
except ImportError:np=None
SOURCE=Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source';sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('conforming_results',SOURCE/'assess_conforming_fea.py')
module=importlib.util.module_from_spec(spec)
if np is not None:spec.loader.exec_module(module)


@unittest.skipIf(np is None,'NumPy unavailable')
class ConformingResultTests(unittest.TestCase):
    def test_translated_unit_tetrahedron_load_and_moment(self):
        vertices=np.array([[0.,0,2],[1,0,2],[0,1,2],[0,0,3]])
        force,moment,_,_,volume=module.centrifugal(vertices,np.array([[0,1,2,3]]),1.,1.)
        self.assertAlmostEqual(volume,1/6)
        np.testing.assert_allclose(force,[1/24,1/24,0],rtol=1e-14)
        np.testing.assert_allclose(moment,[-11/120,11/120,0],rtol=1e-14)
        # Centroid-only quadrature gives 3/32; it must not replace the exact moment.
        self.assertGreater(abs(moment[1]-3/32),.002)
        with self.assertRaises(ValueError):module.centrifugal(vertices,np.array([[0,2,1,3]]),1.,1.)

    def test_consistent_body_loads_distinguish_linear_and_quadratic_quadrature(self):
        vertices=np.array([[0.,0,2],[1,0,2],[0,1,2],[0,0,3]])
        linear=module.nodal_centrifugal(vertices,np.array([[0,1,2,3]]),1.,1.)
        np.testing.assert_allclose(linear,np.tile([1/96,1/96,0],(4,1)))
        higher=np.vstack((vertices,[(vertices[i]+vertices[j])/2 for i,j in ((0,1),(1,2),(0,2),(0,3),(1,3),(2,3))]))
        quadratic=module.nodal_centrifugal(higher,np.arange(10)[None],1.,1.)
        np.testing.assert_allclose(quadratic.sum(axis=0),[1/24,1/24,0],rtol=1e-13)
        np.testing.assert_allclose(np.cross(higher,quadratic).sum(axis=0),[-11/120,11/120,0],rtol=1e-13,atol=1e-16)
        self.assertTrue(np.any(quadratic[:4,:2]<0))

    def test_result_coverage_rejects_missing_duplicate_foreign_and_nonfinite(self):
        head='forces (fx,fy,fz) for set BORE and time 1\n'
        middle='displacements (vx,vy,vz) for set NALL and time 1\n1 0 0 0\n2 1 2 3\n'
        stress='stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set ROTOR and time 1\n'
        for gauss in (1,4):
            text=head+'1 2 3 4\n'+middle+stress+''.join(f'1 {k} 1 0 0 0 0 0\n' for k in range(1,gauss+1))
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'rotor.dat';path.write_text(text)
                u,rf,vm=module.fields(path,2,1,np.array([True,False]),gauss)
                np.testing.assert_array_equal(u[1],[1,2,3]);np.testing.assert_array_equal(rf[0],[2,3,4]);self.assertEqual(vm[0],1.)
                for invalid in (text.replace('2 1 2 3\n',''),text+'1 1 1 0 0 0 0 0\n',
                                text.replace('1 2 3 4\n','2 2 3 4\n'),text.replace('2 1 2 3\n','2 nan 2 3\n'),
                                text+stress,text.replace('1 1 1 0 0 0 0 0\n','')):
                    path.write_text(invalid)
                    with self.assertRaises(ValueError):module.fields(path,2,1,np.array([True,False]),gauss)
