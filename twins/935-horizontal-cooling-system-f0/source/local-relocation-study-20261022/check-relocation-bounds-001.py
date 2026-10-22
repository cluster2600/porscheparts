"""Check the relocation proposal with the unchanged complete native certificate."""
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

phase=Path('/home/lolman/935-local-relocation-20261022')
candidate=phase/'candidate-001/candidate.off'
original=Path('/home/lolman/935-native-gpu-20261022/geometry-certification/original.off')
reference=Path('/home/lolman/935-analysis-patches-20261022/surface-001/candidate-quantized.off')
checker=original.parent/'tiled-envelope-linux'
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
inputs={str(p):sha(p) for p in [candidate,original,reference,checker]}
assert list(inputs.values())==['d5cbbf4cd7e58509f29c8ad176944d4cfdd09c80f2f9ccca65a28b7bbd75d56c','e374fc2f850645efb6db4854a4355f541a9617833b827a6cff52d24929757587','addba09e1ee2d7814f19a3262ac0910f0bc5b9d58dd43ada3254444845392e5a','a64afa7238ab1b28064412142701473a94ba869089d20cfedfcbe3994ff56430']
out=phase/'bounds-001';out.mkdir(mode=0o700)
record={'source_sha256':sha(__file__),'inputs_sha256':inputs,'steps':[],'complete_surface_bound_established':False,'CFD_accepted':False,'manufacturing_authorized':False}

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))

for name,args,seconds in [('controls',['--self-test'],30),('original',[original,candidate],900),('reference',[reference,candidate],900)]:
    started=time.monotonic()
    with (out/(name+'.stdout')).open('x') as stdout,(out/(name+'.stderr')).open('x') as stderr:
        result=subprocess.run(['timeout','--signal=TERM','--kill-after=10s',str(seconds)+'s',str(checker),*map(str,args)],stdout=stdout,stderr=stderr,preexec_fn=limits,timeout=seconds+20)
    step={'name':name,'exit':result.returncode,'elapsed_s':time.monotonic()-started,'memory_limit_GiB':4,'timeout_s':seconds}
    if result.returncode==0 and name!='controls':
        proof=json.loads((out/(name+'.stdout')).read_text());assert proof['complete_containment_pass'] and proof['topology_and_self_intersection_checks_pass'] and proof['envelope_bound_native_units']==.0225 and proof['reserved_numeric_margin_native_units']==.0025;step['certificate']=proof
    record['steps'].append(step)
    assert all(sha(Path(p))==expected for p,expected in inputs.items())
    (out/'assessment.json').write_text(json.dumps(record,indent=2)+'\n')
    if result.returncode!=0:raise SystemExit(1)
record['complete_surface_bound_established']=True
(out/'assessment.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
