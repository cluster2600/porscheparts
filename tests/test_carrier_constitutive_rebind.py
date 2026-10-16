"""Only export identity metadata may change in the frozen constitutive reference."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('constitutive_rebind', SCRIPTS / 'rebind_carrier_constitutive_plan.py')
rebind = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebind)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class ConstitutiveRebindTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        previous = rebind.DESIGN
        rebind.DESIGN = self.root / 'design'
        self.addCleanup(setattr, rebind, 'DESIGN', previous)
        self.run, self.output = self.root / 'run', self.root / 'plan'
        self.mesh = self.run / 'cad/mesh-9'
        self.mesh.mkdir(parents=True)
        (self.mesh / 'mesh.npz').write_bytes(b'identical data arrays')
        (self.mesh / 'combined-spring-1000-static.inp').write_bytes(b'unchanged loads and springs')
        (self.mesh / 'mesh.inp').write_text('*Heading\ncurrent/path\n*NODE\n1,0,0,0\n')
        (self.run / 'cad/carrier.step').write_bytes(b'new STEP export')
        self.geometry = {'dense_reference_mass_kg': 1.262,
                         'geometry_sha256': {'carrier.step': rebind.sha(self.run / 'cad/carrier.step')}}
        write(self.run / 'cad/geometry.json', self.geometry)
        write(self.run / 'comparison/comparison.json', {'selection': {'selection_pass': True}})
        witness = {'mesh_NPZ_sha256': rebind.sha(self.mesh / 'mesh.npz'),
                   'mesh_INP_after_only_heading_removal_sha256': hashlib.sha256(rebind.mesh_without_heading(self.mesh / 'mesh.inp')).hexdigest(),
                   'reference_deck_sha256': rebind.sha(self.mesh / 'combined-spring-1000-static.inp')}
        write(rebind.DESIGN / 'constitutive-evidence/constitutive-binding-independent-002.json', witness)
        self.template = {'frozen_at_UTC': 'old timestamp', 'geometry_STEP_sha256': 'a'*64,
                         'mesh_inp_sha256': 'b'*64, 'reference_deck_sha256': witness['reference_deck_sha256'],
                         'plasticity': {'curve_sha256': 'c'*64, 'E_MPa': 106000, 'nu': .31},
                         'step': {'initial_increment': .125}, 'unload_to_zero': True,
                         'fixture': 'same springs', 'criterion': .0001}
        write(rebind.DESIGN / 'luo-flat1-nlgeom-plan.json', self.template)

    def test_all_material_load_fixture_increment_and_criterion_values_remain_unchanged(self):
        result = rebind.prepare(self.run, self.output)
        plan = json.loads((self.output / 'plan.json').read_text())
        self.assertEqual(result['status'], 'plan_prepared_no_solver_execution')
        allowed = {'frozen_at_UTC', 'geometry_STEP_sha256', 'mesh_inp_sha256'}
        self.assertEqual(set(result['changed_fields']), allowed)
        self.assertEqual({k: v for k, v in plan.items() if k not in allowed},
                         {k: v for k, v in self.template.items() if k not in allowed})

    def test_changed_solver_mesh_is_refused_even_if_NPZ_remains_identical(self):
        (self.mesh / 'mesh.inp').write_text('*Heading\nnew/path\n*NODE\n1,1,0,0\n')
        with self.assertRaisesRegex(ValueError, 'identical mesh'):
            rebind.prepare(self.run, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_reference_load_deck_is_refused(self):
        (self.mesh / 'combined-spring-1000-static.inp').write_bytes(b'altered fixture')
        with self.assertRaisesRegex(ValueError, 'identical mesh'):
            rebind.prepare(self.run, self.output)
        self.assertFalse(self.output.exists())

    def test_mass_or_selection_failure_prevents_plan_creation(self):
        for mass, selected in ((1.31, True), (1.262, False)):
            self.geometry['dense_reference_mass_kg'] = mass
            write(self.run / 'cad/geometry.json', self.geometry)
            write(self.run / 'comparison/comparison.json', {'selection': {'selection_pass': selected}})
            with self.subTest(mass=mass, selected=selected), self.assertRaisesRegex(ValueError, 'ceiling must pass'):
                rebind.prepare(self.run, self.output)
            self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
