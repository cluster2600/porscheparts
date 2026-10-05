"""Retokenize the frozen 53 factual examples for concise Qwen3 precision SFT."""
import argparse,json,copy
from pathlib import Path
import format_qwen,verify_grounded as v,run_corrective as u,precision_profile
HERE=Path(__file__).resolve().parent

def build(output,snapshot):
 from transformers import AutoTokenizer
 if output.exists():raise ValueError('Use a fresh precision release')
 u.audit();tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True)
 old=[r for r in v.rows(HERE/'corrective-v4/train-records.jsonl') if r['kind']=='original_positive']
 if len(old)!=53:raise ValueError('Original factual curriculum incomplete')
 records=[];tokens=[]
 for row in old:
  r=copy.deepcopy(row);target=r['messages'][-1]
  q={**r,'messages':r['messages'][:2]}
  if r['language'] in ('fr','en','de','zh'):messages=precision_profile.questions_with_profile([q])[0]['messages']+[target]
  else:
   messages=copy.deepcopy(r['messages']);messages[0]['content']+=' Answer only the requested facts, briefly, in the requested language. Keep the exact property types and evidence conditions; do not infer causality from co-occurrence. End with the supplied reference.'
  data,start,end=format_qwen.assistant_tokens(messages,tokenizer,1536)
  r.update(messages=messages,assistant_start=start,assistant_eos=end,kind='precision_original_factual');records.append(r);tokens.append(data)
 output.mkdir(parents=True);u.dump(output/'train-records.jsonl',records);u.dump(output/'train-tokens.jsonl',tokens)
 profile=v.load(HERE/'compact-qwen3-v5/model-profile.json');u.save(output/'model-profile.json',profile)
 (output/'MODEL-LICENSE.txt').write_bytes((HERE/'compact-qwen3-v5/MODEL-LICENSE.txt').read_bytes())
 manifest={'status':'prepared_precision_factual_curriculum','train_rows':len(records),'case_families':len({r['id'].rsplit('-',1)[0] for r in records}),'sequence_tokens':sum(len(t['input_ids']) for t in tokens),'assistant_tokens':sum(sum(x!=-100 for x in t['labels']) for t in tokens),'maximum_tokens':max(len(t['input_ids']) for t in tokens),'training_sources':sorted({r['source_id'] for r in records}),'parent_manifest_sha256':v.sha(HERE/'grounded-v3/manifest.json'),'corrective_parent_manifest_sha256':v.sha(HERE/'corrective-v4/manifest.json'),'profile_sha256':v.sha(HERE/'precision-profile.json'),'profile_helper_sha256':v.sha(HERE/'precision_profile.py'),'producer_sha256':v.sha(HERE/'prepare_precision.py'),'expert_review':'pending','training_policy':'Original 53 factual examples only; no source-held-out or retired-test examples added to SFT. Targets unchanged; native Qwen3 template and assistant-only masks.','files_sha256':{p.name:v.sha(p) for p in output.iterdir() if p.is_file()}}
 u.save(output/'manifest.json',manifest);print(json.dumps({k:manifest[k] for k in ('train_rows','sequence_tokens','assistant_tokens','maximum_tokens')}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('output','snapshot'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();build(a.output.resolve(),a.snapshot.resolve())
