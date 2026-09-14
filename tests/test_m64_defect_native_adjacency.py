import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('defect_adj',ROOT/'analyze_defect_native_adjacency.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


class DefectNativeAdjacencyTests(unittest.TestCase):
    def test_profiles_keep_distinct_meshes_receipts_and_native_ids(self):
        old=mod.selected_profile();new=mod.selected_profile(True)
        for key in ('domain','msh','mesh_report','manifest','localization'):
            self.assertNotEqual(old[key],new[key])
        self.assertIsNone(new['thin_face']);self.assertEqual(new['merged_port_face'],37)
        self.assertEqual(new['annular'],{53,54,55,56,59,60,61,62})
        self.assertNotIn('concaveCells',new['families'])
        self.assertIn('concaveCells',old['families'])
        for value in (1,0,None,'true'):
            with self.assertRaises(ValueError):mod.selected_profile(value)

    def test_unified_category_does_not_reuse_old_thin_face_or_annular_ids(self):
        native={i:{'role':role,'source_match':[]} for i,role in
                ((37,'walls_port'),(38,'walls_port'),(53,'walls_guide'),(64,'walls_valve'))}
        result=mod.family_summary([0],'cellSet',[0,0,0,0],[],
            {0:[(0,37),(1,38),(2,53),(3,64)]},native,unified=True)
        self.assertEqual(result['disjoint_boundary_category_combinations'],
            {'annular_guide_or_stem+merged_port_face_37+other_boundary':1})
        self.assertNotIn('thin_face_38',str(result['disjoint_boundary_category_combinations']))

    def test_unique_mapping_independent_of_point_order(self):
        msh={2:(1.123456789012345,0,0),9:(2.23456789012345,1,0)}
        foam=[tuple(float(format(x*.001,'.12g')) for x in msh[9]),tuple(float(format(x*.001,'.12g')) for x in msh[2])]
        mapping,proof=mod.point_bijection(msh,foam)
        self.assertTrue(proof['passes']);self.assertEqual(mapping,{0:9,1:2})

    def test_coordinate_outside_print_budget_rejected(self):
        _,proof=mod.point_bijection({2:(1,0,0)},[(.00100001,0,0)])
        self.assertFalse(proof['passes'])

    def test_ambiguous_serialized_points_rejected(self):
        _,proof=mod.point_bijection({2:(1,0,0),3:(1+1e-14,0,0)},[(.001,0,0),(.001,0,0)])
        self.assertFalse(proof['passes']);self.assertEqual(proof['ambiguous'],2)

    def test_faceSet_counts_both_cells_and_overlapping_roles(self):
        native={38:{'role':'walls_port','source_match':[]},55:{'role':'walls_guide','source_match':[]}}
        result=mod.family_summary([0],'faceSet',[0,0,1],[1],{0:[(1,38),(2,55)]},native)
        self.assertEqual(result['distinct_affected_cells'],2)
        self.assertEqual(result['cells_with_no_boundary_face'],1)
        self.assertEqual(result['directly_selected_internal_faces'],1)
        self.assertEqual(result['disjoint_boundary_category_combinations'],{'annular_guide_or_stem+thin_face_38':1})

    def test_cell_count_per_face_is_unique_but_triangles_counted(self):
        native={38:{'role':'walls_port','source_match':[]}}
        result=mod.family_summary([0],'cellSet',[0,0],[],{0:[(0,38),(1,38)]},native)
        row=result['native_face_histogram'][0]
        self.assertEqual(row['adjacent_affected_cells'],1);self.assertEqual(row['adjacent_boundary_triangles'],2)

    def test_internal_degree_uses_internal_owner_neighbour_not_wall_faces(self):
        # Three internal faces connect 0-1, 0-2 and 1-2; six following faces are walls.
        owner=[0,0,1,0,0,1,1,2,2];neighbour=[1,2,2]
        result=mod.family_summary([0,1,2],'cellSet',owner,neighbour,{}, {},unified=True)
        self.assertEqual(result['uncoupled_mesh_internal_face_degree_histogram'],{2:3})
        self.assertEqual(result['affected_cells_with_at_most_two_internal_faces'],3)


if __name__=='__main__':unittest.main()
