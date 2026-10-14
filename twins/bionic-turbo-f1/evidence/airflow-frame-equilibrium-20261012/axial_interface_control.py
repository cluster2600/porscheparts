import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
import static_mrf_witness as witness
from prepare_case import sha
parent=Path('work/bionic-airflow-20261012/baseline-interface-015')
case=Path('work/bionic-airflow-20261012/static-mrf-witness-019/axial-interface')
manifest=witness.prepare(parent,case,10471.975511966)
p=case/'system/topoSetDict';text=p.read_text()
old='source cylinderToCell; p1 (0 0 -.05); p2 (0 0 .05); radius .02;'
assert text.count(old)==1
p.write_text(text.replace(old,'source boxToCell; box (-1 -1 -.02) (1 1 .02);'))
manifest['file_sha256']['system/topoSetDict']=sha(p)
manifest['axial_interface_control']={'source_sha256':sha(Path(__file__)),'planes_z_m':[-.02,.02],'expected_rotating_cell_count':4000,'interface_inside_fluid':True,'change':'Same two frames, but rotation is exactly tangential to both planar internal interfaces.'}
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(witness.run(case,manifest)),flush=True)
assert 'cellZoneSet rotorZone now size 4000' in (case/'log.topoSet').read_text()
