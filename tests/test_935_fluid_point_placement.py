from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0,str(SOURCE))
try:
    import numpy as np
    import optimize_fluid_edge_stars as placement
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Requires NumPy and SciPy')
class FluidPointPlacementTests(unittest.TestCase):
    def fixture(self):
        vertices=np.array([[0.,0,-1],[0,0,1],[1,0,0],[-.5,np.sqrt(3)/2,0],[-.5,-np.sqrt(3)/2,0]])
        return vertices,np.array([[0,1,2,3],[0,1,3,4],[0,1,4,2]])

    def evaluate(self,vertices,cells,before=None):
        initial=vertices[cells[0,:2]].mean(axis=0)
        proposal=placement.kernel_proposal(vertices,cells,initial)
        outside={tuple(face):-1 for face in placement.base.outer_faces(cells)}
        if before is None:before=placement.base.patch_quality(vertices,cells,outside,np.empty((0,3)),np.empty(0))
        return placement.search_placement(vertices,cells,initial,proposal,outside,np.empty((0,3)),np.empty(0),before),proposal,outside

    def test_analytic_unit_and_translated_scale_controls(self):
        placement.self_test()

    def test_local_index_remapping_matches_full_array_quality_without_moving_originals(self):
        vertices,cells=self.fixture();ids=np.array([1,3,5,7,9])
        extended=np.full((12,3),10.);extended[ids]=vertices;before=extended.copy()
        (best,_,stats),proposal,outside=self.evaluate(extended,ids[cells])
        self.assertIsNotNone(best)
        global_after=placement.base.patch_quality(np.vstack([extended,best[1]]),proposal[1],outside,np.empty((0,3)),np.empty(0))
        np.testing.assert_array_equal(global_after[0],best[-1][0])
        np.testing.assert_allclose(global_after[1],best[-1][1],rtol=1e-12,atol=1e-12)
        np.testing.assert_array_equal(extended,before)
        self.assertLessEqual(stats['DE_objective_evaluations'],256)
        self.assertLessEqual(stats['total_quality_evaluations'],261)
        self.assertTrue(placement.positive_partition(extended,ids[cells],best[1],proposal[1],proposal[2],proposal[3]))

    def test_positive_partition_alone_does_not_admit_a_non_improving_result(self):
        vertices,cells=self.fixture()
        (best,_,_),_,_=self.evaluate(vertices,cells,(np.zeros(5,dtype=int),np.zeros(5)))
        self.assertIsNone(best)

    def test_invalid_sample_bounds_fail_before_input_read_or_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for limit in [0,513]:
                output=root/f'output-{limit}'
                with self.assertRaises(ValueError):placement.run(root/'absent',limit,output)
                self.assertFalse(output.exists())

    def test_missing_complete_boundary_audit_is_refused_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);parent=root/'parent';parent.mkdir();output=root/'output'
            vertices,cells=self.fixture();np.savez(parent/'volume.npz',vertices=vertices,tetrahedra=cells)
            digest=hashlib.sha256((parent/'volume.npz').read_bytes()).hexdigest()
            (parent/'assessment.json').write_text(json.dumps({'volume_npz_sha256':digest,'exact_PLC_volume_equal':True,'complete_boundary_coordinate_triangle_marker_bijection':False,'exact_cell_orientation':{'negative':0,'zero':0}}))
            with self.assertRaises(AssertionError):placement.run(parent,1,output)
            self.assertFalse(output.exists())


class FluidPointPlacementCheckpointTests(unittest.TestCase):
    def test_checkpoint_keeps_full_quality_and_physical_scope_unqualified(self):
        r=json.loads((ROOT/'docs/research/935-horizontal-cooling/fluid-point-placement-20261022.json').read_text())
        for path,digest in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        self.assertTrue(all(value is False for value in r['scope'].values()))
        self.assertFalse(r['PicoGK_design_master_changed'])
        self.assertEqual(r['new_rotor_PDE_runs'],0)
        self.assertEqual(r['accepted_interior_stars'],67)
        self.assertEqual([c['small_determinant_cells'] for c in r['native_cases'].values()],[519,515,450,448])
        for c in r['native_cases'].values():
            for flag in ['all_cell_orientations_positive','exact_volume_equal_to_PLC','complete_boundary_coordinate_triangle_marker_bijection','original_quality_dictionary_unchanged']:
                self.assertTrue(c[flag])
            self.assertFalse(c['extended_mesh_quality_passed'])
            self.assertEqual(c['failed_native_checks'],4)
        self.assertTrue(r['prefix_and_boundary_verification']['all_original_vertices_retained_as_exact_prefix'])
        self.assertTrue(r['prefix_and_boundary_verification']['boundary_triangles_and_markers_exactly_equal'])
        self.assertEqual(r['prefix_and_boundary_verification']['added_interior_air_mesh_points'],67)
        self.assertEqual(sum(x['off_old_interpolation_line'] for x in r['point_selection_attribution'].values()),63)
        self.assertEqual(sum(x['matches_five_controls'] for x in r['point_selection_attribution'].values()),4)
        self.assertEqual(r['sweeps']['3']['eligible_internal_edges'],327)
        self.assertEqual(r['sweeps']['3']['sampled_edges'],327)
        self.assertEqual(r['sweeps']['3']['decisions'].get('accepted_disjoint_star',0),0)
        self.assertFalse(r['global_mesh_optimization_converged'])
        self.assertFalse(r['runtime']['new_paid_instance_created'])
        self.assertTrue(r['private_archive']['all_members_verified'])
        self.assertTrue(r['private_archive']['Mac_all_members_verified'])
        self.assertEqual(r['private_archive']['entries'],145)


if __name__=='__main__':unittest.main()
