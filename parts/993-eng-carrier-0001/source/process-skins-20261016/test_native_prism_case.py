import unittest
from pathlib import Path
from fractions import Fraction as Q
import numpy as np
from native_prism_case import PrismNativeCase,_csr,_radical_bound,_same_oriented_triangles,_evidence_path

class StrictCaseTests(unittest.TestCase):
    def test_unsigned_csr_underflow_is_rejected(self):
        d={'all_parent_offsets':np.array([0,5,1,6],dtype=np.uint64),'all_parent_faces':np.arange(6)}
        with self.assertRaises(ValueError):_csr(d,3)
    def test_empty_csr_is_explicit_unknown_only(self):
        d={'all_parent_offsets':np.array([0,0,1]),'all_parent_faces':np.array([7])}
        with self.assertRaises(ValueError):_csr(d,2)
        _csr(d,2,allow_empty=True)
    def test_cyclic_orientation_only(self):
        a=np.array([[[0,0,0],[1,0,0],[0,1,0]]],dtype=np.float64)
        self.assertTrue(_same_oriented_triangles(a,np.roll(a,1,axis=1))[0])
        self.assertFalse(_same_oriented_triangles(a,a[:,[0,2,1]])[0])
    def test_exact_composed_bound(self):
        self.assertTrue(_radical_bound(Q(4),Q(9),Q(5)))
        self.assertFalse(_radical_bound(Q(4),Q(9),Q(4999,1000)))
        self.assertFalse(_radical_bound(Q(9),Q(16),Q(1)))
    def test_relative_map_is_based_on_map_directory(self):
        self.assertEqual(_evidence_path('data/result.npz','/package/local-evidence-map.json'),Path('/package/data/result.npz'))
        self.assertEqual(_evidence_path('/old/result.npz','/package/local-evidence-map.json'),Path('/old/result.npz'))
        with self.assertRaises(ValueError):_evidence_path('../escape.npz','/package/local-evidence-map.json')
    def test_public_paths_and_source_index_are_bound(self):
        for field,value in [('final_npz',Path('/wrong')),('original_raw_npz',Path('/wrong')),('schema_path',Path('/wrong')),('source_index',99)]:
            c=PrismNativeCase();c.final_npz=Path('/final');c.original_raw_npz=Path('/raw');c.schema_path=Path('/schema');c.native_audit_path=Path('/audit');c.source_index=2
            c._public_identity=(c.final_npz,c.original_raw_npz,c.schema_path,c.native_audit_path,c.source_index)
            setattr(c,field,value)
            with self.assertRaisesRegex(ValueError,'Public case identity changed'):c.verify()

if __name__=='__main__':unittest.main()
