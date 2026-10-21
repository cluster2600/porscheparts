"""Patch topology and exact boundary controls, without native head work."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
SPEC = importlib.util.spec_from_file_location("quality_feature_guard", SOURCE / "audit_quality_features.py")
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class PatchContinuity(unittest.TestCase):
    def test_disk_flip_preserves_exact_boundary_and_rejects_changed_boundary_or_fan(self):
        p = np.array([[0.,0,0],[1.,0,0],[1.,1,0],[0.,1,0]])
        f = np.array([[0,1,2],[0,2,3]], dtype=np.int64)
        g = np.array([[0,1,3],[1,2,3]], dtype=np.int64)
        result, boundary = MODULE.compare_patch(p,f,p,g)
        self.assertEqual((result["euler_characteristic"],result["boundary_loops"]),(1,1))
        self.assertEqual(len(boundary),4)
        moved=p.copy();moved[0,0]=np.nextafter(0.,1.)
        for q,h in [(moved,g),(p,g[:,::-1])]:
            with self.subTest(changed=h.tolist()), self.assertRaises(ValueError): MODULE.compare_patch(p,f,q,h)
        with self.assertRaises(ValueError): MODULE.patch_topology(np.array([[0,1,2],[0,3,4]]))


if __name__ == "__main__": unittest.main()
