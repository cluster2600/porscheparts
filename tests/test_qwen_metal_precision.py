"""Precision curriculum isolation, semantic scope and rejected-trial integrity."""
import importlib.util,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'training/qwen-metal-additive-20261002'
def module(name):
 sys.path.insert(0,str(ROOT))
 try:
  spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 finally:sys.path.remove(str(ROOT))
class PrecisionTest(unittest.TestCase):
 def test_new_test_paragraphs_are_outside_actual_training(self):
  cfg,root,manifest,_=module('run_precision').audit();v=module('verify_grounded')
  train=v.rows(root/'train-records.jsonl');new=[q for name in ('precision-final-test.jsonl','precision-domain-benchmark.jsonl') for q in v.rows(ROOT/name)]
  self.assertEqual(manifest['train_rows'],59)
  self.assertEqual(len(new),20)
  self.assertEqual(len({q['passage_id'] for q in new}),20)
  self.assertFalse({q['passage_id'] for q in new}&{r['passage_id'] for r in train})
  self.assertEqual(len(manifest['training_sources']),6)
  self.assertEqual(sum('retired-training-family-' in r['id'] for r in train),6)
 def test_source_words_do_not_trigger_precision_qualification_route(self):
  q={'language':'fr','messages':[{'role':'user','content':'Quels effets sont cités ?\n\nEXCERPT [MET001:p33]: qualification certification'}]}
  response=module('precision_terminology_profile').questions_with_profile([q])[0]
  self.assertNotIn('La question demande une certification',response['messages'][-1]['content'])
  self.assertIn('pression de recul',response['messages'][0]['content'])
 def test_failed_trial_cannot_be_promoted_by_editing_status_and_hashes(self):
  v=module('verify_grounded');verify=module('verify_compact_package')
  with tempfile.TemporaryDirectory() as folder:
   copied=Path(folder)/'trial';shutil.copytree(ROOT/'runs/qwen3-compact-001',copied)
   assessment=json.loads((copied/'assistant-final-assessment.json').read_text());assessment['status']='accepted_on_registered_benchmark'
   (copied/'assistant-final-assessment.json').write_text(json.dumps(assessment))
   manifest=json.loads((copied/'package-manifest.json').read_text());manifest['status']=assessment['status'];manifest['files_sha256']['assistant-final-assessment.json']=v.sha(copied/'assistant-final-assessment.json')
   (copied/'package-manifest.json').write_text(json.dumps(manifest))
   with self.assertRaisesRegex(ValueError,'Acceptance claim disagrees'):verify.verify(copied)
if __name__=='__main__':unittest.main()
