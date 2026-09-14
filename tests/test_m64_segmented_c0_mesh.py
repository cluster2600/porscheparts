import importlib.util
import copy
import math
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

    def test_fab_binding_has_86_faces_without_reusing_historical_88(self):
        binding={'descriptor_bijection_verified':True,'matches_private':[
            {'source_face_index':i,'gmsh_face_tag':i+100} for i in range(1,87)]}
        self.assertEqual(len(audit.verified_face_lookup(binding,audit.UNIFIED_DOMAIN)),86)
        with self.assertRaises(ValueError):audit.verified_face_lookup(binding)
        with self.assertRaises(ValueError):audit.verified_face_lookup(binding,'unregistered')
        binding['matches_private'].append({'source_face_index':87,'gmsh_face_tag':187})
        with self.assertRaises(ValueError):audit.verified_face_lookup(binding,audit.UNIFIED_DOMAIN)


def merge_fixture():
    """Témoin abstrait : les nouveaux IDs ne suivent aucun décalage constant."""
    pairs=((1,19),(2,8),(3,51),(4,12))
    before={str(i):{'curve_global_sha256':str(i),'range':[i,i+1],'tolerance':1e-7} for i,_ in pairs}
    after={str(j):copy.deepcopy(before[str(i)]) for i,j in pairs}
    before_faces={}; after_faces={}
    for a,b in ((10,30),(20,40)):
        descriptor={'support_sha256':str(a),'orientation':'forward','tolerance':1e-7,
            'occurrences':[{'edge_id':i,'edge_key':str(i),'pcurve_sha256':str((a,i)),
                'range_on_surface':[i,i+1]} for i,j in pairs]}
        before_faces[str(a)]=descriptor
        after_faces[str(b)]=copy.deepcopy(descriptor)
        for row,(_,j) in zip(after_faces[str(b)]['occurrences'],pairs):row['edge_id']=j
    review={'split_curve_reference_comparisons_private':[{'edge_id_private':i} for i,j in pairs]}
    merge={'original_sha256':audit.DOMAIN,'candidate_sha256':audit.UNIFIED_DOMAIN,
        'inputs_unchanged':True,'gates':{'native_valid':True},
        'descriptors_private':{'before_edges':before,'after_edges':after,
            'before_faces':before_faces,'after_faces':after_faces}}
    manifest={'boundary_role_transfer':{'original_domain_sha256':audit.DOMAIN,
        'independent_geometry_review_sha256':audit.UNIFIED_REVIEW,
        'face_index_relation':[[10,30],[20,40]]}}
    return review,merge,manifest


class UnifiedC0CorrespondenceTests(unittest.TestCase):
    def test_ids_are_found_by_exact_geometry_not_offset(self):
        result=audit.unified_correspondence(*merge_fixture())
        self.assertEqual(result['edge_pairs_private'],[(1,19),(2,8),(3,51),(4,12)])
        self.assertEqual(result['face_pairs_private'],[(10,30),(20,40)])

    def test_missing_or_ambiguous_edge_is_not_a_match(self):
        for ambiguous in (False,True):
            review,merge,manifest=merge_fixture(); edges=merge['descriptors_private']['after_edges']
            if ambiguous:edges['99']=copy.deepcopy(edges['19'])
            else:del edges['19']
            with self.assertRaises(ValueError):audit.unified_correspondence(review,merge,manifest)

    def test_changed_curve_range_or_tolerance_is_rejected(self):
        for field,value in (('curve_global_sha256','changed'),('range',[0,99]),('tolerance',2e-7)):
            review,merge,manifest=merge_fixture()
            merge['descriptors_private']['after_edges']['19'][field]=value
            with self.assertRaises(ValueError):audit.unified_correspondence(review,merge,manifest)

    def test_support_and_pcurve_proofs_are_required(self):
        for kind in ('support','pcurve'):
            review,merge,manifest=merge_fixture();face=merge['descriptors_private']['after_faces']['30']
            if kind=='support':face['support_sha256']='different'
            else:face['occurrences'][0]['pcurve_sha256']='different'
            with self.assertRaises(ValueError):audit.unified_correspondence(review,merge,manifest)

    def test_wrong_domain_review_and_failed_gate_are_rejected(self):
        for mutation in ('domain','review','gate','unchanged'):
            review,merge,manifest=merge_fixture()
            if mutation=='domain':merge['candidate_sha256']=audit.DOMAIN
            elif mutation=='review':manifest['boundary_role_transfer']['independent_geometry_review_sha256']=audit.REVIEW
            elif mutation=='gate':merge['gates']['native_valid']=False
            else:merge['inputs_unchanged']=False
            with self.assertRaises(ValueError):audit.unified_correspondence(review,merge,manifest)

    def test_duplicate_face_relation_is_rejected(self):
        review,merge,manifest=merge_fixture()
        manifest['boundary_role_transfer']['face_index_relation'].append([10,30])
        with self.assertRaises(ValueError):audit.unified_correspondence(review,merge,manifest)


