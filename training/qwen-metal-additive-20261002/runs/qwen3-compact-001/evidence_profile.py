"""Apply a registered quote-first profile with training-only demonstrations."""
import copy
from pathlib import Path
import verify_grounded
HERE=Path(__file__).resolve().parent

def questions_with_profile(questions):
 profile=verify_grounded.load(HERE/'evidence-profile.json')
 passages={p['passage_id']:p for p in verify_grounded.rows(HERE/'grounded-v3/passages.jsonl')}
 if any(passages[p]['split']!='train' for p in profile['demonstration_passages']):raise ValueError('Demonstration leaks held-out source')
 result=[]
 for question in questions:
  row=copy.deepcopy(question);lang=row.get('language','fr')
  original=row['messages']
  row['messages']=[{'role':'system','content':original[0]['content']+' '+profile['system_suffix'][lang]},*copy.deepcopy(profile['demonstrations'][lang]),original[1]]
  result.append(row)
 return result
