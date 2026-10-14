"""Read back the final native fields of the completed aligned-interface witness."""
import json
from pathlib import Path
import re
import sys
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha

def internal(text,components):
    match=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    if match:
        assert match[1]==('vector' if components==3 else 'scalar')
        result=np.fromstring(match[3].translate(str.maketrans('()','  ')),sep=' ')
        assert int(match[2])==9600 and result.size==9600*components
        result=result.reshape(9600,components)
    else:
        match=re.search(r'internalField\s+uniform\s+([^;]+);',text)
        assert match
        value=np.fromstring(match[1].translate(str.maketrans('()','  ')),sep=' ')
        assert value.size==components
        result=np.tile(value,(9600,1))
    assert np.isfinite(result).all()
    return result

assert internal('internalField uniform (0 0 0);',3).shape==(9600,3)
try:
    internal('internalField nonuniform List<scalar> 9600 (1 2);',1)
except AssertionError:
    pass
else:
    raise AssertionError('Incomplete field accepted')
case=Path('work/bionic-airflow-20261012/static-mrf-witness-021/aligned-radial-interface')
report=json.loads((case/'report.json').read_text());assert report['native_exit_code']==0
result={'case':str(case),'checkpoint':'2e-05','source_sha256':sha(Path(__file__)),'report_sha256':sha(case/'report.json'),'performance_ranking_authorized':False,'fields':{}}
for name,components in (('p',1),('T',1),('U',3)):
    p=case/'2e-05'/name
    assert sha(p)==report['output_sha256']['2e-05/'+name]
    values=internal(p.read_text(),components)
    magnitudes=np.linalg.norm(values,axis=1) if components==3 else values[:,0]
    result['fields'][name]={'cells':len(values),'sha256':sha(p),'min':float(magnitudes.min()),'max':float(magnitudes.max())}
assert max(abs(result['fields']['p'][key]-101325) for key in ('min','max'))<=.001
assert max(abs(result['fields']['T'][key]-298.15) for key in ('min','max'))<=1e-6
assert result['fields']['U']['max']<=1e-8
print(json.dumps(result,indent=2))
