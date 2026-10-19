"""Only three unchanged finite binary witnesses and their existing gates."""
from fractions import Fraction
import hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
import witnesses

root=Path(sys.argv[1]);out=root/'smoke';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
cases=[('union-prisms','union',witnesses.prism(10),witnesses.prism(20),Fraction(4000)),
       ('intersection-prisms','intersection',witnesses.prism(10),witnesses.prism(20),Fraction(2000)),
       ('difference-prism-gap','difference',witnesses.prism(20),witnesses.box([-1,-1,8],[21,21,12]),Fraction(3200))]
rows=[];error=None;began=time.monotonic()
try:
    for name,mode,a,b,volume in cases:
        job=out/name;job.mkdir();inputs=[]
        for role,(v,f)in [('A',a),('B',b)]:
            path=job/(role+'.npz');np.savez_compressed(path,vertices=v,faces=f,source_face=np.arange(len(f),dtype=np.int64));inputs.append(path)
        command=[sys.executable,'-B',str(root/'worker.py'),mode,str(inputs[0]),str(job),
                 str(root/'build/carrier_soup_boolean'),'--second-input',str(inputs[1])]
        with (job/'worker.stdout.log').open('x')as stdout,(job/'worker.stderr.log').open('x')as stderr:
            result=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=18)
        audit=json.loads((job/'audit.json').read_text());native=audit.get('native',{})
        passed=(result.returncode==0 and audit.get('native_returncode')==0
            and audit.get('native_exact_gate_pass')is True and audit.get('rounded_exact_contact_gate_pass')is True
            and audit.get('local_geometry_gates_pass')is True and audit.get('output_topology',{}).get('pass')is True
            and native.get('source_face_lineage_complete')is True
            and Fraction(native['exact_signed_volume_mm3'])==volume)
        row=dict(name=name,mode=mode,actual_worker_returncode=result.returncode,
            actual_native_returncode=audit.get('native_returncode'),expected_exact_volume_mm3=str(volume),
            actual_exact_volume_mm3=native.get('exact_signed_volume_mm3'),passed=passed,
            audit_sha256=sha(job/'audit.json'),native_sha256=sha(job/'native.json'),
            result_sha256=sha(job/'result.npz'),exact_result_sha256=sha(job/'result.mesh64.exact'),
            output_topology=audit.get('output_topology'),native_exact_gate_pass=audit.get('native_exact_gate_pass'),
            rounded_exact_contact_gate_pass=audit.get('rounded_exact_contact_gate_pass'),
            source_face_lineage_complete=native.get('source_face_lineage_complete'))
        rows.append(row)
        if not passed:raise ValueError('Existing witness refused: '+name)
except BaseException as e:error=dict(type=type(e).__name__,message=str(e))
report=dict(status='three_existing_binary_witnesses_passed'if error is None and len(rows)==3 else'finite_witnesses_refused_or_incomplete',
    CGAL_commit='b4e8c1887ce6a0abeb618634125e5cfcd301ce16',experimental=True,cases=rows,error=error,
    seconds=time.monotonic()-began,worker_source_sha256=sha(root/'worker.py'),witness_source_sha256=sha(root/'witnesses.py'),
    binary_sha256=sha(root/'build/carrier_soup_boolean'),global_admission=False,
    scope='Only restored experimental archive and three finite binary software witnesses. No self_union or carrier computation.')
(out/'smoke-receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(status=report['status'],cases=len(rows),seconds=report['seconds'])) ,flush=True)
raise SystemExit(0 if report['status']=='three_existing_binary_witnesses_passed'else 1)
