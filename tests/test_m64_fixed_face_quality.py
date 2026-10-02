import importlib.util
import math
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/audit_fixed_face_quality.py'
spec=importlib.util.spec_from_file_location('fixed_face_quality',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FixedFaceQualityTest(unittest.TestCase):
    def test_straight_corner_bound_agrees_with_triangle_area_formula(self):
        for angle in (1., 2., 10., 30., 60.):
            theta = math.radians(angle); ceiling = module.triangle_corner_ceiling(angle)
            for ratio in (.01, .1, .5, 1., 2., 10., 100.):
                q = math.sqrt(3)*ratio*math.sin(theta)/(1+ratio**2-ratio*math.cos(theta))
                self.assertLessEqual(q, ceiling+1e-14)
                if ratio == 1.: self.assertAlmostEqual(q, ceiling, places=14)
        self.assertAlmostEqual(module.triangle_corner_ceiling(60.), 1.)
        self.assertLess(module.tetra_ceiling(module.triangle_corner_ceiling(1.006)), .1)
        for angle in (0., -1., 61., float('nan'), float('inf')):
            with self.assertRaises(ValueError): module.triangle_corner_ceiling(angle)

    def test_bound_values_and_invalid_input(self):
        self.assertEqual(module.tetra_ceiling(1.),1.)
        self.assertEqual(module.tetra_ceiling(0.),0.)
        self.assertAlmostEqual(module.tetra_ceiling(2*.1/(3-.1)),.1)
        for q in (-1.,1.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): module.tetra_ceiling(q)

    @unittest.skipUnless(importlib.util.find_spec('gmsh'),'optional native Gmsh witness')
    def test_optimal_and_displaced_apices_against_native_metric(self):
        import gmsh
        import numpy as np
        W=np.array([[1.,.5],[0.,math.sqrt(3)/2]])
        gmsh.initialize(['ceiling-witness','-nopopup'],readConfigFiles=False,run=False)
        gmsh.option.setNumber('General.Terminal',0)
        try:
            for height in (.01,.05,.2,math.sqrt(3)/2):
                a=np.array([0.,0.,0.]); b=np.array([1.,0.,0.]); c=np.array([.5,height,0.])
                sa,sb=np.linalg.svd(np.column_stack((b-a,c-a))@np.linalg.inv(W),compute_uv=False)
                q2=2*sa*sb/(sa*sa+sb*sb)
                for scale,shift in ((1.,0.),(.5,0.),(2.,0.),(1.,.1),(1.,-.1)):
                    apex=(a+b+c)/3+np.array([shift,0.,scale*math.sqrt(2/3)*math.sqrt(sa*sb)])
                    gmsh.clear();gmsh.model.add('witness')
                    gmsh.model.addDiscreteEntity(2,1);gmsh.model.addDiscreteEntity(3,1)
                    gmsh.model.mesh.addNodes(3,1,[1,2,3,4],np.concatenate([a,b,c,apex]))
                    gmsh.model.mesh.addElementsByType(1,2,[1],[1,2,3])
                    gmsh.model.mesh.addElementsByType(1,4,[2],[1,2,3,4])
                    triangle,tetra=gmsh.model.mesh.getElementQualities([1,2],'minSICN')
                    self.assertAlmostEqual(triangle,q2,places=12)
                    self.assertLessEqual(tetra,module.tetra_ceiling(q2)+1e-12)
                    if scale==1. and shift==0.: self.assertAlmostEqual(tetra,module.tetra_ceiling(q2),places=12)
        finally:
            gmsh.finalize()
