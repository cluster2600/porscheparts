"""Pilot mesh integrity witnesses; never a CFD or manufacturing qualification."""
import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/mesh_gas_domain.py'
SPEC=importlib.util.spec_from_file_location('gas_mesh',SOURCE)
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)


class GasMeshTests(unittest.TestCase):
    def setUp(self):
        self.msh='''$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
4
2 1 "inlet"
2 2 "receiver_outlet"
2 3 "walls"
3 100 "air"
$EndPhysicalNames
$Nodes
4
11 0 0 0
23 1 0 0
47 0 1 0
89 0 0 1
$EndNodes
$Elements
5
1 2 2 1 1 11 47 23
2 2 2 2 2 11 23 89
3 2 2 3 3 11 89 47
4 2 2 3 4 23 47 89
5 4 2 100 1 11 23 47 89
$EndElements
'''

    def test_boundary_partition_requires_exact_nonoverlapping_coverage(self):
        groups={'inlet':[4],'receiver_outlet':[10],'walls':[20,30]}
        self.assertTrue(MODULE.boundary_partition([4,10,20,30],groups)['complete'])
        for invalid in ({**groups,'walls':[20]}, {**groups,'walls':[20,30,4]},
                        {**groups,'walls':[20,30,90]}, {**groups,'inlet':[]},
                        {**groups,'extra':[50]}):
            with self.subTest(groups=invalid),self.assertRaises(ValueError):
                MODULE.boundary_partition([4,10,20,30],invalid)

    def test_native_contract_preserves_subroles_and_rejects_any_failed_gate(self):
        contract={'schema':'m64-intake-gas-domain/v1',
                  'gates':dict.fromkeys(MODULE.REQUIRED_DOMAIN_GATES,True),
                  'boundary_faces':[{'id':i,'role':role,'area':1.,'center':[0.,0.,float(i)]}
                                    for i,role in enumerate(('inlet','receiver_outlet','walls_port','fixture_stem_seals'),1)]}
        result=MODULE.validated_boundary_contract(contract)
        self.assertEqual(result['groups']['walls'],[3,4])
        self.assertEqual(result['original_roles'][4],'fixture_stem_seals')
        for gate in MODULE.REQUIRED_DOMAIN_GATES:
            invalid={**contract,'gates':{**contract['gates'],gate:False}}
            with self.subTest(gate=gate),self.assertRaises(ValueError):
                MODULE.validated_boundary_contract(invalid)
        invalid={**contract,'boundary_faces':contract['boundary_faces']+[{'id':5,'role':'unknown','area':1.,'center':[0.,0.,0.]}]}
        with self.assertRaises(ValueError):MODULE.validated_boundary_contract(invalid)

    def test_msh22_physical_names_and_boundary_orientation(self):
        r=MODULE.parse_msh22(self.msh)
        self.assertEqual(len(r['tetrahedra']),1)
        orientation=MODULE.boundary_orientation(r['points'],r['tetrahedra'],r['grouped_triangles'])
        self.assertTrue(orientation['all_outward'])
        triangles=sum(r['grouped_triangles'].values(),[])
        topology=MODULE.checks.connectivity_metrics(r['points'],r['tetrahedra'],triangles)
        self.assertTrue(topology['boundary_matches'])
        self.assertAlmostEqual(topology['signed_volume_sum'],1/6)
        self.assertEqual(MODULE.mesh_bounds(r['points']),[0.,0.,0.,1.,1.,1.])

    def test_reversed_boundary_triangle_is_reported(self):
        r=MODULE.parse_msh22(self.msh.replace('11 47 23','11 23 47'))
        result=MODULE.boundary_orientation(r['points'],r['tetrahedra'],r['grouped_triangles'])
        self.assertFalse(result['all_outward'])
        self.assertEqual(result['patches']['inlet']['inward'],1)

    def test_msh_parser_rejects_lost_groups_unknown_nodes_and_wrong_format(self):
        mutations=(self.msh.replace('2.2 0 8','4.1 0 8'),
                   self.msh.replace('2.2 0 8','2.2 1 8'),
                   self.msh.replace('"walls"','"defaultFaces"'),
                   self.msh.replace('5 4 2 100 1','5 4 2 0 1'),
                   self.msh.replace('11 23 47 89','11 23 47 999'),
                   self.msh.replace('$Nodes\n4','$Nodes\n5'))
        for value in mutations:
            with self.subTest(value=value),self.assertRaises(ValueError):MODULE.parse_msh22(value)

    def test_missing_boundary_is_not_hidden_by_present_physical_names(self):
        text=self.msh.replace('$Elements\n5','$Elements\n4').replace('4 2 2 3 4 23 47 89\n','')
        r=MODULE.parse_msh22(text)
        topology=MODULE.checks.connectivity_metrics(r['points'],r['tetrahedra'],sum(r['grouped_triangles'].values(),[]))
        self.assertFalse(topology['boundary_matches'])
        self.assertEqual(topology['boundary_missing_triangles'],1)

    def test_C0_advisory_is_hash_bound_and_does_not_promote_failed_gates(self):
        manifest={'schema':'m64-intake-gas-domain/v1',
                  'gates':dict.fromkeys(MODULE.REQUIRED_DOMAIN_GATES,True),
                  'exports':{'domain_brep':{'sha256':'a'*64}},
                  'boundary_faces':[{'id':i,'sha256':str(i)*64,'role':'walls_seat'} for i in range(1,5)],
                  'native_BOP':{'has_faulty':True,'has_errors':False,'has_warnings':False,'faults':['BOPAlgo_GeomAbs_C0']},
                  'native_roundtrip_BOP':{'has_faulty':True,'has_errors':False,'has_warnings':False,'faults':['BOPAlgo_GeomAbs_C0']},
                  'local_intake_necks':[{'name':name,'BRep_valid':True,'solid_count':1,'trunk_excluded_by_axial_bound':True,
                    'other_seat_overlap_volume':0.,'throat_side_area':2.,'chamber_side_area':3.,
                    'BOP':{'has_errors':False,'has_warnings':False,'faults':[]}} for name in ('intake_1','intake_2')]}
        manifest['gates'].update(bop_no_faults=False,positive_intake_curtain=False)
        receipt={'schema':'m64-native-gas-domain-advisories/v1','allow_diagnostic_meshing':True,
                 'inputs_sha256':{'domain':'a'*64,'classified_report':'b'*64},
                 'geometry_modified':False,'tolerance_modified':False,'all_inputs_unchanged':True,
                 'classified_boundary_assignment_complete':True,'native_check':{'BRep_valid_exact_method':True},
                 'ambiguous_face_ownership':[{'face_id':i,'source_face_sha256':str(i)*64,'recommended_physical_role':'walls_seat',
                    'ownership_evidence_pass':True} for i in range(1,5)],
                 'C0_entities':[{'edge_id':97,'curve':{'C0_internal_knots':[
                    {'parameter':float(i),'position_private':[0.,0.,float(i)],'position_jump_native_numeric':0.,
                     'tangent_angle_degrees':float(i+1)} for i in range(3)]}}]}
        original=deepcopy(manifest)
        result=MODULE.validated_c0_advisory(manifest,'b'*64,receipt)
        self.assertEqual(result['failed_source_gates_not_promoted'],['bop_no_faults','positive_intake_curtain'])
        self.assertEqual(manifest,original)
        self.assertFalse(result['source_gates_preserved']['bop_no_faults'])
        for target,path,value in (
                ('receipt',('inputs_sha256','domain'),'c'*64),
                ('receipt',('inputs_sha256','classified_report'),'c'*64),
                ('receipt',('allow_diagnostic_meshing',),False),
                ('receipt',('tolerance_modified',),True),
                ('receipt',('all_inputs_unchanged',),False),
                ('receipt',('ambiguous_face_ownership',1,'source_face_sha256'),'c'*64),
                ('manifest',('gates','brep_valid'),False),
                ('manifest',('native_BOP','faults'),['BOPAlgo_InvalidCurveOnSurface']),
                ('manifest',('local_intake_necks',1,'chamber_side_area'),0.),
                ('receipt',('C0_entities',0,'curve','C0_internal_knots',1),deepcopy(receipt['C0_entities'][0]['curve']['C0_internal_knots'][0])),
                ('receipt',('C0_entities',0,'curve','C0_internal_knots',1,'position_jump_native_numeric'),1e-12)):
            modified={'receipt':deepcopy(receipt),'manifest':deepcopy(manifest)}
            obj=modified[target]
            for key in path[:-1]:obj=obj[key]
            obj[path[-1]]=value
            with self.subTest(target=target,path=path),self.assertRaises(ValueError):
                MODULE.validated_c0_advisory(modified['manifest'],'b'*64,modified['receipt'])

    def test_nearest_boundary_checkpoint_is_diagnostic_at_submesh_spacing(self):
        r=MODULE.parse_msh22(self.msh)
        # Both subresolution checkpoints legitimately choose the same node.
        checkpoints=[{'edge_id':97,'parameter':i,'position_private':[float(i)*1e-5,0.,0.]} for i in (1,2)]
        r['points'][999]=(1e-5,0.,0.) # Interior/unreferenced node must not be selected.
        result=MODULE.nearest_boundary_nodes(checkpoints,r['points'],r['grouped_triangles'])
        self.assertEqual([row['nearest_boundary_node'] for row in result['checkpoints_private']],[11,11])
        self.assertAlmostEqual(result['maximum_distance_scan_units'],2e-5)
        self.assertTrue(result['distance_is_diagnostic_not_C0_conformity_or_CFD_acceptance'])
        self.assertNotIn('passed',result)

    def test_like_integrator_volume_reference_retains_adaptive_difference_and_tolerance(self):
        imported=995961.8505977859;fixed=995961.8505977857;adaptive=995964.5870880088
        previous=MODULE.import_volume_comparison(imported,adaptive)
        self.assertFalse(previous['within_unchanged_tolerance'])
        result=MODULE.import_volume_comparison(imported,adaptive,fixed)
        self.assertTrue(result['within_unchanged_tolerance'])
        self.assertEqual(result['relative_tolerance_unchanged'],1e-6)
        self.assertGreater(result['relative_difference_from_adaptive_volume'],1e-6)
        self.assertFalse(MODULE.import_volume_comparison(imported+5,adaptive,fixed)['within_unchanged_tolerance'])
        for value in (0.,-1.,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):
                MODULE.import_volume_comparison(imported,adaptive,value)

    def test_volume_quadrature_receipt_requires_exact_native_source_and_adaptive_estimate(self):
        manifest={'exports':{'domain_brep':{'sha256':'a'*64}},'properties':{'volume':995964.587088009}}
        receipt={'schema':'m64-native-volume-quadrature-reference/v1','status':'matched_nonadaptive_reference',
                 'domain_sha256':'a'*64,'input_unchanged':True,'geometry_modified':False,'tolerance_modified':False,
                 'nonadaptive_volume':995961.8505977857,'adaptive_volume':995964.5870880088}
        self.assertEqual(MODULE.validated_volume_reference(manifest,receipt),receipt)
        for key,value in (('domain_sha256','b'*64),('input_unchanged',False),('geometry_modified',True),
                          ('adaptive_volume',995961.8505977857),('nonadaptive_volume',float('nan'))):
            with self.subTest(key=key),self.assertRaises(ValueError):
                MODULE.validated_volume_reference(manifest,{**receipt,key:value})

    def test_surface_only_parser_preserves_patches_and_rejects_volume_elements(self):
        surface=self.msh.replace('$Elements\n5','$Elements\n4').replace('5 4 2 100 1 11 23 47 89\n','')
        r=MODULE.parse_msh22(surface,surface_only=True)
        self.assertEqual(r['tetrahedra'],[])
        topology=MODULE.surface_topology(sum(r['grouped_triangles'].values(),[]))
        self.assertTrue(topology['closed_two_manifold_edge_incidence'])
        self.assertEqual(topology['incoherent_two_triangle_edge_orientations'],0)
        with self.assertRaises(ValueError):MODULE.parse_msh22(surface)
        with self.assertRaises(ValueError):MODULE.parse_msh22(self.msh,surface_only=True)
        no_volume_name=surface.replace('$PhysicalNames\n4','$PhysicalNames\n3').replace('3 100 "air"\n','')
        self.assertEqual(MODULE.parse_msh22(no_volume_name,surface_only=True)['tetrahedra'],[])

    def test_surface_topology_detects_missing_duplicate_and_reversed_facets(self):
        r=MODULE.parse_msh22(self.msh);triangles=sum(r['grouped_triangles'].values(),[])
        self.assertFalse(MODULE.surface_topology(triangles[:-1])['closed_two_manifold_edge_incidence'])
        self.assertEqual(MODULE.surface_topology(triangles+[triangles[0]])['duplicate_triangles'],1)
        changed=[tuple(reversed(triangles[0])),*triangles[1:]]
        self.assertEqual(MODULE.surface_topology(changed)['incoherent_two_triangle_edge_orientations'],3)

    def test_local_surface_algorithm_is_bound_to_exact_native_face_not_raw_Gmsh_tag(self):
        manifest={'exports':{'domain_brep':{'sha256':MODULE.GAS05_NATIVE_SHA}},
                  'boundary_faces':[{'id':38,'sha256':MODULE.GAS05_FACE38_SHA,'role':'walls_port'}]}
        binding={'descriptor_bijection_verified':True,'matches_private':[{'source_face_index':38,'gmsh_face_tag':104}]}
        self.assertIsNone(MODULE.face38_algorithm_assignment(manifest,binding,None))
        for algorithm in (1,5):
            assigned=MODULE.face38_algorithm_assignment(manifest,binding,algorithm)
            self.assertEqual(assigned['gmsh_face_tag'],104)
            self.assertEqual(assigned['surface_algorithm'],algorithm)
        with self.assertRaises(ValueError):MODULE.face38_algorithm_assignment(manifest,binding,6)
        for target,path,value in (('manifest',('exports','domain_brep','sha256'),'0'*64),
                                 ('manifest',('boundary_faces',0,'sha256'),'0'*64),
                                 ('manifest',('boundary_faces',0,'role'),'walls_valve'),
                                 ('binding',('descriptor_bijection_verified',),False),
                                 ('binding',('matches_private',0,'source_face_index'),39)):
            state={'manifest':deepcopy(manifest),'binding':deepcopy(binding)};obj=state[target]
            for key in path[:-1]:obj=obj[key]
            obj[path[-1]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):
                MODULE.face38_algorithm_assignment(state['manifest'],state['binding'],1)

    def test_local_size_field_preserves_CAD_and_global_minimum(self):
        manifest={'exports':{'domain_brep':{'sha256':MODULE.GAS05_NATIVE_SHA}},
                  'boundary_faces':[{'id':38,'sha256':MODULE.GAS05_FACE38_SHA,'role':'walls_port'}]}
        binding={'descriptor_bijection_verified':True,'matches_private':[{'source_face_index':38,'gmsh_face_tag':104}]}
        result=MODULE.face38_size_assignment(manifest,binding,.15)
        self.assertEqual(result['gmsh_face_tag'],104)
        self.assertEqual(result['global_minimum_size_unchanged'],.005)
        self.assertTrue(result['include_boundary'])
        self.assertFalse(result['CAD_geometry_modified'])
        self.assertNotIn('surface_algorithm',result)
        for value in (0.,.004,.21,float('inf'),float('nan'),True):
            with self.assertRaises(ValueError):MODULE.face38_size_assignment(manifest,binding,value)
        manifest['exports']['domain_brep']['sha256']='0'*64
        with self.assertRaises(ValueError):MODULE.face38_size_assignment(manifest,binding,.15)

    def test_guide_refinement_binds_all_four_exact_cylinders_without_claiming_a_bound(self):
        manifest={'exports':{'domain_brep':{'sha256':MODULE.GAS05_NATIVE_SHA}},'boundary_faces':[
            {'id':i,'role':r,'sha256':h,'surface_type':'GeomAbs_Cylinder'}
            for i,(r,h) in MODULE.GAS05_GUIDE_STEM_FACES.items()]}
        binding={'descriptor_bijection_verified':True,'matches_private':[
            {'source_face_index':i,'gmsh_face_tag':100+i} for i in MODULE.GAS05_GUIDE_STEM_FACES]}
        self.assertIsNone(MODULE.guide_size_assignment(manifest,binding,None))
        result=MODULE.guide_size_assignment(manifest,binding,.2)
        self.assertEqual([r['gmsh_face_tag'] for r in result['faces']],[155,158,162,163])
        self.assertTrue(result['target_size_is_not_a_guaranteed_actual_chord_bound'])
        self.assertFalse(result['CAD_geometry_modified'])
        for value in (0.,.004,.21,float('inf'),float('nan'),True):
            with self.assertRaises(ValueError):MODULE.guide_size_assignment(manifest,binding,value)
        for field,value in (('sha256','0'*64),('role','walls_port'),('surface_type','GeomAbs_Plane')):
            changed=deepcopy(manifest);changed['boundary_faces'][0][field]=value
            with self.assertRaises(ValueError):MODULE.guide_size_assignment(changed,binding,.2)
        changed=deepcopy(binding);changed['matches_private'].pop()
        with self.assertRaises(ValueError):MODULE.guide_size_assignment(manifest,changed,.2)

    def test_guide_frame_reference_does_not_reuse_an_earlier_mesh_acceptance(self):
        frames={'domain_sha256':MODULE.GAS05_NATIVE_SHA,'faces_private':[]}
        receipt={'schema':'m64-persisted-guide-chord-diagnostic/v1','mode':'native_cylinder_diagnostics',
                 'all_inputs_unchanged':True,'inputs_sha256':{'domain':MODULE.GAS05_NATIVE_SHA,
                 'source':MODULE.GUIDE_CHORD_SOURCE_SHA},'result':{'frames_private':frames,
                 'whole_facet_chord_gate':{'local_radial_envelopes_accepted':False}}}
        self.assertIs(MODULE.validated_guide_frames(receipt,MODULE.GUIDE_FRAME_RECEIPT_SHA),frames)
        with self.assertRaises(ValueError):MODULE.validated_guide_frames(receipt,'0'*64)
        for key,value in (('mode','crossings'),('all_inputs_unchanged',False),('schema','unknown')):
            changed=deepcopy(receipt);changed[key]=value
            with self.assertRaises(ValueError):MODULE.validated_guide_frames(changed,MODULE.GUIDE_FRAME_RECEIPT_SHA)


if __name__=='__main__':unittest.main()
