import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

try:import numpy as np
except ImportError:np=None
spec=importlib.util.spec_from_file_location('surface_contacts',Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source/review_surface_contacts.py')
module=importlib.util.module_from_spec(spec)
if np is not None:spec.loader.exec_module(module)
FCL=importlib.util.find_spec('fcl') is not None


@unittest.skipIf(np is None,'NumPy unavailable')
class SurfaceContactTests(unittest.TestCase):
    def test_truncated_or_wrong_size_stl_rejected_before_bvh(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'mesh.stl'
            for data,count in ((b'',1),(b' '*80+struct.pack('<I',2),1),
                               (b' '*80+struct.pack('<I',1)+b' '*49,1),(b' '*84,True)):
                p.write_bytes(data)
                with self.assertRaises(ValueError):module.load(p,count)

    @unittest.skipUnless(FCL,'Optional native FCL unavailable')
    def test_actual_engine_matches_independent_analytic_fixtures(self):
        rows=module.fixtures();self.assertEqual(len(rows),3);self.assertTrue(all(r['passed'] for r in rows))

    @unittest.skipUnless(FCL,'Optional native FCL unavailable')
    def test_surface_distance_does_not_assert_solid_containment(self):
        # Two concentric tetrahedral surfaces: the small surface is contained
        # without crossing. This is why the system report keeps containment open.
        v=np.array([[1.,1,1],[-1,-1,1],[-1,1,-1],[1,-1,-1]])
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=np.int32)
        r=module.query(module.model(v,f),module.model(v*.1,f))
        self.assertFalse(r['surface_crossing']);self.assertGreater(r['minimum_surface_distance_native_units'],0)
