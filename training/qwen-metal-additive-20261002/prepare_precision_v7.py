"""Retokenize the frozen 53 factual examples for concise Qwen3 precision SFT."""
import argparse,json,copy
from pathlib import Path
import format_qwen,verify_grounded as v,run_corrective as u,precision_terminology_profile
HERE=Path(__file__).resolve().parent

def build(output,snapshot):
 from transformers import AutoTokenizer
 if output.exists():raise ValueError('Use a fresh precision release')
 u.audit();tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True)
 old=[r for r in v.rows(HERE/'corrective-v4/train-records.jsonl') if r['kind']=='original_positive']
 if len(old)!=53:raise ValueError('Original factual curriculum incomplete')
 passages={p['passage_id']:p for p in v.rows(HERE/'grounded-v3/passages.jsonl')}
 extras=[('[MET001:p33]',{'fr':('Quels deux effets le passage cite-t-il pour l’écoulement du bain ?', 'Le passage cite la pression de recul (recoil pressure) et la convection de Marangoni.'),'en':('Which two effects does the passage name for melt-pool flow?', 'The passage names recoil pressure and Marangoni convection.')}),('[MET002:p28]',{'fr':('Quelle tendance expérimentale densité/conductivité est rapportée ici ?', 'Dans l’étude citée, les échantillons de cuivre plus denses présentent une conductivité thermique plus élevée. Il s’agit d’une tendance observée dans ces conditions.'),'en':('What density/conductivity experimental trend is reported here?', 'In the cited study, denser copper samples exhibit higher thermal conductivity. This is an observed trend under the reported conditions.')}),('[thermal_en_prediction:p4]',{'fr':('Dans quelles conditions l’erreur inférieure à 20 % est-elle rapportée ?', 'L’erreur inférieure à 20 % est rapportée à température ambiante pour le modèle simplifié utilisant d₅₀ ; aucune garantie à une autre température n’est fournie ici.'),'en':('Under what conditions is the error below 20% reported?', 'The error below 20% is reported at room temperature for the simplified model using d₅₀; this excerpt provides no guarantee at another temperature.')})]
 for n,(pid,variants) in enumerate(extras,1):
  passage=passages[pid]
  if passage['split']!='train':raise ValueError('Retired held-out source cannot enter SFT')
  for lang,(question,answer) in variants.items():
   old.append({'id':f'retired-training-family-{n}-{lang}','language':lang,'source_id':passage['source_id'],'passage_id':pid,'excerpt':passage['text'],'messages':u.load(HERE/'corrective-v4/train-records.jsonl') if False else __import__('prepare_corrective').message(lang,question,passage['text'],pid,answer+' '+pid),'expert_review':'pending','origin':'Assistant-authored correction using retired domain passages from training-source families; not part of new benchmark.'})
 records=[];tokens=[]
 for row in old:
  r=copy.deepcopy(row);target=r['messages'][-1]
  q={**r,'messages':r['messages'][:2]}
  if r['language'] in ('fr','en','de','zh'):messages=precision_terminology_profile.questions_with_profile([q])[0]['messages']+[target]
  else:
   messages=copy.deepcopy(r['messages']);messages[0]['content']+=' Answer only the requested facts, briefly, in the requested language. Keep the exact property types and evidence conditions; do not infer causality from co-occurrence. End with the supplied reference.'
  data,start,end=format_qwen.assistant_tokens(messages,tokenizer,1536)
  r.update(messages=messages,assistant_start=start,assistant_eos=end,kind='precision_original_factual');records.append(r);tokens.append(data)
 output.mkdir(parents=True);u.dump(output/'train-records.jsonl',records);u.dump(output/'train-tokens.jsonl',tokens)
 profile=v.load(HERE/'compact-qwen3-v5/model-profile.json');u.save(output/'model-profile.json',profile)
 (output/'MODEL-LICENSE.txt').write_bytes((HERE/'compact-qwen3-v5/MODEL-LICENSE.txt').read_bytes())
 manifest={'status':'prepared_precision_factual_curriculum','train_rows':len(records),'case_families':len({r['id'].rsplit('-',1)[0] for r in records}),'sequence_tokens':sum(len(t['input_ids']) for t in tokens),'assistant_tokens':sum(sum(x!=-100 for x in t['labels']) for t in tokens),'maximum_tokens':max(len(t['input_ids']) for t in tokens),'training_sources':sorted({r['source_id'] for r in records}),'parent_manifest_sha256':v.sha(HERE/'grounded-v3/manifest.json'),'corrective_parent_manifest_sha256':v.sha(HERE/'corrective-v4/manifest.json'),'profile_sha256':v.sha(HERE/'precision-terminology-profile.json'),'profile_helper_sha256':v.sha(HERE/'precision_terminology_profile.py'),'producer_sha256':v.sha(HERE/'prepare_precision_v7.py'),'expert_review':'pending','training_policy':'Original 53 factual targets unchanged, plus six correction examples from three retired domain paragraphs of training-source families. No held-out-source text or new registered benchmark paragraphs in SFT. Native Qwen3 template and assistant-only masks.','files_sha256':{p.name:v.sha(p) for p in output.iterdir() if p.is_file()}}
 u.save(output/'manifest.json',manifest);print(json.dumps({k:manifest[k] for k in ('train_rows','sequence_tokens','assistant_tokens','maximum_tokens')}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('output','snapshot'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();build(a.output.resolve(),a.snapshot.resolve())
