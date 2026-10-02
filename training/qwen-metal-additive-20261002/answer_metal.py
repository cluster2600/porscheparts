"""Answer a question against an explicit licensed passage with a selected adapter."""
import argparse,json,re
from pathlib import Path
import prepare_corrective
import verify_grounded
HERE=Path(__file__).resolve().parent

def check_answer(answer,citation):
 cited=set(re.findall(r'\[[\w]+:p\d+\]',answer))
 return citation in cited and not (cited-{citation})

def answer(adapter,cache,passage_id,question,language):
 # Explicit passage selection makes evidence inspectable; no opaque retrieval score.
 from transformers import AutoTokenizer,AutoModelForCausalLM
 from peft import PeftModel
 import torch
 passages={p['passage_id']:p for p in verify_grounded.rows(HERE/'grounded-v3/passages.jsonl')}
 if passage_id not in passages:raise ValueError('Unknown registered passage')
 p=passages[passage_id];sources={s['source_id']:s for s in verify_grounded.load(HERE/'grounded-v3/sources.json')}
 cfg=verify_grounded.load(adapter/'adapter_config.json')
 model_id='Qwen/Qwen2.5-1.5B-Instruct';revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
 if (cfg['base_model_name_or_path'],cfg['revision'])!=(model_id,revision):raise ValueError('Adapter uses a different base')
 torch.set_num_threads(4)
 tokenizer=AutoTokenizer.from_pretrained(model_id,revision=revision,cache_dir=str(cache))
 messages=prepare_corrective.message(language,question,p['text'],passage_id)
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
 return {'status':'answer_generated' if citation_pass and complete else 'answer_withheld','answer':text,'reference':{k:source[k] for k in ('source_id','title','doi','url')},'passage_id':passage_id,'excerpt':p['text'],'checks':{'expected_citation':citation_pass,'complete_under_token_budget':complete},'independent_expert_validated':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--adapter',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--passage',required=True);parser.add_argument('--question',required=True);parser.add_argument('--language',choices=['fr','en','de','zh'],default='fr');args=parser.parse_args();print(json.dumps(answer(args.adapter.resolve(),args.cache.resolve(),args.passage,args.question,args.language),ensure_ascii=False,indent=2))
