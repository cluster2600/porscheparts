"""A historical sensitivity cannot be attached to a different mesh or load deck."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('constitutive_binding', SCRIPTS / 'bind_carrier_constitutive_evidence.py')
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class ConstitutiveBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name, value in (('ROOT', self.root), ('DESIGN', self.root / 'design')):
            previous = getattr(binding, name)
            setattr(binding, name, value)
            self.addCleanup(setattr, binding, name, previous)
        self.original, self.cad = self.root / 'work/raw', self.root / 'cad'
        self.original.mkdir(parents=True)
        (self.cad / 'mesh-9').mkdir(parents=True)
        for name, data in [('mesh.npz', b'exact mesh'), ('reference-linear.inp', b'exact deck'),
                           ('combined-spring-1000-luo-flat1-NLGEOM.dat', b'sixteen recorded states')]:
            (self.original / name).write_bytes(data)
        (self.cad / 'mesh-9/mesh.npz').write_bytes(b'exact mesh')
        (self.cad / 'mesh-9/combined-spring-1000-static.inp').write_bytes(b'exact deck')
        (self.cad / 'carrier.step').write_bytes(b'current export')
        write(self.cad / 'geometry.json', {'geometry_sha256': {'carrier.step': binding.sha(self.cad / 'carrier.step')}})
        write(self.original / 'plan.json', {'reference_deck_sha256': binding.sha(self.original / 'reference-linear.inp')})
        self.work = {'all_frames_pass': True, 'frames': [{}] * 16,
                     'solver_dat_sha256': binding.sha(self.original / 'combined-spring-1000-luo-flat1-NLGEOM.dat')}
        self.evidence = binding.DESIGN / 'constitutive-evidence'
        write(self.evidence / 'luo-flat1-finite-work.json', self.work)
        self.case = {'id': binding.CASE, 'retained_folder': 'work/raw',
                     'raw_inputs_sha256': {p.name: binding.sha(p) for p in self.original.iterdir()},
                     'compact_evidence': {'luo-flat1-finite-work.json': binding.sha(self.evidence / 'luo-flat1-finite-work.json')},
                     'unloading_complete': True, 'within_measured_pre_necking_domain': True,
                     'constitutive_model': {'type': 'published reference sensitivity'}, 'unloaded_residual': {},
                     'independent_work': {}, 'ENER_all_frames_pass': False}
        self.save_summary()
        self.output = self.root / 'bound'

    def save_summary(self):
        write(binding.DESIGN / 'constitutive-results.json', {'geometry_STEP_sha256': 'a' * 64, 'cases': [self.case]})

    def test_identical_discrete_problem_preserves_the_scope_and_rejected_ENER_diagnostic(self):
        result = binding.bind(self.cad, self.output)
        self.assertEqual(result['status'], 'identical_discrete_reference_verified')
        self.assertNotEqual(result['source_geometry_STEP_sha256'], result['current_geometry_STEP_sha256'])
        self.assertFalse(result['ENER_all_frames_pass'])
        self.assertNotIn('manufacturing_authorized', result)
        self.assertIn('No new solve', result['scope'])

    def test_changed_mesh_or_fixture_is_refused_before_output(self):
        for name in ('mesh.npz', 'combined-spring-1000-static.inp'):
            path = self.cad / 'mesh-9' / name
            original = path.read_bytes()
            path.write_bytes(b'changed model')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'identical'):
                binding.bind(self.cad, self.output)
            self.assertFalse(self.output.exists())
            path.write_bytes(original)

    def test_changed_retained_solver_output_is_refused(self):
        (self.original / 'combined-spring-1000-luo-flat1-NLGEOM.dat').write_bytes(b'changed solve')
        with self.assertRaisesRegex(ValueError, 'Retained constitutive evidence'):
            binding.bind(self.cad, self.output)
        self.assertFalse(self.output.exists())

    def test_partial_or_failed_work_audit_is_refused_with_valid_file_hash(self):
        for alteration in ({'frames': [{}] * 15}, {'all_frames_pass': False}):
            write(self.evidence / 'luo-flat1-finite-work.json', {**self.work, **alteration})
            self.case['compact_evidence']['luo-flat1-finite-work.json'] = binding.sha(self.evidence / 'luo-flat1-finite-work.json')
            self.save_summary()
            with self.subTest(alteration=alteration), self.assertRaisesRegex(ValueError, 'sixteen-state'):
                binding.bind(self.cad, self.output)
            self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
