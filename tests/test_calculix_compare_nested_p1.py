"""Case identity and actual parent/child binding must precede energy comparison."""
import copy
import importlib.util
from pathlib import Path
import unittest
SPEC=importlib.util.spec_from_file_location('nested_p1',Path(__file__).resolve().parents[1]/'scripts/calculix_compare_nested_p1.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)
def report(case,declared=True):
 result={'source_sha256':{'/fixture/run/current-'+case+'/case/job.dat':'dat'},'payload_source_sha256':{'groups.npz':'supports','gravity-serialized-loads.npz':'gravity','combined-serialized-loads.npz':'combined'}}
 if declared:result['load_case']=case
 return result
class NestedP1Tests(unittest.TestCase):
 def test_qualified_energy_and_compliance_controls(self):
  self.assertTrue(all(MODULE.controls().values()))
 def test_actual_parent_children_and_corrupted_connectivity_controls(self):
  self.assertTrue(all(MODULE.nesting_controls().values()))
 def test_identical_combined_case_is_admitted(self):
  self.assertTrue(MODULE.load_binding(report('combined'),report('combined'),'combined'))
 def test_legacy_gravity_requires_its_actual_execution_path(self):
  self.assertTrue(MODULE.load_binding(report('gravity',False),report('gravity',False),'gravity'))
  wrong=report('combined',False)
  with self.assertRaises(AssertionError):MODULE.load_binding(wrong,report('gravity',False),'gravity')
 def test_gravity_and_combined_are_not_interchangeable(self):
  with self.assertRaises(AssertionError):MODULE.load_binding(report('gravity'),report('combined'),'combined')
 def test_matching_gravity_hash_cannot_hide_changed_combined_loads(self):
  source=report('combined');refined=copy.deepcopy(source);refined['payload_source_sha256']['combined-serialized-loads.npz']='different'
  with self.assertRaises(AssertionError):MODULE.load_binding(source,refined,'combined')
 def test_changed_supports_are_refused(self):
  source=report('combined');refined=copy.deepcopy(source);refined['payload_source_sha256']['groups.npz']='different'
  with self.assertRaises(AssertionError):MODULE.load_binding(source,refined,'combined')
 def test_missing_combined_declaration_is_refused(self):
  with self.assertRaises(AssertionError):MODULE.load_binding(report('combined',False),report('combined'),'combined')
 def test_declared_case_cannot_override_actual_DAT_path(self):
  source=report('gravity');source['load_case']='combined'
  with self.assertRaises(AssertionError):MODULE.load_binding(source,report('combined'),'combined')
if __name__=='__main__':unittest.main()
