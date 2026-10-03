"""Apply an explicit source-reference reminder after the supplied evidence."""
import copy,re
from pathlib import Path
import verify_grounded
HERE=Path(__file__).resolve().parent

def questions_with_profile(questions):
 profile=verify_grounded.load(HERE/'condition-fidelity-profile.json');result=[]
 for question in questions:
  row=copy.deepcopy(question);language=row.get('language','fr');user=copy.deepcopy(row['messages'][-1])
  references=re.findall(r'\[[\w]+:p\d+\]',user['content'])
  if not references:raise ValueError('No supplied evidence reference')
  reference=row.get('passage_id',references[-1])
  if reference not in references:raise ValueError('Reference does not match supplied evidence')
  question_text=row.get('question',user['content'].split('REFERENCE:',1)[0].split('EXCERPT ',1)[0])
  needs_qualification=any(term in question_text.casefold() for term in profile['qualification_keywords'])
  tail=(profile['qualification_tail'][language] if needs_qualification else '')+profile['tail'][language]
  user['content']+='\n\nRESPONSE FORMAT: '+tail.format(reference=reference)
  system=profile['system'][language]
  source=user['content'].split('EXCERPT ',1)[-1].split('RESPONSE FORMAT:',1)[0]
  if language=='fr':
   terms=[translation for term,translation in profile['source_term_translations_fr'].items() if term in source.casefold()]
   if re.search(r'\bRSs?\b',source):terms.append('RS : contraintes résiduelles')
   if terms:system+=' Terminologie présente dans cet extrait : '+' ; '.join(terms)+'.'
  row['messages']=[{'role':'system','content':system},user]
  result.append(row)
 return result
