import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('comparison',Path(__file__).with_name('compare_to_base.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ComparisonTest(unittest.TestCase):
    def rows(self):
        return [{'mesh':mesh,'case':case,'ratios':{'displacement_max_mm':.99,
                'integration_point_VM_max_MPa':.89,'volume_above_900_mm3':.79}}
                for mesh in ('mesh-9','mesh-7')
                for case in ('combined-rigid-static','combined-spring-1000-static')]

    def test_all_objectives_pass(self):
        result=module.decide(self.rows(),1.293,1.30,True,.9,.8)
        self.assertTrue(result['reinforcement_objectives_pass'])

    def test_one_peak_regression_fails(self):
        rows=self.rows();rows[0]['ratios']['integration_point_VM_max_MPa']=1.001
        result=module.decide(rows,1.293,1.30,True,.9,.8)
        self.assertFalse(result['comparative_non_regression_pass'])

    def test_no_regression_is_not_the_improvement_objective(self):
        rows=self.rows();rows[1]['ratios']['integration_point_VM_max_MPa']=.95
        result=module.decide(rows,1.293,1.30,True,.9,.8)
        self.assertTrue(result['comparative_non_regression_pass'])
        self.assertFalse(result['reinforcement_objectives_pass'])

    def test_missing_case_and_failed_V6f_are_refused(self):
        self.assertFalse(module.decide(self.rows()[:3],1.293,1.30,True,.9,.8)['comparative_non_regression_pass'])
        self.assertFalse(module.decide(self.rows(),1.293,1.30,False,.9,.8)['comparative_non_regression_pass'])


if __name__=='__main__': unittest.main()
