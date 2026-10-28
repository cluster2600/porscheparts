"""Portable JSON/SHA fixtures; no solver, DAT parsing, AM or PDF rendering."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('carrier_guide_v7_tests',ROOT/'scripts/build_carrier_workshop_guide_v7.py')
guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
ORIGINAL_CAPSULE=guide.CAPSULE


class WorkshopGuideV7(unittest.TestCase):
    def setUp(self):
        # Only the two current CAD identities and the old guard are software doubles.
        # The retained numerical reports, executions and their comparisons stay real.
        self.temp=tempfile.TemporaryDirectory(prefix='guide-v7-fixture-',dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.run=self.root/'run';self.capsule=self.root/'capsule'
        shutil.copytree(ORIGINAL_CAPSULE,self.capsule)
        for name in ('mesh.npz','combined-spring-1000-static.inp'):
            path=self.run/'cad/mesh-9'/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('Explicit software-fixture identity: '+name).encode())
        mesh=guide.digest(self.run/'cad/mesh-9/mesh.npz')
        deck=guide.digest(self.run/'cad/mesh-9/combined-spring-1000-static.inp')
        self.rewrite('current-reference-binding.json',lambda d:d.update(
            current_mesh_npz_sha256=mesh,current_linear_deck_sha256=deck))
        self.rewrite('guide-attachment-proposal.json',lambda d:d['required_bindings'].update(
            current_mesh_npz_sha256=mesh,current_linear_reference_deck_sha256=deck,
            new_capsule_binding_sha256=guide.digest(self.capsule/'current-reference-binding.json')))
        manifest=self.read('manifest.json')
        for name in ('current-reference-binding.json','guide-attachment-proposal.json'):
            manifest['files_sha256'][name]=guide.digest(self.capsule/name)
        (self.capsule/'manifest.json').write_text(json.dumps(manifest))
        self.historical=dict(identical_mesh_npz_sha256=mesh,identical_reference_deck_sha256=deck,
            frames_verified=16,ENER_all_frames_pass=False,reference_files_sha256={
                'luo-flat1-analysis.json':manifest['files_sha256']['baseline-16/ener.json'],
                'luo-flat1-finite-work.json':manifest['files_sha256']['baseline-16/piola.json']})
        old=self.run/'constitutive-reference/current-reference-binding.json';old.parent.mkdir()
        old.write_text(json.dumps(self.historical))
        for field,value in [('CAPSULE',self.capsule),('MANIFEST_SHA256',guide.digest(self.capsule/'manifest.json'))]:
            handle=patch.object(guide,field,value);handle.start();self.addCleanup(handle.stop)
        self.old_patch=patch.object(guide._historical,'reference_binding',return_value=copy.deepcopy(self.historical))
        self.old_guard=self.old_patch.start();self.addCleanup(self.old_patch.stop)

    def read(self,name):return json.loads((self.capsule/name).read_text())

    def rewrite(self,name,transform):
        path=self.capsule/name;data=self.read(name);transform(data)
        path.write_text(json.dumps(data,allow_nan=False))

    def tamper(self,name,transform):
        self.rewrite(name,transform)
        manifest=self.read('manifest.json');manifest['files_sha256'][name]=guide.digest(self.capsule/name)
        (self.capsule/'manifest.json').write_text(json.dumps(manifest))
        # Explicit fixture resealing reaches semantic guards after the SHA checks.
        guide.MANIFEST_SHA256=guide.digest(self.capsule/'manifest.json')

    def test_retained_numeric_comparison_and_production_identity_pins(self):
        production=json.loads((ORIGINAL_CAPSULE/'guide-attachment-proposal.json').read_text())['required_bindings']
        self.assertEqual(production['current_mesh_npz_sha256'],'b156b03ab99f65e534a024a63f9cec12529ce9eb6392b0579bf2c20f857a5119')
        self.assertEqual(production['current_linear_reference_deck_sha256'],'903956e464014c32f674869d55c62ca635edce42dfa01a4125938053dc3d8caf')
        before={p:guide.digest(self.capsule/p) for p in guide.verify_sources()}
        result=guide.refinement_binding(self.run)
        self.old_guard.assert_called_once_with(self.run)
        self.assertEqual(result['frames_verified'],32);self.assertEqual(len(result['files_sha256']),44)
        self.assertEqual(result['thresholds'],dict(ENER=.001,Piola=.0001))
        self.assertTrue(result['historical_ENER16_rejection_retained'])
        self.assertGreater(result['worst_Piola_relative_to_gross']['difference'],0)
        self.assertIsNone(result['unloaded_residual']['acceptance_threshold'])
        for key in ('DAT_or_solver_replayed','mesh_convergence_claimed','STEP_equivalence_claimed','global_admission'):
            self.assertFalse(result[key])
        self.assertEqual(before,{p:guide.digest(self.capsule/p) for p in before})

    def test_current_mesh_deck_and_historical_binding_cannot_change(self):
        for name in ('cad/mesh-9/mesh.npz','cad/mesh-9/combined-spring-1000-static.inp',
                     'constitutive-reference/current-reference-binding.json'):
            path=self.run/name;original=path.read_bytes();path.write_bytes(original+b'X')
            with self.subTest(name=name),self.assertRaises(ValueError):guide.refinement_binding(self.run)
            path.write_bytes(original)

    def test_payload_manifest_and_source_pins_refuse_tamper(self):
        path=self.capsule/'refined-32/ener.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'payload changed'):guide.refinement_binding(self.run)
        with patch.object(guide,'BASE_SHA256','0'*64),self.assertRaisesRegex(ValueError,'source changed'):guide.verify_sources()
        with patch.object(guide,'SOURCE_SHA256','0'*64),self.assertRaisesRegex(ValueError,'source changed'):guide.verify_sources()
        with patch.object(guide,'MANIFEST_SHA256','0'*64),self.assertRaisesRegex(ValueError,'manifest changed'):guide.verify_sources()

    def test_resealed_state_threshold_and_rejection_manipulations_refuse(self):
        cases=[('refined-32/ener.json',lambda d:d['frames'][0].update(total_time=.1)),
            ('refined-32/ener.json',lambda d:d['frames'].pop()),
            ('refined-32/ener.json',lambda d:d['frames'].reverse()),
            ('refined-32/ener.json',lambda d:d.update(work_relative_tolerance=.01)),
            ('refined-32/piola.json',lambda d:d['frames'][0].update(minimum_detF_at_Gauss=0.)),
            ('refined-32/piola.json',lambda d:d.update(all_frames_pass=False)),
            ('baseline-16/ener.json',lambda d:d.update(all_frames_ENER_diagnostic_pass=True)),
            ('refined-32/comparison.json',lambda d:d.update(refined_states=31))]
        manifest=(self.capsule/'manifest.json').read_bytes()
        for name,transform in cases:
            original=(self.capsule/name).read_bytes();self.tamper(name,transform)
            with self.subTest(name=name),self.assertRaises(ValueError):guide.refinement_binding(self.run)
            (self.capsule/name).write_bytes(original);(self.capsule/'manifest.json').write_bytes(manifest)
            guide.MANIFEST_SHA256=guide.digest(self.capsule/'manifest.json')

    def test_resealed_failed_solver_or_audit_returncode_refuses(self):
        for name,key in [('receipts/solver-execution.json','actual_container_exit_code'),
                         ('receipts/ENER-audit-execution.json','actual_child_returncode'),
                         ('receipts/Piola-audit-execution.json','actual_child_returncode')]:
            original=(self.capsule/name).read_bytes();manifest=(self.capsule/'manifest.json').read_bytes()
            self.tamper(name,lambda d:d.update({key:1}))
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'execution'):guide.refinement_binding(self.run)
            (self.capsule/name).write_bytes(original);(self.capsule/'manifest.json').write_bytes(manifest)
            guide.MANIFEST_SHA256=guide.digest(self.capsule/'manifest.json')

    def test_render_retains_old_fields_and_copies_only_small_payloads(self):
        data=dict(stages=[dict(id=n,checks=[],files=[],commands=[]) for n in ('reference','dimensions','mechanics','supports','layers','delivery')],
            constitutive_reference={'frames_verified':16,'ENER_all_frames_pass':False},workshop_adapter={'source':'frozen guide6'})
        data['stages'][2]['checks']=[dict(label='ENER16 REFUSÉ')]
        data['stages'][3]['checks']=[dict(label='six admissions unchanged')]
        data['stages'][5]['commands']=['recipe6 unchanged']
        description=self.run/'guide-description.json';description.write_text(json.dumps(data))
        with patch.object(guide,'build',return_value={'fixture':True}) as build:
            self.assertEqual(guide.render(description,self.run/'guide'),{'fixture':True})
        actual=json.loads(description.read_text());target=self.run/guide.TARGET
        self.assertEqual(actual['constitutive_reference'],data['constitutive_reference'])
        self.assertEqual(actual['stages'][3],data['stages'][3]);self.assertEqual(actual['stages'][5],data['stages'][5])
        self.assertEqual(actual['stages'][2]['checks'][0],data['stages'][2]['checks'][0])
        self.assertEqual(actual['workshop_adapter']['retained_adapter'],data['workshop_adapter'])
        self.assertEqual(actual['workshop_adapter']['source'],'scripts/build_carrier_workshop_guide_v7.py')
        self.assertEqual(len(actual['stages'][2]['files']),6);build.assert_called_once()
        self.assertEqual(len([p for p in target.rglob('*') if p.is_file()]),46)
        self.assertLess(sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),1000000)
        with self.assertRaises(FileExistsError):guide.render(description,self.run/'guide')

    def test_changed_copy_after_generic_render_is_refused(self):
        data=dict(stages=[dict(id=n,checks=[],files=[],commands=[]) for n in ('reference','dimensions','mechanics','supports','layers','delivery')])
        description=self.run/'guide-description.json';description.write_text(json.dumps(data))
        def mutate(*_):
            path=self.run/guide.TARGET/'summary.json';path.write_bytes(path.read_bytes()+b' ')
            return {}
        with patch.object(guide,'build',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed during'):
            guide.render(description,self.run/'guide')

    def test_private_hook_and_historical_admission_refusal_propagate(self):
        self.assertIs(guide._base.build,guide.render)
        self.assertEqual(guide.digest(guide.BASE),guide.BASE_SHA256)
        with patch.object(guide._historical,'reference_binding',side_effect=ValueError('Old16 refused')) as old,\
             patch.object(guide,'verify_sources') as verify,self.assertRaisesRegex(ValueError,'Old16'):
            guide.refinement_binding(self.run)
        old.assert_called_once_with(self.run);verify.assert_not_called()
        with patch.object(guide._base,'package',side_effect=ValueError('Retained16 or six-admission refusal')) as old,\
             patch.object(guide,'build') as build,self.assertRaisesRegex(ValueError,'Retained16'):
            guide.package(self.run)
        old.assert_called_once_with(self.run);build.assert_not_called()


if __name__=='__main__':unittest.main()
