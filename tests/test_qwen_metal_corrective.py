"""Corrective data boundaries and rejection of lexical false positives."""
import importlib.util,json
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]/'training/qwen-metal-additive-20261002'
def module(name):
 sys.path.insert(0,str(ROOT))
 try:
  spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 finally:sys.path.remove(str(ROOT))
class CorrectiveTest(unittest.TestCase):
 def test_answer_guard_rejects_an_invented_or_missing_reference(self):
  inference=module('answer_metal')
  self.assertTrue(inference.check_answer('Convection et rayonnement. [MET002:p22]','[MET002:p22]'))
  self.assertFalse(inference.check_answer('Convection et rayonnement.','[MET002:p22]'))
  self.assertFalse(inference.check_answer('[MET002:p22] et [UNKNOWN:p1]','[MET002:p22]'))
 def test_release_audit_and_source_isolation(self):
  runner=module('run_corrective');_,_,manifest=runner.audit()
  self.assertEqual(manifest['train_rows'],191)
  self.assertFalse(set(manifest['training_sources'])&set(manifest['final_test_sources']))
  self.assertEqual(manifest['final_test_count'],12)
 def test_incomplete_final_predictions_are_rejected(self):
  evaluator=module('evaluate_corrective')
  with self.assertRaisesRegex(ValueError,'Predictions missing'):
   evaluator.screen([{'id':'missing'}],[])
 def test_missing_value_with_guessed_temperature_fails_screen(self):
  evaluator=module('evaluate_corrective')
  q={'id':'probe','passage_id':'[NEW_WAAM:p45]','required_groups':[['ne','pas']],'critical_boundary':True}
  prediction={'id':'probe','response':'Ne le faites pas sans validation. Je conseille 450 °C. [NEW_WAAM:p45]','reached_token_budget':False}
  result=evaluator.screen([q],[prediction])
  self.assertEqual(result['automated_screen_passes'],0)
  self.assertEqual(result['critical_boundary_screen_failures'],1)
 def test_unqualified_yes_is_rejected_on_critical_development_question(self):
  runner=module('run_corrective')
  q={'id':'eval-004','messages':[{}, {'content':'EXCERPT [NEW_QUALITY:p23]:'}]}
  p={'response':'Oui, la précision est universelle. [NEW_QUALITY:p23]','reached_token_budget':False}
  self.assertEqual(runner.development_screen([q],[p])['critical_boundaries_pass'],0)
if __name__=='__main__':unittest.main()
