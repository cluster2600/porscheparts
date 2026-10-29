"""Native fixed-vertex controls with explicit success and refusal cases."""
from pathlib import Path
import json
import math
import struct
import subprocess

import numpy as np

r=Path(__file__).resolve().parent
out=r/"controls-001"
out.mkdir()
work=r.parents[1]
v=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype="<u8")
with(out/"source.meshbin").open("wb")as stream:
    stream.write(struct.pack("<QQ",4,4));v.astype("<f8").tofile(stream);f.tofile(stream)
cases=[("vertex-sphere",0,[-.04]*3,[-.1/math.sqrt(3)]*3,0),
       ("wrong-source-vertex",1,[-.04]*3,[-.1/math.sqrt(3)]*3,2),
       ("wrong-radius",0,[-.04]*3,[-.1]*3,2),
       ("face-instead-of-vertex",0,[-.05,.2,.2],[-.1,.2,.2],2)]
rows=[]
for name,index,a,b,expected in cases:
    q=out/(name+".txt");q.write_text(str(index)+"\n"+" ".join(format(x,".17g")for x in a+b)+"\n")
    dest=out/(name+".json")
    cmd=["docker","run","--rm","--pull=never","--platform","linux/arm64","--network","none","--memory","2g","--entrypoint","/usr/bin/timeout","-v",str(work)+":/work","sha256:7ed241be10194d98e4ae750cb7f983b0d501742f1ac651580b86c165cba39537","60s","/work/qualified-dilation-001/projection-002/check_vertex_offset","/work/"+str((out/"source.meshbin").relative_to(work)),"/work/"+str(q.relative_to(work)),"/work/"+str(dest.relative_to(work))]
    run=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
    assert run.returncode==expected,(name,run.returncode,run.stderr)
    rows.append(dict(case=name,returncode=run.returncode,result=json.loads(dest.read_text())))
(out/"assessment.json").write_text(json.dumps(dict(status="exact_vertex_offset_controls_passed",cases=rows),indent=2)+"\n")
print(json.dumps([dict(case=row["case"],returncode=row["returncode"])for row in rows]))
