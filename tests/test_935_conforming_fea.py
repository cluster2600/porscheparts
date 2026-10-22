import importlib.util
from pathlib import Path
import sys
import unittest

try:import numpy as np
except ImportError:np=None
SOURCE=Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source';sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('conforming_fea',SOURCE/'prepare_conforming_fea.py')
module=importlib.util.module_from_spec(spec)
if np is not None:spec.loader.exec_module(module)


@unittest.skipIf(np is None,'NumPy unavailable')
class ConformingFEATests(unittest.TestCase):
    def test_quadratic_edges_are_shared_and_match_the_calculix_order(self):
        v=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1],[0,0,-1]])
        cells=np.array([[0,1,2,3],[0,2,1,4]])
        mapping=module.helper(module.SHARED/'audit_quadratic_mapping.py','_935_test_mapping')
        points,higher=module.quadratic_nodes(v,cells,mapping.EDGES)
        self.assertEqual(len(points),14)
        self.assertEqual(set(higher[0,4:7]),set(higher[1,4:7]))
        for original,quad in zip(cells,higher):
            for k,(a,b) in enumerate(mapping.EDGES):np.testing.assert_array_equal(points[quad[4+k]],(v[original[a]]+v[original[b]])/2)
        integers,_=module.integer_points(points)
        for quad in higher:
            numerator,denominator,delta=mapping.integer_cell_bound([integers[int(i)] for i in quad])
            self.assertEqual(numerator,0);self.assertGreater(denominator,0);self.assertEqual(delta,0)
