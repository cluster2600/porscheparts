import hashlib,json,time
from pathlib import Path
from mlx_lm import load,stream_generate
from mlx_lm.sample_utils import make_sampler
import argparse
parser=argparse.ArgumentParser(description="Run the selected local Qwen adapter; retain raw, untrusted output")
parser.add_argument("model",type=Path)
parser.add_argument("adapter",type=Path)
parser.add_argument("output",type=Path)
parser.add_argument("--controlled",action="store_true")
args=parser.parse_args()
if args.output.exists(): raise FileExistsError(args.output)
model,adapter=args.model,args.adapter
messages=[{'role':'system','content':'Return only valid JSON. You propose unvalidated engineering experiments, never simulation results.'},{'role':'user','content':'Propose three organic fan blade parameter sets for CFD comparison. Keep existing 245 mm diameter, 11 blades, alternator hub, and 4.4 mm blade thickness unchanged. Baseline pitch=36, tip twist=-10, camber=-3.5, sweep=8, tip chord=70. Return an array of three objects with exactly these numeric keys: blade_pitch_deg (30 to 48), tip_twist_deg (-16 to -4), camber_mm (-5.5 to -2), sweep_mm (-8 to 16), blade_tip_chord_mm (60 to 80). Vary one parameter from baseline per object to separate effects. No claims about increased airflow.'}]
if args.controlled:
 messages=[{'role':'system','content':'Return a JSON object only. No explanation, code, assignment, Markdown, or arrays.'},{'role':'user','content':'Encode this unvalidated organic fan experiment as JSON with exactly five numeric fields: blade_pitch_deg=42, tip_twist_deg=-10, camber_mm=-3.5, sweep_mm=8, blade_tip_chord_mm=70.'}]
network,tokenizer=load(str(model),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False})
tokenizer.add_eos_token('<|im_end|>')
prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
start=time.time()
response=''.join(r.text for r in stream_generate(network,tokenizer,prompt=prompt,max_tokens=700,sampler=make_sampler(temp=0)))
out={'model':str(model),'adapter':str(adapter),'adapter_sha256':hashlib.sha256((adapter/'adapters.safetensors').read_bytes()).hexdigest(),'messages':messages,'response':response,'elapsed_seconds':time.time()-start,'airflow_claim':None}
args.output.write_text(json.dumps(out,indent=2)+'\n')
print(response)
