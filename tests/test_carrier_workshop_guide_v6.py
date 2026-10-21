"""Guide6 metadata/link fixtures; no AM replay, solver or real carrier guide."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_carrier_workshop_guide_v5 as public_v5
import build_part_workflow_guide as renderer
ORIGINAL_BUILD, ORIGINAL_PACKAGE = public_v5.build, public_v5.package
spec = importlib.util.spec_from_file_location('carrier_guide_v6_tests', ROOT/'scripts/build_carrier_workshop_guide_v6.py')
guide = importlib.util.module_from_spec(spec); spec.loader.exec_module(guide)

def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class WorkshopGuideV6(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.run = self.root/'work/run'; self.process = self.run/'process'
        self.process.mkdir(parents=True)
        self.root_patch = patch.object(guide, 'ROOT', self.root); self.root_patch.start(); self.addCleanup(self.root_patch.stop)
        self.result = dict(passed=True, fixture='explicit software receipt, no geometric calculation')
        self.execution = dict(schema='bounded-exact-unit-replays-1', status='completed', workers=4,
            maximum_pending_futures=8, worker_group_closed=True, worker_runtime_identity_verified_at_initialisation=True,
            runtime_before_sha256='a'*64, runtime_after_sha256='a'*64, source_indices=[0,1,2,3,8,9,10],
            policy_sha256={guide.CONSUMER.name:guide.CONSUMER_SHA256}, reviewed_proof_files_sha256={},
            units=[dict(source_index=0, unit='grid-0-0', result_sha256=identity(self.result))])
        self.description = self.run/'guide-description.json'
        self.data = dict(inputs=[dict(title='software fixture')],
            stages=[dict(id=n,checks=[],files=[],commands=[]) for n in ('reference','dimensions','mechanics','supports','layers','delivery')],
            constitutive_reference=dict(frames_verified=16, ENER_all_frames_pass=False, independent_Piola_all_frames_pass=True,STEP_equivalence_claimed=False),
            workshop_adapter=dict(source='scripts/build_carrier_workshop_guide_v5.py',sha256=guide.BASE_SHA256))
        self.data['stages'][2]['checks']=[dict(label='Grade 23 ELI'),dict(label='900 MPa'),dict(label='ENER REFUSÉ')]
        self.data['stages'][5]['commands']=['python3 scripts/run_part_workflow.py run '+guide.OLD_RECIPE+' --runtime work/runtime.json',
            'python3 scripts/run_part_workflow.py verify work/run']
        self.make_evidence(); self.save_description()

    def write(self, name, value):
        (self.process/name).write_text(json.dumps(value, allow_nan=False))

    def save_description(self):self.description.write_text(json.dumps(self.data))

    def make_evidence(self, proofs=False):
        files={}
        if proofs:
            for name in guide.PROOFS:
                self.write(name,dict(explicit_software_fixture=name));files[name]=guide.digest(self.process/name)
        self.execution['reviewed_proof_files_sha256']=files.copy();self.write(guide.REPLAY,self.execution)
        files[guide.REPLAY]=guide.digest(self.process/guide.REPLAY)
        self.binding=dict(receipt=guide.REPLAY,receipt_sha256=files[guide.REPLAY],files_sha256=files)
        self.stage=dict(manufacturing_preparation_admitted=True,input_sha256='b'*64,exact_unit_replays=self.binding,
            outputs_sha256=files,admission={},admission_runtime_hooks=dict(parallel_exact_unit_admissions=dict(source=guide.CONSUMER.name,sha256=guide.CONSUMER_SHA256)))
        for key in guide.KEYS:
            name='admission-'+key+'.json';receipt=dict(passed=True,status='passed',exact_unit_replays=self.binding)
            if key in ('skins','grids','contacts','collisions'):
                receipt['continuous_interval_exact_admissions']=[dict(region=0,unit='grid-0-0',receipt=self.result)]
            self.write(name,receipt);self.stage['admission'][key]=dict(status='passed',receipt=name,receipt_sha256=guide.digest(self.process/name))
        self.refresh()

    def refresh(self):
        for key,item in self.stage['admission'].items():item['receipt_sha256']=guide.digest(self.process/item['receipt'])
        self.write('support-stage.json',self.stage)
        self.report=dict(manufacturing_preparation_admitted=True,input_sha256=self.stage['input_sha256'],admission=copy.deepcopy(self.stage['admission']),
            outputs_sha256={**self.stage['outputs_sha256'],'support-stage.json':guide.digest(self.process/'support-stage.json')})
        self.write('report.json',self.report)

    def test_private_chain_retains_public_sources_and_constitutive_gates(self):
        self.assertIs(public_v5.build,ORIGINAL_BUILD);self.assertIs(public_v5.package,ORIGINAL_PACKAGE)
        self.assertIsNot(guide._base,public_v5);self.assertIs(guide._base.build,guide.render)
        self.assertEqual(guide._base._base.REFERENCE_FILES,public_v5._base.REFERENCE_FILES)
        self.assertEqual(guide._base._base.CASE_ID,public_v5._base.CASE_ID)
        self.assertEqual(guide.digest(guide.CONSUMER),guide.CONSUMER_SHA256)

    def test_bindings_cover_report_stage_replay_and_all_six_gates(self):
        before={p.name:guide.digest(p) for p in self.process.iterdir()}
        ref=guide.exact_replay_reference(self.run)
        self.assertEqual(ref['support_stage_sha256'],self.report['outputs_sha256']['support-stage.json'])
        self.assertEqual(ref['evidence_files_sha256'],self.binding['files_sha256'])
        self.assertEqual(len(ref['admission_receipts_sha256']),6)
        self.assertFalse(ref['exact_units_recomputed_in_PDF']);self.assertFalse(ref['PDF_runtime_compared_to_AM'])
        self.assertEqual(before,{p.name:guide.digest(p) for p in self.process.iterdir()})

    def test_render_changes_only_recipe_provenance_and_new_evidence_links(self):
        mechanics=copy.deepcopy(self.data['stages'][2]);constitutive=copy.deepcopy(self.data['constitutive_reference'])
        with patch.object(guide,'build',return_value={'software_fixture':True}) as build:
            result=guide.render(self.description,self.run/'guide')
        out=json.loads(self.description.read_text());self.assertEqual(out['stages'][2],mechanics)
        self.assertEqual(out['constitutive_reference'],constitutive);self.assertEqual(result,{'software_fixture':True})
        self.assertEqual(out['stages'][5]['commands'][1],self.data['stages'][5]['commands'][1])
        self.assertIn(guide.NEW_RECIPE,out['stages'][5]['commands'][0]);self.assertNotIn(guide.OLD_RECIPE,out['stages'][5]['commands'][0])
        self.assertEqual(out['stages'][5]['commands'][0].split().count(guide.NEW_RUNNER),1)
        self.assertNotIn(guide.OLD_RUNNER,out['stages'][5]['commands'][0])
        self.assertIn(guide.OLD_RUNNER,out['stages'][5]['commands'][1])
        self.assertEqual([Path(i['source']).name for i in out['stages'][3]['files']],['support-stage.json',guide.REPLAY])
        self.assertEqual(out['workshop_adapter']['retained_adapter'],self.data['workshop_adapter']);build.assert_called_once()

    def test_optional_proofs_are_linked_and_copied_with_exact_hashes(self):
        self.make_evidence(proofs=True)
        with patch.object(renderer,'ROOT',self.root),patch.object(renderer,'make_pdf',side_effect=lambda _,out:(out/'guide-atelier.pdf').write_bytes(b'%PDF-software-fixture')):
            result=guide.render(self.description,self.run/'guide')
        expected={str((self.process/n).relative_to(self.root)) for n in ['support-stage.json',guide.REPLAY,*guide.PROOFS]}
        self.assertEqual(set(result['sources']),expected)
        for name,row in result['sources'].items():
            self.assertEqual(guide.digest(self.run/'guide'/row['file']),guide.digest(self.root/name))

    def test_changed_evidence_or_symlink_is_rejected(self):
        original=(self.process/guide.REPLAY).read_bytes()
        (self.process/guide.REPLAY).write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError,'SHA differs'):guide.exact_replay_reference(self.run)
        (self.process/guide.REPLAY).unlink();outside=self.run/'outside.json';outside.write_bytes(original)
        (self.process/guide.REPLAY).symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'symlink'):guide.exact_replay_reference(self.run)

    def test_report_stage_and_one_rehashed_gate_cannot_have_other_bindings(self):
        self.report['outputs_sha256']['support-stage.json']='0'*64;self.write('report.json',self.report)
        with self.assertRaisesRegex(ValueError,'final process report'):guide.exact_replay_reference(self.run)
        self.refresh();p=self.process/'admission-skins.json';r=json.loads(p.read_text());r['exact_unit_replays']=dict(self.binding,receipt_sha256='0'*64);p.write_text(json.dumps(r));self.refresh()
        with self.assertRaisesRegex(ValueError,'six admissions'):guide.exact_replay_reference(self.run)

    def test_fully_rehashed_failed_execution_and_changed_runtime_are_rejected(self):
        for field,value in [('status','failed'),('worker_group_closed',False),('runtime_after_sha256','c'*64),('source_indices',[0,1,2])]:
            original=copy.deepcopy(self.execution);self.execution[field]=value;self.make_evidence()
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'execution is incomplete'):guide.exact_replay_reference(self.run)
            self.execution=original

    def test_result_tamper_and_negative_region_alias_are_rejected_after_rehash(self):
        for mode in ('result','negative-region'):
            self.make_evidence();p=self.process/'admission-contacts.json';r=json.loads(p.read_text())
            if mode=='result':r['continuous_interval_exact_admissions'][0]['receipt']['passed']=False
            else:r['continuous_interval_exact_admissions'][0]['region']=-1
            p.write_text(json.dumps(r));self.refresh()
            with self.subTest(mode=mode),self.assertRaises(ValueError):guide.exact_replay_reference(self.run)

    def test_unknown_duplicate_commands_and_layout_refuse_before_writing(self):
        for mode in ('missing','duplicate','layout','runner-missing','runner-duplicate'):
            data=copy.deepcopy(self.data)
            if mode=='missing':data['stages'][5]['commands'][0]='unexpected'
            elif mode=='duplicate':data['stages'][5]['commands'][0]+=' '+guide.OLD_RECIPE
            elif mode=='layout':data['stages'][3]['id']='unexpected'
            elif mode=='runner-missing':data['stages'][5]['commands'][0]=data['stages'][5]['commands'][0].replace(guide.OLD_RUNNER,'scripts/unknown.py')
            else:data['stages'][5]['commands'][0]+=' '+guide.OLD_RUNNER
            self.description.write_text(json.dumps(data));before=self.description.read_bytes()
            with patch.object(guide,'build') as build,self.assertRaises(ValueError):guide.render(self.description,self.run/'guide')
            build.assert_not_called();self.assertEqual(self.description.read_bytes(),before)

    def test_source_pins_and_historical_refusal_propagate_before_delegation(self):
        for field in ('BASE_SHA256','SOURCE_SHA256','CONSUMER_SHA256'):
            with self.subTest(field=field),patch.object(guide,field,'0'*64),patch.object(guide._base,'package') as base:
                with self.assertRaisesRegex(ValueError,'source changed'):guide.package(self.run)
                base.assert_not_called()
        with patch.object(guide._base,'package',side_effect=ValueError('Retained Piola/ENER verdicts differ')):
            with self.assertRaisesRegex(ValueError,'Piola/ENER'):guide.package(self.run)

    def test_evidence_change_after_render_or_package_is_refused(self):
        def alter(*_):
            with (self.process/guide.REPLAY).open('a') as stream:stream.write(' ')
            return {}
        with patch.object(guide,'build',side_effect=alter),self.assertRaises(ValueError):guide.render(self.description,self.run/'guide')
        self.make_evidence()
        with patch.object(guide._base,'package',side_effect=alter),self.assertRaises(ValueError):guide.package(self.run)

    def test_import_does_not_require_or_load_am_packages(self):
        code="""import builtins,sys
sys.path.insert(0,sys.argv[1])
original=builtins.__import__
def deny(name,*args,**kwargs):
 if name.split('.')[0] in ('numpy','shapely','pyslm','scipy','trimesh'):raise AssertionError('AM dependency imported: '+name)
 return original(name,*args,**kwargs)
builtins.__import__=deny
import build_carrier_workshop_guide_v6
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT/'scripts')],cwd='/',capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
