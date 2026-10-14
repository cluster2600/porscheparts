import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
case=Path('work/bionic-airflow-20261012/baseline-profile-mesh-031')
receipt=json.loads((case/'write-centres-receipt.json').read_text());assert receipt['native_exit_code']==0
arrays={}
for name in ('C','Cx','Cy','Cz'):
 p=case/'0'/name;assert sha(p)==receipt['outputs']['0/'+name]
 m=re.search(r'internalField\s+nonuniform\s+List<(vector|scalar)>\s+(\d+)\s*\((.*?)\)\s*;',p.read_text(),re.S);assert m
 components=3 if name=='C' else 1
 values=np.fromstring(m[3].translate(str.maketrans('()','  ')),sep=' ')
 assert int(m[2])==718456 and len(values)==718456*components and np.isfinite(values).all()
 arrays[name]=values.reshape(718456,components)
for i,name in enumerate(('Cx','Cy','Cz')):assert np.array_equal(arrays[name][:,0],arrays['C'][:,i])
print(json.dumps({'source_sha256':sha(Path(__file__)),'cells':718456,'all_four_native_fields_finite':True,'components_exactly_match_vector_field':True,'fields_sha256':receipt['outputs'],'geometry_only':True,'flow_solver_launched':False},indent=2))
