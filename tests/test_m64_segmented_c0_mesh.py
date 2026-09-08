import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/audit_segmented_c0_mesh.py'
spec=importlib.util.spec_from_file_location('segmented_c0_mesh',PATH)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class SegmentedC0SurfaceTests(unittest.TestCase):
    def test_common_faces_need_single_incidence(self):
        self.assertEqual(audit.common_face_edges([(1,2,3)],[(2,1,4)]),{(1,2)})
        with self.assertRaises(ValueError):
            audit.common_face_edges([(1,2,3),(2,1,5)],[(2,1,4)])
        with self.assertRaises(ValueError):audit.common_face_edges([(1,2,3)],[(1,2,4)])

    def test_nearby_nodes_are_not_topological_chain(self):
        result=audit.monotone_segment_chain({(1,2)}, {1:0.,2:.5,3:1.},1,3,set())
        self.assertFalse(result['passes'])

    def test_four_paths_can_preserve_small_segments(self):
        edges={(1,2),(2,3),(3,4),(4,5)}
        parameters={1:0.,2:.1,3:.1002,4:.10025,5:1.}
        for k in range(1,5):
            result=audit.monotone_segment_chain(edges,parameters,k,k+1,set(parameters)-{k,k+1})
            self.assertTrue(result['passes']);self.assertEqual(result['nodes_private'],[k,k+1])

    def test_skipping_corner_or_reversing_parameter_rejected(self):
        self.assertFalse(audit.monotone_segment_chain({(1,3)}, {1:0.,2:.5,3:1.},1,2,{3})['passes'])
        self.assertFalse(audit.monotone_segment_chain({(1,2)}, {1:1.,2:0.},1,2,set())['passes'])

    def test_two_paths_rejected(self):
        result=audit.monotone_segment_chain({(1,2),(2,4),(1,3),(3,4)},
            {1:0.,2:.2,3:.3,4:1.},1,4,set())
        self.assertFalse(result['passes']);self.assertEqual(result['path_count_capped_at_two'],2)

    def test_dangling_or_disconnected_admissible_edge_rejected(self):
        result=audit.monotone_segment_chain({(1,2),(2,4),(2,3)},
            {1:0.,2:.2,3:.3,4:1.},1,4,set())
        self.assertFalse(result['passes'])

    def test_complete_partition_rejects_omission_and_double_count(self):
        shared={(1,2),(2,3),(3,4),(4,5)}
        chains=[{'passes':True,'nodes_private':[i,i+1]} for i in range(1,5)]
        self.assertTrue(audit.exact_chain_partition(shared,chains)['passes'])
        self.assertFalse(audit.exact_chain_partition(shared|{(5,6)},chains)['passes'])
        self.assertFalse(audit.exact_chain_partition(shared,chains[:3]+[chains[0]])['passes'])

    def test_node_bijection_not_only_distance(self):
        vertices=[{'id':1,'point_private':[0,0,0],'tolerance':1e-5},
                  {'id':2,'point_private':[1e-6,0,0],'tolerance':1e-5}]
        self.assertFalse(audit.match_anchors({7:(0,0,0)},{7},vertices)[1])
        self.assertFalse(audit.match_anchors({7:(0,0,0),8:(1e-6,0,0)},{7,8},vertices)[1])

    def test_parser_preserves_elementary_face_tags(self):
        msh='$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n3\n1 0 0 0\n2 1 0 0\n3 0 1 0\n$EndNodes\n$Elements\n1\n7 2 2 3 38 1 2 3\n$EndElements\n'
        points,faces,counts=audit.parse_surface_msh22(msh)
        self.assertEqual(faces,{38:[(1,2,3)]});self.assertEqual(counts,{2:1})
        with self.assertRaises(ValueError):audit.parse_surface_msh22(msh.replace('1 2 3\n$EndElements','1 2 4\n$EndElements'))

    def test_face_binding_requires_descriptor_proof_and_exact_native_index_set(self):
        binding={'descriptor_bijection_verified':True,'unmatched_gmsh_faces':[],
            'ambiguous_gmsh_faces':[],'matches_private':[
                {'source_face_index':i,'gmsh_face_tag':i+100} for i in range(1,89)]}
        self.assertEqual(len(audit.verified_face_lookup(binding)),88)
        with self.assertRaises(ValueError):
            audit.verified_face_lookup({**binding,'descriptor_bijection_verified':False})
        binding['matches_private'][-1]['source_face_index']=89
        with self.assertRaises(ValueError):audit.verified_face_lookup(binding)


if __name__=='__main__':unittest.main()
