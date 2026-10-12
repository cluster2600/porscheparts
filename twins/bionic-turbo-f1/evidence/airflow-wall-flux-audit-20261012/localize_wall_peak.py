"""Locate final velocity maxima and adjacent angular cuts without modifying a case."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
results=[]
for name in ('directed-equilibrium-044','wall-flux-pressure-051'):
    case=Path('work/bionic-airflow-20261012')/name;mesh=case/'constant/polyMesh'
    receipt=json.loads((case/'report.json').read_text())
    assert receipt['native_exit_code']==0 and receipt['native_end']
    assert all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
    text=(case/'2e-05/U').read_text()
    m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    u=np.fromstring(m[2].translate(str.maketrans('()','  ')),sep=' ').reshape(-1,3)
    assert len(u)==int(m[1]) and np.isfinite(u).all()
    owner=ascii_list((mesh/'owner').read_text()).astype(int)
    neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
    points=ascii_list((mesh/'points').read_text(),True)
    faces=list(ascii_faces((mesh/'faces').read_text()));assert len(faces)==len(owner)
    cell=int(np.argmax(np.linalg.norm(u,axis=1)));boundary=[]
    for i in np.flatnonzero(owner[len(neighbour):]==cell)+len(neighbour):
        vertices=points[list(faces[i])]
        boundary.append(dict(face=int(i),vertices_mm=(vertices*1000).tolist(),
                             all_vertices_exactly_on_y_zero=bool((vertices[:,1]==0).all())))
    results.append(dict(case=name,receipt_sha256=sha(case/'report.json'),cell=cell,
                        final_velocity_m_s=u[cell].tolist(),boundary=boundary))
output=dict(source_sha256=sha(Path(__file__)),results=results,
            scope='Read-only localization, not a causal proof or a real turbo boundary.')
with Path(__file__).with_name('wall-peak-localization.json').open('x') as f:json.dump(output,f,indent=2)
print(json.dumps(output))
