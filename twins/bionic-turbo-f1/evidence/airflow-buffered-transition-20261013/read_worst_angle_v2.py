"""Record the worst internal centre separation without proposing changed dimensions."""
import ast,csv,json,math,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();helper=Path('twins/bionic-turbo-f1/evidence/airflow-conformal-local-design-20261013/verify_pyramids.py');assert sha(helper)=='673f80a53bd03dba18820fa060c51e4cea75c660a6e546a8cda6c1e394be6c2a'
astmod=ast.parse(helper.read_text());exec(compile(ast.Module(body=[x for x in astmod.body if isinstance(x,ast.FunctionDef) and x.name in ('polygon','metrics')],type_ignores=[]),str(helper),'exec'))
s=json.loads((w/'construction.json').read_text());assert sha(w/'construction.json')==json.loads((w/'independent-readback.json').read_text())['construction_sha256'];p=np.array(s['vertices']);rows=list(csv.DictReader((w/'angles.csv').open()));worst=max(rows,key=lambda r:float(r['angle_deg']));a,b=int(worst['owner']),int(worst['neighbour'])
def faces(c):
 block=s['blocks'][c];n=4 if s['stages'][c]=='buffer' else 3;lo=block[:n];hi=block[4:4+n]
 return [lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)]
fa,fb=faces(a),faces(b);common=[f for f in fa if any(set(f)==set(g) for g in fb)];assert len(common)==1
ca,_,_=metrics([[p[i] for i in f] for f in fa]);cb,_,_=metrics([[p[i] for i in f] for f in fb]);cf,sf=polygon([p[i] for i in common[0]]);n=sf/np.linalg.norm(sf);delta=cb-ca;normal=float(delta@n);tangent=float(np.linalg.norm(delta-normal*n));angle=math.degrees(math.atan2(tangent,normal));assert abs(angle-float(worst['angle_deg']))<1e-9
out={'source_sha256':sha(Path(__file__)),'construction_sha256':sha(w/'construction.json'),'angles_sha256':sha(w/'angles.csv'),'severe_counts_by_interval_pair':dict(Counter(str((int(r['owner'])//2048,int(r['neighbour'])//2048)) for r in rows if float(r['angle_deg'])>70)),'worst':{'owner':a,'neighbour':b,'face_vertices':common[0],'owner_centre_m':ca.tolist(),'neighbour_centre_m':cb.tolist(),'face_centre_m':cf.tolist(),'unit_normal':n.tolist(),'normal_separation_m':normal,'tangential_separation_m':tangent,'angle_deg':angle},'constraint':'For each actual internal face, normal separation must be positive and tangential separation <= tan(70 deg) * normal separation. This is a quality relation, not an inferred physical dimension or a parameter sweep.','native_executed':False}
(w/'worst-angle.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
