"""Choose a scope or factual prompt using only generic question-language markers."""
import copy,re
from pathlib import Path
import verify_grounded as v,source_precision_profile,condition_fidelity_profile
HERE=Path(__file__).resolve().parent

def questions_with_profile(questions):
 profile=v.load(HERE/'task-routed-profile.json')
 for name,sha in profile['backend_inputs_sha256'].items():
  if v.sha(HERE/name)!=sha:raise ValueError('Pinned task backend changed: '+name)
 result=[]
 for question in questions:
  row=copy.deepcopy(question)
  text=row.get('question',row['messages'][-1]['content'].split('REFERENCE:',1)[0].split('EXCERPT ',1)[0]).casefold()
  scope=any(term in text for term in profile['scope_keywords'])
  factual=any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text) if term.isascii() else term in text for term in profile['factual_markers'])
  helper=source_precision_profile if scope or not factual else condition_fidelity_profile
  expanded=helper.questions_with_profile([row])[0]
  expanded['inference_task_route']='scope' if helper is source_precision_profile else 'factual'
  result.append(expanded)
 return result
