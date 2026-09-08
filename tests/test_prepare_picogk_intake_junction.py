import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import prepare_picogk_intake_junction as prep


class InputPackageContracts(unittest.TestCase):
    def test_proposal_inflates_radius_plus_three_voxels_and_contracts_only_inner_box(self):
        result = prep.proposal_boxes([0., 1., 2., 3., 4., 2.])
        self.assertAlmostEqual(result['inflation_scan_units'], 1.6)
        for got, wanted in zip(result['authorized_box_PROPOSED_private'], [-1.6, -.6, .4, 4.6, 5.6, 3.6]):
            self.assertAlmostEqual(got, wanted)
        for got, wanted in zip(result['calculation_box_PROPOSED_private'], [-1., 0., 1., 4., 5., 3.]):
            self.assertAlmostEqual(got, wanted)
        self.assertIsNone(result['keepout_subtracted_domain_nonempty'])
        self.assertFalse(result['private_processing_authorized'])
        self.assertFalse(result['authorized_box_frozen_by_this_preparation'])

    def test_bad_bounds_and_nonpositive_masks_refuse_preparation(self):
        for bounds, radius, voxel in (
                ([0, 0, 0, -1, 1, 1], 1, .2), ([0, 0, 0, 1, 1, 1], 0, .2),
                ([0, 0, 0, 1, 1, 1], 1, 0), ([0, 0, 0, float('nan'), 1, 1], 1, .2)):
            with self.assertRaises(ValueError):
                prep.proposal_boxes(bounds, radius, voxel)

    def fixture(self):
        checkpoint = {'kind': 'intake', 'exports': {'native_BRep_sha256': prep.EXPECTED_INTAKE,
                       'native_BOP': {'has_faulty': False}}, 'seed_sections_private': [None]*7,
                       'trunk_quality': {'method': 'bounded-c1'},
                       'branches': [{'name': 'intake_1'}, {'name': 'intake_2'}]}
        context = {'inputs_sha256': {'body_build': 'build', 'module_STEP': 'module'}}
        body = {'module_sha256': 'module', 'registration': dict(prep.EXPECTED_REGISTRATION)}
        routing = {'inputs_sha256': dict(context['inputs_sha256']),
                   'bank_records': [copy.deepcopy(checkpoint)]}
        return ({'intake': prep.EXPECTED_INTAKE, 'body_build': 'build'}, checkpoint, context, body, routing)

    def test_exact_source_checkpoint_module_and_frame_are_bound(self):
        prep.verify_provenance(*self.fixture())
        for target, key, value in ((0, 'intake', 'wrong'), (0, 'body_build', 'wrong'),
                                   (1, 'kind', 'exhaust'), (1, 'seed_sections_private', [None]*6),
                                   (3, 'module_sha256', 'wrong'), (3, 'registration', {})):
            arguments = list(self.fixture())
            arguments[target][key] = value
            with self.assertRaises(ValueError):
                prep.verify_provenance(*arguments)

    def test_bad_recorded_native_quality_or_replaced_branch_is_rejected(self):
        arguments = list(self.fixture())
        arguments[1]['exports']['native_BOP']['has_faulty'] = True
        arguments[4]['bank_records'] = [copy.deepcopy(arguments[1])]
        with self.assertRaises(ValueError):
            prep.verify_provenance(*arguments)
        arguments = list(self.fixture())
        arguments[1]['branches'][0]['name'] = 'exhaust_1'
        arguments[4]['bank_records'] = [copy.deepcopy(arguments[1])]
        with self.assertRaises(ValueError):
            prep.verify_provenance(*arguments)


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'native OCP runtime required')
class NativeInputWitnesses(unittest.TestCase):
    def test_native_inner_branch_edge_selected_without_outer_ring(self):
        cad = prep.local.ports.design.CAD()
        branch = cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,-10,0), cad.gp_Dir(0,1,0)),5,12).Shape()
        trunk = cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,0), cad.gp_Dir(0,1,0)),10,10).Shape()
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
        source = BRepAlgoAPI_Fuse(branch, trunk).Shape()
        section = {'center': [0,0,0], 'normal': [0,1,0], 'radius': 10}
        edges = prep.local.branch_cap_edges(cad, source, section)
        self.assertEqual(len(edges), 1)
        record = prep.edge_description(cad, edges[0][1], edges[0][0])
        self.assertEqual(len(record['uniform_parameter_samples_private']), 65)
        self.assertLess(edges[0][2], section['radius'])
        bounds = record['native_precision_bounds_private']
        for point in record['uniform_parameter_samples_private']:
            for index in range(3):
                self.assertLessEqual(bounds[index], point[index])
                self.assertGreaterEqual(bounds[index+3], point[index])

    def test_full_plane_section_keeps_second_loop_outside_the_seed_circle(self):
        cad = prep.local.ports.design.CAD()
        cylinders = [cad.BRepPrimAPI_MakeCylinder(
            cad.gp_Ax2(cad.gp_Pnt(x,-1,0),cad.gp_Dir(0,1,0)),1,2).Shape() for x in (0,4)]
        source = cad.compound(cylinders)
        section = prep.full_plane_section(cad, source, {'center': [0,0,0], 'normal': [0,1,0], 'radius': 1})
        self.assertEqual(cad.indexed(section, cad.TopAbs_EDGE).Extent(), 2)
        self.assertGreater(prep.native_bounds(section)[3], 4.)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'section.brep'
            receipt = prep.write_shape(path, section)
            self.assertEqual(receipt['sha256'], prep.local.ports.sha(path))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                prep.write_shape(path, section)

    def test_zero_width_native_box_is_rejected(self):
        with self.assertRaises(ValueError):
            prep.box_shape([0,0,0,1,1,0])


if __name__ == '__main__':
    unittest.main()