class CompleteNativeInterfaceTests(unittest.TestCase):
    def test_eight_native_curves_partition_all_edges_not_only_four_C0(self):
        shared={(i,i+1) for i in range(1,9)}
        chains=[{'passes':True,'nodes_private':[i,i+1],'native_edge_id':100+i} for i in range(1,9)]
        self.assertTrue(audit.exact_native_chain_partition(shared,chains,list(range(101,109)))['passes'])
        self.assertFalse(audit.exact_chain_partition(shared,chains[:4])['passes'])
        self.assertFalse(audit.exact_native_chain_partition(shared,chains[:7],list(range(101,109)))['passes'])
        self.assertFalse(audit.exact_native_chain_partition(shared|{(9,10)},chains,list(range(101,109)))['passes'])

    def test_curve_id_bijection_and_no_double_mesh_coverage_are_required(self):
        shared={(i,i+1) for i in range(1,9)}
        chains=[{'passes':True,'nodes_private':[i,i+1],'native_edge_id':i} for i in range(1,9)]
        chains[7]['native_edge_id']=7
        self.assertFalse(audit.exact_native_chain_partition(shared,chains,list(range(1,9)))['passes'])
        chains[7]['native_edge_id']=8;chains[7]['nodes_private']=[1,2]
        result=audit.exact_native_chain_partition(shared,chains,list(range(1,9)))
        self.assertFalse(result['passes']);self.assertEqual(result['multiply_counted_edges'],1)

    def test_open_chain_is_not_promoted_to_closed_loop(self):
        edges=[{'id':i,'vertex_ids_private':[i,i+1]} for i in range(1,9)]
        graph=audit.native_interface_graph(edges)
        self.assertTrue(graph['unbranched']);self.assertEqual(graph['vertices'],9)
        self.assertEqual(graph['open_chains'],1);self.assertEqual(graph['closed_cycles'],0)
        self.assertEqual(graph['components_private'][0]['endpoint_vertex_ids_private'],[1,9])
        edges[-1]['vertex_ids_private']=[8,1]
        self.assertEqual(audit.native_interface_graph(edges)['closed_cycles'],1)

    def test_branch_and_duplicate_native_edge_rejected(self):
        edges=[{'id':i,'vertex_ids_private':[0,i]} for i in range(1,4)]
        self.assertFalse(audit.native_interface_graph(edges)['unbranched'])
        with self.assertRaises(ValueError):audit.native_interface_graph(edges+[edges[0]])

    def test_native_vertex_ball_does_not_inflate_edge_or_vertex_tolerance(self):
        vertex={'point_private':[0.,0.,0.],'tolerance':.25}
        self.assertTrue(audit.native_endpoint_ball((0.,0.,0.),vertex,(.25,0.,0.))['passes'])
        outside=math.nextafter(.25,math.inf)
        self.assertFalse(audit.native_endpoint_ball((0.,0.,0.),vertex,(outside,0.,0.))['passes'])
        self.assertFalse(audit.native_endpoint_ball((outside,0.,0.),vertex,(0.,0.,0.))['passes'])

    def test_complete_correspondence_inventories_extra_curves_and_opposite_occurrences(self):
        review,merge,manifest=merge_fixture();data=merge['descriptors_private']
        for phase in ('before','after'):
            for f,face in data[phase+'_faces'].items():
                for row in face['occurrences']:row['orientation']=1 if f in ('10','30') else -1
        for i in range(4):
            old=100+i;new=200+i;descriptor={'curve_global_sha256':f'other-{i}','range':[0.,1.]}
            data['before_edges'][str(old)]=descriptor;data['after_edges'][str(new)]=copy.deepcopy(descriptor)
            for phase,eid in (('before',old),('after',new)):
                for f,face in data[phase+'_faces'].items():
                    face['occurrences'].append({'edge_id':eid,'orientation':1 if f in ('10','30') else -1,
                        'edge_key':f'other-{i}','pcurve_sha256':str(i),'range_on_surface':[0.,1.]})
        original=audit.unified_correspondence(review,merge,manifest)
        complete=audit.complete_unified_correspondence(original,merge)
        self.assertEqual(len(complete['edge_pairs_private']),8)
        self.assertEqual(complete['other_edge_ids_private'],list(range(200,204)))
        changed=copy.deepcopy(merge);changed['descriptors_private']['after_faces']['30']['occurrences'][-1]['orientation']=-1
        altered={**original,'after_faces':changed['descriptors_private']['after_faces']}
        with self.assertRaises(ValueError):audit.complete_unified_correspondence(altered,changed)


