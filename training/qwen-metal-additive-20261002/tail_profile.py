"""Apply an explicit source-reference reminder after the supplied evidence."""
import copy,re
from pathlib import Path
import verify_grounded
HERE=Path(__file__).resolve().parent

def questions_with_profile(questions):
 profile=verify_grounded.load(HERE/'tail-profile.json');result=[]
 for question in questions:
  row=copy.deepcopy(question);language=row.get('language','fr');user=copy.deepcopy(row['messages'][-1])
  references=re.findall(r'\[[\w]+:p\d+\]',user['content'])
  if not references:raise ValueError('No supplied evidence reference')
  reference=row.get('passage_id',references[-1])
  if reference not in references:raise ValueError('Reference does not match supplied evidence')
  user['content']+='\n\nRESPONSE FORMAT: '+profile['tail'][language].format(reference=reference)
  row['messages']=[{'role':'system','content':profile['system'][language]},user]
  result.append(row)
 return result
