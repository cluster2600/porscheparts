"""Independent arithmetic, refusal, partition and promotion boundary checks."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'training/qwen-picogk-qualified-20261014'


class QualifiedPicoGKTests(unittest.TestCase):
    def check(self, code):
        result = subprocess.run([sys.executable, '-c', 'import sys;sys.path.insert(0,sys.argv[1]);\n'+code, str(FOLDER)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_radial_roles_units_locale_and_reordering(self):
        self.check('''
import request_contract as c
request={'recipe':'pipe','language':'fr','interface_status':'synthetic','fields':{
 'inner':{'value':'0,4','unit':'cm','quantity':'diameter'},
 'length':{'value':'0.012','unit':'m','quantity':'length'},
 'outer':{'value':'0,85','unit':'cm','quantity':'radius'}}}
assert c.normalize(request)['parameters_mm']==[12.0,8.5,2.0]
request['fields']['outer']['quantity']='diameter'
assert c.normalize(request)['parameters_mm']==[12.0,4.25,2.0]
request['fields']=dict(reversed(list(request['fields'].items())))
assert c.normalize(request)['parameters_mm']==[12.0,4.25,2.0]
request['language']='en'
try:c.normalize(request)
except ValueError:pass
else:raise AssertionError('English decimal comma accepted')
''')

    def test_bcc_radius_becomes_diameter_and_invalid_inputs_fail(self):
        self.check('''
import copy,request_contract as c
r={'recipe':'bcc','language':'de','interface_status':'synthetic','fields':{
 'cell_side':{'value':12,'unit':'mm','quantity':'length'},'beam':{'value':'0,075','unit':'cm','quantity':'radius'}}}
assert c.normalize(r)['parameters_mm']==[12.0,1.5]
for key,value in [('value',True),('value','NaN'),('value','1 234'),('value','1e2'),('unit',['mm']),('quantity',[])]:
 bad=copy.deepcopy(r);bad['fields']['beam'][key]=value
 try:c.normalize(bad)
 except ValueError:pass
 else:raise AssertionError((key,value))
bad=copy.deepcopy(r);bad['recipe']=[]
try:c.normalize(bad)
except ValueError:pass
else:raise AssertionError('Non-string recipe accepted')
''')

    def test_model_cannot_supply_its_own_numeric_contract(self):
        self.check('''
import json,request_contract as c
r={'recipe':'cylinder','language':'en','interface_status':'synthetic','fields':{
 'length':{'value':10,'unit':'mm','quantity':'length'},'outer':{'value':8,'unit':'mm','quantity':'radius'}}}
for response,finish in [('{"recipe":"cylinder","parameters_mm":[10,4],"missing":[]}','stop'),(json.dumps(c.normalize(r)),'length')]:
 try:c.accepted(response,finish,r)
 except ValueError:pass
 else:raise AssertionError('Wrong intent or missing EOS accepted')
for status in ('missing','unverified'):
 r['interface_status']=status
 assert c.normalize(r)=={'recipe':'needs_measurement','parameters_mm':[],'missing':['measured_interfaces']}
''')

    def test_course_disjointness_and_true_unique_intents(self):
        self.check('''
import collections,qualify as q
data=q.rows(set())
assert collections.Counter(r['split'] for r in data)=={'train':720,'valid':60,'test':60}
sets={s:{(r['expected']['recipe'],tuple(r['expected']['parameters_mm'])) for r in data if r['split']==s and r['expected']['parameters_mm']} for s in ('train','valid','test')}
assert len(sets['train'])==300 and len(sets['valid'])==50 and len(sets['test'])==50
assert not sets['train'] & sets['valid'] and not sets['train'] & sets['test'] and not sets['valid'] & sets['test']
assert len({r['id'] for r in data})==len(data)
assert all(q.pilot.matches(q.contract.normalize(r['request']),r['expected']) for r in data)
''')

    def test_milestone_cannot_hide_language_refusal_or_regression(self):
        self.check('''
import qualify as q
rows=[r for r in q.rows(set()) if r['split']=='valid']
scores=[dict(id=r['id'],passed=True) for r in rows]
assert q.summary(scores,scores,rows)['eligible']
failed=[dict(s) for s in scores]
for i in range(5):failed[i]['passed']=False
assert not q.summary(scores,failed,rows)['eligible']
before=[dict(s,passed=False) for s in scores]
assert not q.summary(before,failed,rows)['eligible'] # One language falls below eight.
ref=next(i for i,r in enumerate(rows) if r['expected']['recipe']=='needs_measurement')
failed=[dict(s) for s in scores];failed[ref]['passed']=False
assert not q.summary(before,failed,rows)['eligible']
''')

    def test_second_trial_excludes_consumed_final_intents_and_mixes_field_syntax(self):
        self.check('''
import qualify as q
old=q.rows(set());excluded={(r['expected']['recipe'],tuple(r['expected']['parameters_mm'])) for r in old if r['expected']['parameters_mm']}
new=q.rows(excluded,broader=True)
assert not excluded & {(r['expected']['recipe'],tuple(r['expected']['parameters_mm'])) for r in new if r['expected']['parameters_mm']}
for split in ('train','valid','test'):
 prompts=[r['messages'][1]['content'] for r in new if r['split']==split and r['expected']['recipe']!='needs_measurement']
 assert any('(' in s for s in prompts) and any(' = ' in s for s in prompts) and any(': ' in s for s in prompts)
assert all('Field order is irrelevant' in r['messages'][0]['content'] for r in new)
''')

    def test_library_selector_rejects_extra_fields_and_incomplete_answers(self):
        self.check('''
import library_stage as s
assert s.parse_action('{"operation":"scalar_vdb"}','stop')=='scalar_vdb'
for text,finish in [('{"operation":"scalar_vdb","solver":true}','stop'),('{"operation":"unknown"}','stop'),('{"operation":"scalar_vdb"}','length'),('{"operation":true}','stop')]:
 try:s.parse_action(text,finish)
 except ValueError:pass
 else:raise AssertionError('Unsupported library action accepted')
''')

    def test_profile_requires_trusted_hash_before_reading_or_loading(self):
        self.check('''
import importlib.util,pathlib,tempfile
spec=importlib.util.spec_from_file_location('qualified_ask',pathlib.Path(__import__('sys').argv[1])/'ask.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as folder:
 p=pathlib.Path(folder)/'profile.json';p.write_text('{}')
 try:m.profile(p,'0'*64)
 except ValueError:pass
 else:raise AssertionError('Untrusted profile accepted')
''')

    def test_profile_does_not_trust_eligible_flag_or_assisted_score(self):
        self.check('''
import importlib.util,pathlib,tempfile,json,sys
spec=importlib.util.spec_from_file_location('qualified_ask',pathlib.Path(sys.argv[1])/'ask.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as folder:
 root=pathlib.Path(folder);(root/'run-001').mkdir()
 frozen=root/'FROZEN.json';frozen.write_text('{}')
 scores={'total':60,'passed':49,'refusal_passes':10,'regressions':[], 'by_language':dict.fromkeys(m.contract.LANGUAGES,10)}
 result={'schema':'qwen.picogk.qualification-results@1','eligible':True,'test_opened':True,'frozen_inputs_verified':True,
  'old_plans_passed':48,'old_code_passed':16,'historical_regressions':[], 'development':scores,'final':scores,
  'assisted':{'passed':60}}
 rp=root/'run-001/results.json';rp.write_text(json.dumps(result))
 config={'schema':'qwen.picogk.qualified-profile@1','work_root':str(root),'results_sha256':m.pilot.digest(rp),'frozen_sha256':m.pilot.digest(frozen)}
 p=root/'profile.json';p.write_text(json.dumps(config))
 try:m.profile(p,m.pilot.digest(p))
 except ValueError:pass
 else:raise AssertionError('49 raw passes promoted using eligible or assisted fields')
''')

    def test_sdk_placeholder_relocation_still_requires_registered_bytes(self):
        self.check('''
import pathlib,tempfile,types,qualify as q
from unittest.mock import patch
with tempfile.TemporaryDirectory() as folder:
 root=pathlib.Path(folder);prior=root/'prior';sdk=prior/'runtime/dotnet';sdk.mkdir(parents=True)
 original=sdk/'resource.dll';original.write_bytes(b'registered')
 local=root/'local/dotnet';local.mkdir(parents=True);alternate=local/'resource.dll';alternate.write_bytes(b'registered')
 q.pilot.save(prior/'FROZEN.json',{'files':{str(original):q.pilot.digest(original)}})
 q.PRIOR=prior;q.RUNTIME=root;q.pilot.PICO=root/'local'
 real=pathlib.Path.stat
 def metadata(path,*args,**kw):
  if path==original:return types.SimpleNamespace(st_flags=0x40000000)
  return real(path,*args,**kw)
 with patch.object(pathlib.Path,'stat',metadata):
  assert q.verify_prior()['relocated_dataless_sdk_files']=={str(original):str(alternate)}
  alternate.write_bytes(b'changed')
  try:q.verify_prior()
  except ValueError:pass
  else:raise AssertionError('SDK relocation ignored the historical hash')
''')

    def test_continuation_is_pinned_to_its_published_rejected_trial(self):
        self.check('''
import json,pathlib,tempfile,qualify as q
with tempfile.TemporaryDirectory() as folder:
 root=pathlib.Path(folder);trial=root/'trial';(trial/'run-001').mkdir(parents=True);published=root/'published';published.mkdir()
 result={'test_opened':True,'eligible':False,'frozen_inputs_verified':True,'adapter_sha256':'a'*64,'final':{'passed':27},'receipt_sha256':{}}
 path=trial/'run-001/results.json';path.write_text(json.dumps(result))
 q.pilot.save(published/'results-001.json',{'status':'completed_rejected_final','adapter_sha256':'a'*64,'final':{'passed':27},'private_receipt_sha256':{'results.json':q.pilot.digest(path)}})
 try:q.published_trial(trial)
 except ValueError:pass
 else:raise AssertionError('Unpublished continuation accepted')
 q.HERE=published
 assert q.published_trial(trial)==(result,q.pilot.digest(path))
 path.write_text(json.dumps(dict(result,adapter_sha256='b'*64,receipt_sha256={'trained-adapter/adapter_config.json':'c'*64})))
 try:q.published_trial(trial)
 except ValueError:pass
 else:raise AssertionError('Altered continuation result trusted')
''')