def tetra_fixture(volume=False, reverse=False, group=7, moved=False, omit=False):
    nodes=['1 0 0 0','2 1 0 0','3 0 1 0','4 0 0 1']
    if moved:nodes[-1]='4 0 0 1.000000000000001'
    triangles=[(1,3,2),(1,2,4),(1,4,3),(2,3,4)]
    if reverse:triangles[0]=triangles[0][::-1]
    if omit:triangles.pop()
    start=100 if volume else 10
    elements=[f'{start+i} 2 2 {group} 38 '+ ' '.join(map(str,tri)) for i,tri in enumerate(triangles)]
    if volume:elements.append('999 4 2 8 1 1 2 3 4')
    return ('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n4\n'+'\n'.join(nodes)+
        '\n$EndNodes\n$Elements\n'+str(len(elements))+'\n'+'\n'.join(elements)+'\n$EndElements\n')


class VolumeBoundaryConservationTests(unittest.TestCase):
    def test_element_id_permutation_does_not_change_boundary(self):
        result=audit.compare_volume_boundary(tetra_fixture(),tetra_fixture(volume=True))
        self.assertTrue(result['passes']);self.assertEqual(result['surface_element_ids_reassigned'],4)
        self.assertTrue(result['surface_records_equal_actual_tetrahedral_boundary'])

    def test_changed_coordinate_or_physical_label_rejected(self):
        for kwargs in ({'moved':True},{'group':8}):
            result=audit.compare_volume_boundary(tetra_fixture(),tetra_fixture(volume=True,**kwargs))
            self.assertFalse(result['passes'])

    def test_same_bad_surface_records_do_not_replace_real_tetra_boundary(self):
        for kwargs in ({'reverse':True},{'omit':True}):
            result=audit.compare_volume_boundary(tetra_fixture(**kwargs),tetra_fixture(volume=True,**kwargs))
            self.assertTrue(result['oriented_triangles_and_physical_elementary_groups_exact'])
            self.assertFalse(result['passes'])


if __name__=='__main__':unittest.main()
