import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
import static_mrf_witness as witness
from prepare_case import sha
parent=Path('work/bionic-airflow-20261012/baseline-interface-015')
case=Path('work/bionic-airflow-20261012/static-mrf-witness-018/full-domain-frame')
manifest=witness.prepare(parent,case,10471.975511966)
p=case/'system/topoSetDict';text=p.read_text();assert text.count('radius .02;')==1
p.write_text(text.replace('radius .02;','radius .2;'))
manifest['file_sha256']['system/topoSetDict']=sha(p)
manifest['full_domain_control']={'source_sha256':sha(Path(__file__)),'radius_m':.2,'cube_xy_corner_radius_m':2**.5*.04,'interface_inside_fluid':False,'change':'All cells in the same rotating coordinate frame; same stationary physical walls.'}
assert .2>2**.5*.04
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(witness.run(case,manifest)),flush=True)
