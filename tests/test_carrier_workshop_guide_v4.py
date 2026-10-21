"""Guide presentation fixtures; no solve, DAT parsing or real PDF export."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_part_workflow_guide as renderer
import build_carrier_workshop_guide_v2 as public_v2
import build_carrier_workshop_guide_v3 as public_v3
ORIGINAL_V2_BUILD, ORIGINAL_V3_BUILD = public_v2.build, public_v3.build
spec = importlib.util.spec_from_file_location('carrier_workshop_v4', ROOT/'scripts/build_carrier_workshop_guide_v4.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)
PRODUCTION_REFERENCE = guide.REFERENCE_FILES.copy()


class WorkshopGuideV4(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root/'work/run'
        (self.run/'cad/mesh-9').mkdir(parents=True)
        (self.run/'comparison').mkdir()
        self.sources = self.root/'retained'
        self.sources.mkdir()
        self.pins = {}
        for name, (source, _) in PRODUCTION_REFERENCE.items():
            shutil.copyfile(source, self.sources/name)
        self.mesh = self.run/'cad/mesh-9/mesh.npz'
        self.deck = self.run/'cad/mesh-9/combined-spring-1000-static.inp'
        self.mesh.write_bytes(b'explicit software-fixture mesh bytes')
        self.deck.write_bytes(b'explicit software-fixture linear deck bytes')
        (self.run/'cad/carrier.step').write_bytes(b'new distinct software-fixture STEP export')
        summary = self.read('constitutive-results.json')
        next(c for c in summary['cases'] if c['id'] == guide.CASE_ID)['raw_inputs_sha256']['mesh.npz'] = guide.digest(self.mesh)
        self.save('constitutive-results.json', summary)
        binding = self.read('constitutive-binding-result.json')
        binding['identical_mesh_npz_sha256'] = guide.digest(self.mesh)
        binding['identical_reference_deck_sha256'] = guide.digest(self.deck)
        self.save('constitutive-binding-result.json', binding)
        cycle = self.read('luo-flat1-cycle.json')
        cycle['mesh_npz_sha256'] = guide.digest(self.mesh)
        self.save('luo-flat1-cycle.json', cycle)
        self.refresh()
        self.addCleanup(patch.stopall)
        patch.object(guide, 'ROOT', self.root).start()
        patch.object(guide, 'REFERENCE_FILES', self.pins).start()
        self.comparison = dict(cases=[dict(mesh='mesh-9', case='combined-spring-1000-static',
            metrics=dict(integration_point_VM_max_MPa=dict(candidate=1801.234)))])
        self.save_comparison()

    def read(self, name):
        return json.loads((self.sources/name).read_text())

    def save(self, name, data):
        (self.sources/name).write_text(json.dumps(data))

    def refresh(self):
        self.pins.update({name:(self.sources/name, guide.digest(self.sources/name)) for name in PRODUCTION_REFERENCE})

    def bind_compacts(self):
        self.refresh()
        summary = self.read('constitutive-results.json')
        case = next(c for c in summary['cases'] if c['id'] == guide.CASE_ID)
        cycle = self.read('luo-flat1-cycle.json')
        for name, field in [('luo-flat1-analysis.json', 'analysis_sha256'), ('luo-flat1-finite-work.json', 'work_audit_sha256')]:
            case['compact_evidence'][name] = self.pins[name][1]
            cycle[field] = self.pins[name][1]
        self.save('constitutive-results.json', summary)
        self.save('luo-flat1-cycle.json', cycle)
        self.refresh()

    def save_comparison(self):
        (self.run/'comparison/comparison.json').write_text(json.dumps(self.comparison))

    def descriptor(self):
        data = json.loads((ROOT/'manufacturing/workflows/993-carrier-guide.json').read_text())
        data['stages'][5]['commands'] = ['python3 scripts/run_part_workflow.py run '+guide.OLD_RECIPE+' --runtime work/RUNTIME.json',
                                        'python3 scripts/assemble_carrier_workflow.py verify work/run']
        path = self.run/'guide-description.json'
        path.write_text(json.dumps(data))
        return path

    def test_same_discrete_problem_allows_distinct_STEP_exports_without_equivalence_claim(self):
        binding = guide.reference_binding(self.run)
        self.assertEqual(binding['frames_verified'], 16)
        self.assertTrue(binding['independent_Piola_all_frames_pass'])
        self.assertFalse(binding['ENER_all_frames_pass'])
        self.assertFalse(binding['STEP_equivalence_claimed'])
        self.assertNotEqual(binding['current_STEP_sha256'], binding['retained_source_STEP_sha256'])
        self.assertEqual(binding['identical_mesh_npz_sha256'], guide.digest(self.mesh))

    def test_mesh_or_deck_change_refuses_before_copy_or_base_package(self):
        for path in [self.mesh, self.deck]:
            original = path.read_bytes();path.write_bytes(original+b' changed')
            with self.subTest(path=path), patch.object(guide._base, 'package') as base:
                with self.assertRaisesRegex(ValueError, 'mesh or reference deck'):
                    guide.package(self.run)
                base.assert_not_called()
                self.assertFalse((self.run/'constitutive-reference').exists())
            path.write_bytes(original)

    def test_retained_result_change_refuses_its_source_pin(self):
        path = self.sources/'constitutive-results.json'
        path.write_text(path.read_text()+' ')
        with self.assertRaisesRegex(ValueError, 'reference changed'):
            guide.prepare_reference(self.run)

    def test_rehashed_compact_evidence_must_still_match_case_summary(self):
        path = self.sources/'luo-flat1-finite-work.json'
        path.write_text(path.read_text()+' ');self.refresh()
        with self.assertRaisesRegex(ValueError, 'compact evidence'):
            guide.reference_binding(self.run)

    def test_fifteen_states_cannot_pass_even_after_rebinding_compact_hashes(self):
        work = self.read('luo-flat1-finite-work.json');work['frames'].pop()
        self.save('luo-flat1-finite-work.json', work);self.bind_compacts()
        with self.assertRaisesRegex(ValueError, 'sixteen-state'):
            guide.reference_binding(self.run)

    def test_false_Piola_or_promoted_ENER_verdict_is_refused(self):
        work = self.read('luo-flat1-finite-work.json');work['frames'][0]['work_pass'] = False
        self.save('luo-flat1-finite-work.json', work);self.bind_compacts()
        with self.assertRaisesRegex(ValueError, 'Piola/ENER'):
            guide.reference_binding(self.run)
        work['frames'][0]['work_pass'] = True;self.save('luo-flat1-finite-work.json', work);self.bind_compacts()
        binding = self.read('constitutive-binding-result.json');binding['ENER_all_frames_pass'] = True
        self.save('constitutive-binding-result.json', binding);self.refresh()
        with self.assertRaisesRegex(ValueError, 'Piola/ENER'):
            guide.reference_binding(self.run)

    def test_descriptor_and_HTML_expose_findings_and_copy_all_bound_reference_files(self):
        descriptor = self.descriptor()
        before = json.loads(descriptor.read_text())
        guide.prepare_reference(self.run)
        def fake_pdf(data, output):
            (output/'guide-atelier.pdf').write_bytes(b'%PDF-software-fixture')
        with patch.object(renderer, 'ROOT', self.root), patch.object(renderer, 'make_pdf', fake_pdf):
            manifest = guide.render(descriptor, self.run/'guide')
        data = json.loads(descriptor.read_text())
        visible = json.dumps(data['stages'][2], ensure_ascii=False)
        for text in ['1801,23', '900 MPa', 'Grade 23 ELI', 'Grade 5', 'Piola indépendant : PASS', 'ENER sur tous les états : REFUSÉ']:
            self.assertIn(text, visible)
        self.assertIn(guide.NEW_RECIPE, data['stages'][5]['commands'][0].split())
        self.assertEqual(data['stages'][5]['commands'][1], before['stages'][5]['commands'][1])
        for index in [0, 1, 3, 4]:self.assertEqual(data['stages'][index], before['stages'][index])
        html = (self.run/'guide/index.html').read_text()
        self.assertIn('Grade 23 ELI', html)
        self.assertIn('REFUSÉ', html)
        self.assertEqual(len(manifest['sources']), 7)
        self.assertEqual(set(p.name for p in (self.run/'constitutive-reference').iterdir()),
                         set(PRODUCTION_REFERENCE)|{'current-reference-binding.json'})
        self.assertIs(public_v2.build, ORIGINAL_V2_BUILD)
        self.assertIs(public_v3.build, ORIGINAL_V3_BUILD)

    def test_changed_copied_figure_refuses_before_rendering(self):
        descriptor = self.descriptor();guide.prepare_reference(self.run)
        (self.run/'constitutive-reference/luo-flat1-cycle.png').write_bytes(b'changed image')
        with patch.object(guide, 'build') as build, self.assertRaisesRegex(ValueError, 'Copied'):
            guide.render(descriptor, self.run/'guide')
        build.assert_not_called()

    def test_unrecognized_command_or_nonfinite_current_peak_cannot_be_presented(self):
        descriptor = self.descriptor();guide.prepare_reference(self.run)
        data = json.loads(descriptor.read_text());data['stages'][5]['commands'][0] = 'unexpected command'
        descriptor.write_text(json.dumps(data));before = descriptor.read_bytes()
        with self.assertRaisesRegex(ValueError, 'reproduction command'):
            guide.render(descriptor, self.run/'guide')
        self.assertEqual(descriptor.read_bytes(), before)
        descriptor = self.descriptor()
        self.comparison['cases'][0]['metrics']['integration_point_VM_max_MPa']['candidate'] = float('nan')
        self.save_comparison()
        with self.assertRaisesRegex(ValueError, 'finite and positive'):
            guide.render(descriptor, self.run/'guide')

    def test_changed_guide_source_refuses_before_private_package(self):
        with patch.object(guide, 'SOURCE_SHA256', '0'*64), patch.object(guide._base, 'package') as base:
            with self.assertRaisesRegex(ValueError, 'guide sources changed'):
                guide.package(self.run)
            base.assert_not_called()


if __name__ == '__main__':
    unittest.main()
