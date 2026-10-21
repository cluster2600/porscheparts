import tempfile,unittest
from pathlib import Path
import numpy as np
from consolidate_exact_vertices_v3 import consolidate

class ExactConsolidationV3Tests(unittest.TestCase):
    def test_closed_tetra_edge_collapse_preserves_csr(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[0,0,0]],dtype=np.float64)
            f=np.array([[0,2,4],[4,2,1],[0,4,3],[4,1,3],[1,2,3],[2,0,3]],dtype=np.int32)
            np.savez(p/'in.npz',vertices=v,faces=f,all_parent_offsets=np.arange(0,13,2),all_parent_faces=np.arange(12),source_face=np.arange(6))
            r=consolidate(p/'in.npz',p/'out');d=np.load(p/'out/result.npz')
            self.assertEqual((r['vertices'],r['faces'],r['discarded_repeated_position_faces']),(4,4,2))
            np.testing.assert_array_equal(d['canonical_input_face'],[1,3,4,5])
            np.testing.assert_array_equal(d['all_parent_faces'],[2,3,6,7,8,9,10,11])
            self.assertTrue(r['discarded_support_covered_by_retained_faces'])

    def test_uncovered_degenerate_segment_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);v=np.array([[0,0,0],[1,0,0],[0,1,0],[9,9,9],[10,9,9]],dtype=np.float64)
            np.savez(p/'in.npz',vertices=v,faces=np.array([[0,1,2],[3,4,4]]))
            with self.assertRaisesRegex(ValueError,'not proved covered'):consolidate(p/'in.npz',p/'out')

    def test_tiny_positive_triangle_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);v=np.array([[0,0,0],[1,0,0],[0,1e-100,0]],dtype=np.float64)
            np.savez(p/'in.npz',vertices=v,faces=np.array([[0,1,2]]))
            r=consolidate(p/'in.npz',p/'out');self.assertEqual(r['faces'],1);self.assertEqual(r['discarded_repeated_position_faces'],0)

    def test_unsigned_nonmonotone_csr_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);v=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype=np.float64)
            np.savez(p/'in.npz',vertices=v,faces=np.array([[0,1,2]]*3),all_parent_offsets=np.array([0,5,1,6],dtype=np.uint64),all_parent_faces=np.arange(6))
            with self.assertRaisesRegex(ValueError,'Invalid parent CSR'):consolidate(p/'in.npz',p/'out')

if __name__=='__main__':unittest.main()
