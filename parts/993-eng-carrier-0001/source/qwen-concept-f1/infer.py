import hashlib, importlib.metadata, json, os, sys, time
from pathlib import Path
if len(sys.argv) != 3:
    raise SystemExit('Usage: infer.py <training-checkout> <new-output-json>')
training = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2])
if output.exists():
    raise SystemExit('Refusing to overwrite an inference receipt')
sys.path.insert(0, str(training / 'training/m64-qwen'))
from picogk import SYSTEM, parse, signature
from run import configure_tokenizer
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler
import mlx.core as mx
model = training / 'work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
adapter = training / 'work/m64-qwen/coding-003/checkpoint-600'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(model/'model.safetensors') == 'daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58'
assert digest(adapter/'adapters.safetensors') == 'a1014c6f71b46d879c09462c4a57d17d00df8f11b8178dd53bf6d5f2ac2f778a'
assert importlib.metadata.version('mlx-lm') == '0.31.3'
mx.random.seed(42)
network, tokenizer = load(str(model), adapter_path=str(adapter), tokenizer_config={'trust_remote_code':False})
configure_tokenizer(tokenizer)
records=[]
for side in (-1,1):
    vertices={'A':[side*28,0,0],'B':[side*20,0,1.9],'C':[0,0,0.9],'D':[0,0,-1.9]}
    edges=[('A','B'),('B','C'),('C','D'),('D','A')]
    prompt=('Build a synthetic frame. Vertices in mm: '+json.dumps(vertices)+'. Directed edges: A->B, B->C, C->D, D->A. Each edge has start radius 0.6 mm and end radius 0.6 mm. Rounded caps: true. There are four edges; emit all four exactly once. Use 0.6f for every radius argument.')
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}]
    rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    started=time.perf_counter()
    response=''
    last=None
    for last in stream_generate(network,tokenizer,prompt=rendered,max_tokens=512,sampler=make_sampler(temp=0)):
        response+=last.text
    row={'side':side,'messages':messages,'response':response,'seconds':time.perf_counter()-started,
         'vertices':vertices,'edges':edges,'radius_model_mm':0.6,'rounded_caps':True,
         'generation_tokens':last.generation_tokens,'generation_tps':last.generation_tps,'peak_memory_gb':last.peak_memory}
    try:
        clean, beams = parse(response)
        expected=[vertices[a]+[.6]+vertices[b]+[.6,True] for a,b in edges]
        row['semantic_passed']=signature(beams)==signature(expected)
        row['parsed_code']=clean
    except ValueError as exc:
        row['semantic_passed']=False
        row['error']=str(exc)
    records.append(row)
    print(json.dumps({'side':side,'semantic_passed':row['semantic_passed'],'response':response}),flush=True)
receipt={'model_repository':'mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit',
         'model_revision':model.name,'model_weights_sha256':digest(model/'model.safetensors'),
         'adapter_run':'coding-003/checkpoint-600','adapter_sha256':digest(adapter/'adapters.safetensors'),
         'adapter_config_sha256':digest(adapter/'adapter_config.json'),'mlx_lm_version':importlib.metadata.version('mlx-lm'),
         'decoding':{'temperature':0,'seed':42,'max_tokens':512},'records':records,
         'geometry_scale':10,'coordinate_authority':'human-designed hypotheses; model transcribes a graph, no OEM dimensions inferred',
         'part_number':'993 115 021 53','manufacturing_authorized':False}
output.write_text(json.dumps(receipt,indent=2)+'\n')
