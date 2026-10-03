"""Audit the third registered benchmark against frozen sources and exclusions."""
from pathlib import Path
import run_compact,run_precision,run_corrective as u,verify_grounded as v
HERE=Path(__file__).resolve().parent

def audit():
 cfg,root,manifest,profile=run_compact.audit();run_precision.audit()
 primary=u.load(HERE/'fidelity-test-manifest.json');domain=u.load(HERE/'fidelity-domain-manifest.json')
 for m in (primary,domain):
  if m['parent_source_manifest_sha256']!=v.sha(HERE/'grounded-v3/manifest.json'):raise ValueError('Source release changed')
  for name,sha in m.get('files_sha256',{}).items():
   if v.sha(HERE/name)!=sha:raise ValueError('Registered fidelity input changed: '+name)
  for name,sha in m['excluded_inputs_sha256'].items():
   if v.sha(HERE/name)!=sha:raise ValueError('Excluded benchmark/training changed: '+name)
 if v.sha(HERE/'fidelity-domain-benchmark.jsonl')!=domain['benchmark_sha256']:raise ValueError('Domain benchmark changed')
 questions=v.rows(HERE/'fidelity-final-test.jsonl')+v.rows(HERE/'fidelity-domain-benchmark.jsonl')
 if len(questions)!=20 or len({q['passage_id'] for q in questions})!=20:raise ValueError('Repeated or missing new paragraphs')
 if {q['passage_id'] for q in questions}&set(primary['excluded_passage_ids']):raise ValueError('New benchmark reuses a retired paragraph')
 passages={p['passage_id']:p for p in v.rows(HERE/'grounded-v3/passages.jsonl')}
 import hashlib
 for q in questions:
  p=passages[q['passage_id']]
  if q['source_id']!=p['source_id'] or q['excerpt_sha256']!=hashlib.sha256(p['text'].encode()).hexdigest():raise ValueError('Source excerpt mismatch')
  if q['messages'][-1]['content'].split('EXCERPT '+q['passage_id']+':\n',1)[-1]!=p['text']:raise ValueError('Registered question excerpt changed')
 return cfg,root,manifest,profile
if __name__=='__main__':
 print({'status':'pass','questions':20,'independent_expert_validated':False} if audit() else {})
