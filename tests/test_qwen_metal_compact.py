"""Pinned compact base, factual curriculum and training-only demonstrations."""
import importlib.util
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]/'training/qwen-metal-additive-20261002'
def module(name):
 sys.path.insert(0,str(ROOT))
 try:
  spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 finally:sys.path.remove(str(ROOT))
class CompactTest(unittest.TestCase):
 def test_compact_base_and_dataset_pin_are_coupled(self):
  cfg,_,manifest,profile=module('run_compact').audit()
  self.assertEqual(manifest['train_rows'],24)
  self.assertEqual(cfg['model_id'],'Qwen/Qwen3-4B-Instruct-2507')
  self.assertEqual(cfg['revision'],profile['revision'])
  self.assertTrue(cfg['training']['gradient_checkpointing'])
  self.assertEqual(manifest['maximum_tokens'],837)
 def test_evidence_demonstrations_preserve_the_actual_final_question(self):
  helper=module('evidence_profile')
  q={'id':'probe','language':'fr','messages':[{'role':'system','content':'Answer precisely.'},{'role':'user','content':'Actual question with [NEW_WAAM:p45].'}]}
  r=helper.questions_with_profile([q])[0]
  self.assertEqual(r['messages'][-1],q['messages'][-1])
  self.assertEqual([m['role'] for m in r['messages']],['system','user','assistant','user','assistant','user'])
  self.assertEqual(len(q['messages']),2)
 def test_qualified_profile_keeps_evidence_and_explicit_reference(self):
  helper=module('concise_qualified_profile_v7')
  q={'id':'probe','language':'fr','messages':[{'role':'system','content':'old'},{'role':'user','content':'Une valeur certifiée ? EXCERPT [MET002:p1]: copper text.'}]}
  r=helper.questions_with_profile([q])[0]
  self.assertEqual(len(r['messages']),2)
  self.assertTrue(r['messages'][-1]['content'].startswith(q['messages'][-1]['content']))
  self.assertIn('certification',r['messages'][-1]['content'])
  self.assertTrue(r['messages'][-1]['content'].endswith('[MET002:p1].'))
  self.assertEqual(len(q['messages']),2)
 def test_qualified_profile_rejects_mismatched_evidence_id(self):
  q={'language':'en','passage_id':'[MET003:p8]','messages':[{'role':'user','content':'EXCERPT [MET002:p1]: copper'}]}
  with self.assertRaisesRegex(ValueError,'Reference does not match'):module('concise_qualified_profile_v7').questions_with_profile([q])
 def test_ordinary_questions_keep_the_measured_concise_profile(self):
  q={'language':'fr','messages':[{'role':'user','content':'Question ordinaire. REFERENCE: source EXCERPT [MET002:p1]: qualification data.'}]}
  self.assertEqual(module('concise_qualified_profile_v7').questions_with_profile([q]),module('tail_profile').questions_with_profile([q]))
 def test_excerpt_words_do_not_route_real_inference_messages(self):
  q={'language':'fr','messages':[{'role':'user','content':'Explique la conduction.\n\nEXCERPT [MET002:p1]: certification qualification'}]}
  r=module('concise_qualified_profile_v7').questions_with_profile([q])[0]
  self.assertNotIn('La question demande une certification',r['messages'][-1]['content'])
if __name__=='__main__':unittest.main()
