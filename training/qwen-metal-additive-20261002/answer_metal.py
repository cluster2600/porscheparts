"""Answer a question against an explicit licensed passage with a selected adapter."""
import argparse,json,re
from pathlib import Path
import prepare_corrective
import concise_qualified_profile_v7
import precision_terminology_profile
import source_precision_profile
import fidelity_profile
import condition_fidelity_profile
import task_routed_profile
import verify_grounded
HERE=Path(__file__).resolve().parent

def check_answer(answer,citation):
 cited=set(re.findall(r'\[[\w]+:p\d+\]',answer))
 return citation in cited and not (cited-{citation})

def resolve_profile(adapter,model_id,revision,profile_name=None):
 package_path=adapter.parent/'package-manifest.json'
 package=verify_grounded.load(package_path) if package_path.exists() else {}
 if package:
  for name in ('adapter/adapter_model.safetensors','adapter/adapter_config.json'):
   if verify_grounded.sha(adapter.parent/name)!=package['files_sha256'][name]:raise ValueError('Packaged adapter changed')
  if (package['model_id'],package['revision'])!=(model_id,revision):raise ValueError('Package base pin mismatch')
 if model_id=='Qwen/Qwen3-4B-Instruct-2507' and not package and profile_name is None:raise ValueError('An unpackaged Qwen3 adapter needs an explicit --profile; use the reviewed package for final inference')
 expected_profile=package.get('inference_profile','compact-v7')
 if package and profile_name is not None and profile_name!=expected_profile:raise ValueError('Explicit profile disagrees with reviewed package')
 helper=None
 if model_id=='Qwen/Qwen3-4B-Instruct-2507':
  registry={'compact-v7':concise_qualified_profile_v7,'precision-v9':precision_terminology_profile,'source-v10':source_precision_profile,'fidelity-v11':fidelity_profile,'fidelity-v12':condition_fidelity_profile,'task-v14':task_routed_profile}
  if (profile_name or expected_profile) not in registry:raise ValueError('Unknown packaged inference profile')
  helper=registry[profile_name or expected_profile]
  if package:
   receipt_path=adapter.parent/'final-receipt.json'
   if verify_grounded.sha(receipt_path)!=package['files_sha256']['final-receipt.json']:raise ValueError('Packaged inference receipt changed')
   receipt=verify_grounded.load(receipt_path)
   profile_files={'compact-v7':'concise-qualified-profile.json','precision-v9':'precision-terminology-profile.json','source-v10':'source-precision-profile.json','fidelity-v11':'fidelity-profile.json','fidelity-v12':'condition-fidelity-profile.json','task-v14':'task-routed-profile.json'}
   if receipt['profile_helper_sha256']!=verify_grounded.sha(Path(helper.__file__)) or receipt['profile_sha256']!=verify_grounded.sha(HERE/profile_files[profile_name or expected_profile]):raise ValueError('Runtime inference profile differs from benchmark')
 return helper,package

def answer(adapter,cache,passage_id,question,language,profile_name=None):
 # Explicit passage selection makes evidence inspectable; no opaque retrieval score.
 from transformers import AutoTokenizer,AutoModelForCausalLM
 from peft import PeftModel
 import torch
 passages={p['passage_id']:p for p in verify_grounded.rows(HERE/'grounded-v3/passages.jsonl')}
 if passage_id not in passages:raise ValueError('Unknown registered passage')
 p=passages[passage_id];sources={s['source_id']:s for s in verify_grounded.load(HERE/'grounded-v3/sources.json')}
 cfg=verify_grounded.load(adapter/'adapter_config.json')
 pins={'Qwen/Qwen2.5-1.5B-Instruct':'989aa7980e4cf806f80c7fef2b1adb7bc71aa306','Qwen/Qwen3-4B-Instruct-2507':'cdbee75f17c01a7cc42f958dc650907174af0554'}
 model_id=cfg['base_model_name_or_path'];revision=cfg['revision']
 if pins.get(model_id)!=revision:raise ValueError('Adapter uses an unregistered base')
 torch.set_num_threads(4)
 tokenizer=AutoTokenizer.from_pretrained(model_id,revision=revision,cache_dir=str(cache))
 messages=prepare_corrective.message(language,question,p['text'],passage_id)
 helper,package=resolve_profile(adapter,model_id,revision,profile_name)
 if helper:messages=helper.questions_with_profile([{'id':'interactive','language':language,'messages':messages}])[0]['messages']
 inputs=tokenizer.apply_chat_template(messages,add_generation_prompt=True,tokenize=True,return_tensors='pt',return_dict=True,enable_thinking=False)
 if inputs['input_ids'].shape[-1]>4096:raise ValueError('Passage exceeds the inference context budget; choose shorter evidence')
 base=AutoModelForCausalLM.from_pretrained(model_id,revision=revision,cache_dir=str(cache),torch_dtype=torch.bfloat16,attn_implementation='sdpa')
 model=PeftModel.from_pretrained(base,str(adapter)).eval()
 with torch.inference_mode(),torch.autocast('cpu',dtype=torch.bfloat16):
  out=model.generate(**inputs,do_sample=False,max_new_tokens=192,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
 tokens=out[0,inputs['input_ids'].shape[-1]:];text=tokenizer.decode(tokens,skip_special_tokens=True).strip()
 citation_pass=check_answer(text,passage_id);complete=len(tokens)<192
 if not citation_pass or not complete:
  fallback={'fr':'La réponse générée ne passe pas le contrôle de citation ou de complétude. Consultez l’extrait fourni.','en':'The generated answer fails the citation or completeness check. Consult the supplied excerpt.','de':'Die erzeugte Antwort besteht die Quellen- oder Vollständigkeitsprüfung nicht. Bitte prüfen Sie den Auszug.','zh':'生成的回答未通过引用或完整性检查，请查看提供的摘录。'}
  text=fallback[language]+' '+passage_id
 source=sources[p['source_id']]
 return {'status':'answer_generated' if citation_pass and complete else 'answer_withheld','answer':text,'reference':{k:source[k] for k in ('source_id','title','doi','url')},'passage_id':passage_id,'excerpt':p['text'],'checks':{'expected_citation':citation_pass,'complete_under_token_budget':complete},'model_benchmark_status':package.get('status','unpackaged_adapter'),'independent_expert_validated':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--adapter',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--profile',choices=['compact-v7','precision-v9','source-v10','fidelity-v11','fidelity-v12','task-v14']);parser.add_argument('--passage',required=True);parser.add_argument('--question',required=True);parser.add_argument('--language',choices=['fr','en','de','zh'],default='fr');args=parser.parse_args();print(json.dumps(answer(args.adapter.resolve(),args.cache.resolve(),args.passage,args.question,args.language,args.profile),ensure_ascii=False,indent=2))
