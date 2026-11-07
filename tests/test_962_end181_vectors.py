import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/physics_witness/inspect_end181_vectors.py'
spec = importlib.util.spec_from_file_location('end181_vectors', SOURCE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ForceProjectionTests(unittest.TestCase):
    def test_cross_product_and_support_partition(self):
        # The force at (2,3,4) gives r cross F = (-3,6,-3).
        rows = {1: dict(x=2, y=3, z=4, rx=5, ry=6, rz=7),
                0: dict(x=0, y=0, z=0, rx=-5, ry=-6, rz=-7)}
        result = audit.project_forces(rows)
        self.assertEqual(result['free'], [5,6,7,-3,6,-3])
        self.assertEqual(result['constrained'], [-5,-6,-7,0,0,0])

    def test_exact_sum_retains_small_component(self):
        rows = {n: dict(x=0,y=0,z=0,rx=f,ry=0,rz=0)
                for n,f in [(1,1e16),(2,1),(3,-1e16)]}
        self.assertEqual(audit.project_forces(rows)['free'], [1,0,0,0,0,0])


if __name__ == '__main__':
    unittest.main()
