"""Untouched-paragraph isolation and source-scoped terminology aids."""
import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'training/qwen-metal-additive-20261002'
def module(name):
 sys.path.insert(0,str(ROOT))
 try:
  spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 finally:sys.path.remove(str(ROOT))
class FidelityTest(unittest.TestCase):
 def test_third_benchmark_excludes_both_previous_final_sets(self):
  module('audit_fidelity').audit();v=module('verify_grounded')
  fresh=v.rows(ROOT/'fidelity-final-test.jsonl')+v.rows(ROOT/'fidelity-domain-benchmark.jsonl')
  retired=[q for name in ('corrective-v4/final-test.jsonl','corrective-domain-benchmark.jsonl','precision-final-test.jsonl','precision-domain-benchmark.jsonl') for q in v.rows(ROOT/name)]
  self.assertEqual(len(fresh),20);self.assertFalse({q['passage_id'] for q in fresh}&{q['passage_id'] for q in retired})
  self.assertEqual(sum(q['critical_boundary'] for q in fresh),7)
 def test_translation_aid_does_not_add_unrelated_property_types(self):
  helper=module('condition_fidelity_profile')
  q={'language':'fr','messages':[{'role':'user','content':'Que dit stress-rupture ?\n\nEXCERPT [MET004:p21]:\nJMAK describes diffusion-controlled transformations and grain impingement.'}]}
  out=helper.questions_with_profile([q])[0]['messages'][0]['content']
  self.assertIn('empiètement des grains',out);self.assertNotIn('stress-rupture',out);self.assertNotIn('fatigue',out)
 def test_residual_stress_abbreviation_is_recognized_without_substring_matches(self):
  helper=module('condition_fidelity_profile')
  q={'language':'fr','messages':[{'role':'user','content':'Que décrit le texte ?\n\nEXCERPT [NEW_WAAM:p28]:\nRS distribution varies.'}]}
  self.assertIn('RS : contraintes résiduelles',helper.questions_with_profile([q])[0]['messages'][0]['content'])
  q['messages'][0]['content']='Que décrit le texte ?\n\nEXCERPT [NEW_WAAM:p28]:\nResearchers describe temperature.'
  self.assertNotIn('RS : contraintes résiduelles',helper.questions_with_profile([q])[0]['messages'][0]['content'])
 def test_task_route_uses_question_not_source_keywords(self):
  helper=module('task_routed_profile')
  q={'language':'fr','messages':[{'role':'user','content':'Quels effets sont cités ?\n\nEXCERPT [MET001:p33]:\ncertification and qualification are mentioned.'}]}
  self.assertEqual(helper.questions_with_profile([q])[0]['inference_task_route'],'factual')
  q['messages'][0]['content']='Cette étude certifie-t-elle ma pièce ?\n\nEXCERPT [MET001:p33]:\nWhich physical effect is observed?'
  self.assertEqual(helper.questions_with_profile([q])[0]['inference_task_route'],'scope')
 def test_reused_scope_prompt_is_byte_equal_to_executed_input(self):
  v=module('verify_grounded');helper=module('task_routed_profile')
  raw=[q for q in v.rows(ROOT/'corrective-v4/development.jsonl') if q['id']=='eval-002'][0]
  old=[q for q in v.rows(ROOT/'runs/qwen3-source-profile-001/profile-development/questions.jsonl') if q['id']=='eval-002'][0]
  self.assertEqual(helper.questions_with_profile([raw])[0]['messages'],old['messages'])
if __name__=='__main__':unittest.main()
