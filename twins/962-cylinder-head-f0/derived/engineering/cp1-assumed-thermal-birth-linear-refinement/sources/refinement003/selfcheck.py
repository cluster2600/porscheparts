"""Prepared stdlib synthetic binding/gate guards; no native/0548 or field replay."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import tempfile
from unittest import TestCase,main,mock

SOURCE=Path(__file__).with_name('assess_refinement.py')
SOURCE_SHA256='13934e6e8ae5bb1ada1b6bbc29172855441e72b04e34752d4132c530bc69138c'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
spec=importlib.util.spec_from_file_location('fixed_linear_refinement',SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # stdlib-only prepared module; no main/assessor/native import
PREP=SOURCE.parent

class Guards(TestCase):
 def fixture(self,errors=(.016,.008,.004)):
  tmp=tempfile.TemporaryDirectory(dir=module.ROOT/'work/962-engineering');self.addCleanup(tmp.cleanup)
  root=Path(tmp.name).resolve();manifest=json.loads((PREP/'refinement-manifest.json').read_text())
  for record in list(module.SHARED.values())+[r[k] for r in module.REFERENCES for k in ('numerical_reference','time_input')]:
   target=root/record['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(module.ROOT/record['path'],target)
  manifest.update(status='BOUND_THREE_ACCEPTED_LEVELS',ready_for_evaluation=True)
  self.fixture_root=root;self.manifest=manifest;self.reports=[];self.receipts=[];self.peers=[];self.accepted=[]
  self.manifest_path=root/'manifest.json'
  for i,error in enumerate(errors):
   dt=[.01,.005,.0025][i];count=[40,80,160][i]
   self.reports.append(dict(passed=True,classification='HYPOTHETICAL_SOFTWARE_VERIFICATION_ONLY',level=i,dt_s=dt,
    native_steps=count,checks_count=count,failed_checks=[],max_error_by_check={},max_continuous_relative_energy_error=error,
    traces=[dict(step=j,time_s=j*dt,relative_continuous_energy_error=error) for j in range(1,count+1)],
    frozen_contract_sha256=module.REFERENCES[i]['numerical_reference']['sha256'],assessor_sha256=module.SHARED['assessor']['sha256']))
   self.receipts.append(dict(level=i,physics_contract_sha256=module.REFERENCES[i]['numerical_reference']['sha256'],returncode=0,
    native_execution_completed=True,inputs_unchanged=True,binary_and_runtime_unchanged=True))
   self.peers.append(dict(decision='CLEAR_SYNTHETIC_BINDING_ONLY',blockers=[]))
   self.accepted.append(dict(passed_single_level_software_assessment=True))
  self.flush()
 def flush(self):
  for i,row in enumerate(self.manifest['levels']):
   directory=self.fixture_root/f'level{i}';directory.mkdir(exist_ok=True)
   def write(key,obj):
    path=directory/(key+'.json');path.write_text(json.dumps(obj)+'\n')
    row[key]=dict(path=str(path.relative_to(self.fixture_root)),sha256=module.sha(path))
   write('native_receipt',self.receipts[i]);self.reports[i]['native_receipt_sha256']=row['native_receipt']['sha256']
   write('assessment',self.reports[i]);write('assessment_result_peer',self.peers[i])
   self.accepted[i].update(assessment_sha256=row['assessment']['sha256'],peer_sha256=row['assessment_result_peer']['sha256'])
   write('root_assessment_acceptance',self.accepted[i])
  self.fixed2={key:copy.deepcopy(self.manifest['levels'][2][key]) for key in module.RESULT_KEYS}
  self.save_manifest()
 def save_manifest(self):self.manifest_path.write_text(json.dumps(self.manifest)+'\n')
 def call(self,paths=None,permit_synthetic_level2=True):
  paths=paths or [self.fixture_root/r['assessment']['path'] for r in self.manifest['levels']]
  # Synthetic numerical-boundary tests replace only the immutable result-record
  # constant; fixed shared physics and all real numerical references remain exact.
  pinned=self.fixed2 if permit_synthetic_level2 else module.IMMUTABLE_LEVEL2
  with mock.patch.object(module,'ROOT',self.fixture_root),mock.patch.object(module,'IMMUTABLE_LEVEL2',pinned):
   return module.assess(self.manifest_path,paths)
 def test_held_manifest_exact_fixed_inputs_NULL_futures_and_immutable_level2(self):
  m=json.loads((PREP/'refinement-manifest.json').read_text())
  self.assertFalse(m['ready_for_evaluation'])
  for i in [0,1]:self.assertTrue(all(m['levels'][i][k] is None for k in module.RESULT_KEYS))
  self.assertEqual({k:m['levels'][2][k] for k in module.RESULT_KEYS},module.IMMUTABLE_LEVEL2)
  self.assertEqual(m['levels'][2]['assessment']['sha256'],'198ae20f6baa27a726b17f3924659b8c1e0613e9a5b1e161ad8f6ef3b5107dbf')
  self.assertEqual(m['shared'],module.SHARED)
  for r in module.REFERENCES:
   for key in ['numerical_reference','time_input']:
    self.assertEqual(module.sha(module.ROOT/r[key]['path']),r[key]['sha256'])
  with self.assertRaises(ValueError):module.assess(PREP/'refinement-manifest.json',[])
  self.fixture()
  with self.assertRaises(ValueError):self.call(permit_synthetic_level2=False)
 def test_complete_valid_binding_and_distinct_manifest_reference_output(self):
  self.fixture();r=self.call()
  self.assertTrue(r['passed']);self.assertEqual(r['successive_error_ratios'],[2.,2.])
  self.assertEqual(r['predeclared_minimum_error_ratio'],1.4);self.assertEqual(r['predeclared_finest_energy_limit'],.01)
  self.assertEqual(r['refinement_manifest_sha256'],module.sha(self.manifest_path))
  self.assertEqual(r['numerical_reference_sha256s'],[x['numerical_reference']['sha256'] for x in module.REFERENCES])
  self.assertNotIn('frozen_contract_sha256',r)
  self.assertFalse(r['engineering_accepted'] or r['physics_qualified'] or r['manufacturing_authorized'])
 def test_missing_order_dt_contract_assessor_failed_and_receipt_refusals(self):
  for key,value in [('passed',False),('level',1),('dt_s',.02),('frozen_contract_sha256','0'*64),
                    ('assessor_sha256','0'*64),('failed_checks',[{'synthetic':True}])]:
   with self.subTest(field=key):
    self.fixture();self.reports[0][key]=value;self.flush()
    with self.assertRaises(ValueError):self.call()
  self.fixture();paths=[self.fixture_root/r['assessment']['path'] for r in self.manifest['levels']]
  with self.assertRaises(ValueError):self.call(list(reversed(paths)))
  self.fixture();self.manifest['levels'][0]['assessment']=None;self.save_manifest()
  with self.assertRaises(ValueError):self.call(paths=[self.fixture_root/'unselected.json']*3)
  for obj,key,value in [('receipt','level',1),('receipt','returncode',1),('receipt','native_execution_completed',False),
                        ('peer','blockers',['x']),('accept','passed_single_level_software_assessment',False)]:
   with self.subTest(object=obj,key=key):
    self.fixture();target={'receipt':self.receipts,'peer':self.peers,'accept':self.accepted}[obj]
    target[0][key]=value;self.flush()
    with self.assertRaises(ValueError):self.call()
 def test_wrong_reference_shared_identity_and_changed_body_refused(self):
  for key in ['card','deck','assessor']:
   self.fixture();self.manifest['shared'][key]['sha256']='0'*64;self.save_manifest()
   with self.assertRaises(ValueError):self.call()
  self.fixture();self.manifest['levels'][0]['numerical_reference']['sha256']='0'*64;self.save_manifest()
  with self.assertRaises(ValueError):self.call()
  self.fixture();self.manifest['levels'].reverse();self.save_manifest()
  with self.assertRaises(ValueError):self.call()
  self.fixture();(self.fixture_root/self.manifest['levels'][0]['assessment']['path']).write_text('{}\n')
  with self.assertRaises(ValueError):self.call()
 def test_finite_nonnegative_zero_denominator_and_complete_trace_refusals(self):
  for error in [float('nan'),float('inf'),-1.,True,'bad']:
   self.fixture((.016,error,.004))
   with self.assertRaises(ValueError):self.call()
  for errors in [(.016,0.,.004),(.016,.008,0.)]:
   self.fixture(errors)
   with self.assertRaises(ValueError):self.call()
  self.fixture();self.reports[0]['traces'].pop();self.flush()
  with self.assertRaises(ValueError):self.call()
  self.fixture();self.reports[0]['max_continuous_relative_energy_error']=.001;self.flush()
  with self.assertRaises(ValueError):self.call()
 def test_original_ratio_and_finest_boundaries_without_softening(self):
  self.fixture((.007,.005,.0025));self.assertTrue(self.call()['passed'])
  # One downward ULP still divides to1.4; two ULPs make this a strict-below fixture.
  below=math.nextafter(math.nextafter(.007,-math.inf),-math.inf)
  self.assertLess(below/.005,1.4)
  self.fixture((below,.005,.0025));self.assertFalse(self.call()['passed'])
  self.fixture((.04,.02,.01));self.assertTrue(self.call()['passed'])
  self.fixture((.04,.02,math.nextafter(.01,math.inf)));self.assertFalse(self.call()['passed'])
  self.fixture((0.,.008,.004));self.assertFalse(self.call()['passed'])

 def test_valid_mixed_signed_trace_uses_maximum_absolute_error(self):
  self.fixture()
  for report in self.reports:
   for index,trace in enumerate(report['traces']):
    if index%3==0:trace['relative_continuous_energy_error']*=-1
  self.flush();result=self.call()
  self.assertTrue(result['passed'])
  self.assertEqual(result['max_continuous_relative_energy_errors'],[.016,.008,.004])
  self.assertTrue(all(any(t['relative_continuous_energy_error']<0 for t in r['traces']) for r in self.reports))
  self.assertTrue(all(any(t['relative_continuous_energy_error']>0 for t in r['traces']) for r in self.reports))

if __name__=='__main__':main()
