import importlib.util
import math
from pathlib import Path
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location('ported_chamber',DIR/'build_ported_chamber_candidate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PortedChamberTests(unittest.TestCase):
    def test_wall_samples_measure_material_not_old_body_distance(self):
        summary=module.wall_summary([{'status':'resolved','material_segment_length':.8},
            {'status':'resolved','material_segment_length':3.}, {'status':'unresolved_no_verified_material_exit'}])
        self.assertEqual(summary['minimum_resolved_material_segment'],.8)
        self.assertEqual(summary['resolved_below_screening_limit'],1)
        self.assertEqual(summary['unresolved'],1)
        self.assertFalse(summary['global_minimum_verified'])
        with self.assertRaises(ValueError):module.wall_summary([{'status':'resolved','material_segment_length':math.nan}])

    def test_empty_wall_screen_never_qualifies_global_wall(self):
        summary=module.wall_summary([])
        self.assertIsNone(summary['minimum_resolved_material_segment'])
        self.assertFalse(summary['global_minimum_verified'])
        self.assertIn('incomplete',module.candidate_screen(True,1,0.,[0.],summary))

    def test_unexpected_contact_housing_loss_and_thin_wall_remain_rejected(self):
        wall=module.wall_summary([{'status':'resolved','material_segment_length':2.}])
        self.assertEqual(module.candidate_screen(False,1,0.,[],wall),'rejected_native_integrity')
        self.assertEqual(module.candidate_screen(True,1,.1,[],wall),'rejected_unexpected_boundary_contacts')
        self.assertEqual(module.candidate_screen(True,1,0.,[.1],wall),'rejected_housing_contact_loss_requires_design_review')
        self.assertEqual(module.candidate_screen(True,1,0.,[-.1],wall),'rejected_nonconservative_housing_contact_increase')
        thin=module.wall_summary([{'status':'resolved','material_segment_length':1.}])
        self.assertEqual(module.candidate_screen(True,1,0.,[0.],thin),'rejected_sampled_thin_material_requires_design_review')


if __name__=='__main__':unittest.main()
