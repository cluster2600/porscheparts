"""Prepare a small fact-rich curriculum and pin the newer compact Qwen base."""
import argparse,json
from pathlib import Path
import format_qwen,prepare_corrective,verify_grounded,evidence_profile
HERE=Path(__file__).resolve().parent
SELECTED={'ground-'+str(i).zfill(3) for i in (1,3,5,7,17,19,20,21,22,26,29,30)}

def build(output,snapshot):
 from transformers import AutoTokenizer
 if output.exists():raise ValueError('Use a fresh model/data release')
 verify_grounded.verify(HERE,HERE/'grounded-v3')
 profile=verify_grounded.load(HERE/'evidence-profile.json')
 tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True)
 paragraphs={p['passage_id']:p for p in verify_grounded.rows(HERE/'grounded-v3/passages.jsonl')}
 cases=verify_grounded.load(HERE/'grounded-input/cases.json')
 records=[];tokens=[]
 for case in cases:
  if case['case_id'] not in SELECTED:continue
  citation=f"[{case['source_id']}:p{case['paragraph']}]";p=paragraphs[citation]
  if p['split']!='train':raise ValueError('Held-out source in curriculum')
  for lang in ('fr','en'):
   variant=case['variants'][lang];quote=case['evidence_quotes'][0] if case['evidence_quotes'] else None
   if quote and quote not in p['text']:raise ValueError('Evidence quote missing')
   target=('“'+quote+'” '+citation+'\n' if quote else '')+variant['answer']+' '+citation
   messages=prepare_corrective.message(lang,variant['question'],p['text'],citation,target)
   messages[0]['content']+=' '+profile['system_suffix'][lang]
   data,start,end=format_qwen.assistant_tokens(messages,tokenizer,1536)
   records.append({'id':case['case_id']+'-'+lang,'language':lang,'source_id':p['source_id'],'passage_id':citation,'messages':messages,'assistant_start':start,'assistant_eos':end,'evidence_quote':quote,'expert_review':'pending'})
   tokens.append(data)
 output.mkdir(parents=True)
 prepare_corrective.dump_rows(output/'train-records.jsonl',records);prepare_corrective.dump_rows(output/'train-tokens.jsonl',tokens)
 model_id='Qwen/Qwen3-4B-Instruct-2507';revision='cdbee75f17c01a7cc42f958dc650907174af0554'
 names=('config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt')
 model_profile={'model_id':model_id,'revision':revision,'tokenizer_files_sha256':{name:verify_grounded.sha(snapshot/name) for name in names},'chat_template_sha256':__import__('hashlib').sha256(tokenizer.chat_template.encode()).hexdigest(),'source':'https://huggingface.co/'+model_id+'/tree/'+revision,'license':'Apache 2.0','parameters':4022468096,'dtype':'bfloat16'}
 prepare_corrective.save(output/'model-profile.json',model_profile)
 (output/'MODEL-LICENSE.txt').write_bytes((snapshot/'LICENSE').read_bytes())
 manifest={'status':'prepared_fact_rich_compact_curriculum','train_rows':len(records),'case_families':len(SELECTED),'sequence_tokens':sum(len(t['input_ids']) for t in tokens),'assistant_tokens':sum(sum(i!=-100 for i in t['labels']) for t in tokens),'maximum_tokens':max(len(t['input_ids']) for t in tokens),'training_sources':sorted({r['source_id'] for r in records}),'parent_manifest_sha256':verify_grounded.sha(HERE/'grounded-v3/manifest.json'),'evidence_profile_sha256':verify_grounded.sha(HERE/'evidence-profile.json'),'producer_sha256':verify_grounded.sha(HERE/'prepare_compact.py'),'expert_review':'pending','files_sha256':{p.name:verify_grounded.sha(p) for p in output.iterdir() if p.is_file()}}
 prepare_corrective.save(output/'manifest.json',manifest);print(json.dumps({k:manifest[k] for k in ('train_rows','sequence_tokens','assistant_tokens','maximum_tokens')}))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--snapshot',type=Path,required=True);args=parser.parse_args();build(args.output.resolve(),args.snapshot.resolve())
