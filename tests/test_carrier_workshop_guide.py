"""A delivery guide must not mix model identities or package altered scan paths."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('carrier_workshop_guide', SCRIPTS / 'build_carrier_workshop_guide.py')
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class CarrierWorkshopGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'work/run'
        for directory in ('cad', 'surface', 'surface-audit', 'comparison', 'process/layers'):
            (self.run / directory).mkdir(parents=True, exist_ok=True)
        for name, content in [('cad/carrier.step', b'known STEP'), ('surface/carrier-remeshed.stl', b'known STL'),
                              ('process/layers/layer-00000.npz', b'known vectors'), ('process/support-000.stl', b'known support')]:
            (self.run / name).write_bytes(content)
        step, mesh = guide.sha(self.run / 'cad/carrier.step'), guide.sha(self.run / 'surface/carrier-remeshed.stl')
        self.write('cad/geometry.json', {'geometry_sha256': {'carrier.step': step}, 'design_id': 'fixture', 'dense_reference_mass_kg': 1.25})
        self.write('cad/protected-interfaces.json', {'central_pad_symmetric_difference_mm3': 0})
        self.write('surface-audit/cad-mesh-audit.json', {'STEP_sha256': step, 'candidate_STL_sha256': mesh,
                   'status': 'passed', 'topology': {'needle_triangles': 0, 'triangles': 12},
                   'mesh_to_exact_CAD': {'maximum_distance_to_STEP_shell_mm': .01}, 'exact_CAD_to_mesh': {'maximum_mm': .02}})
        self.write('comparison/comparison.json', {'STEP_sha256': step, 'selection': {'selection_pass': True, 'declared_mass_ceiling_kg': 1.3},
                   'cases': [{'mesh': 'mesh-7', 'case': 'combined-rigid-static', 'metrics': {
                       'displacement_max_mm': {'candidate': 2}, 'integration_point_VM_max_MPa': {'candidate': 700, 'change_percent': -10}}}]})
        self.process = {'input_sha256': mesh, 'status': 'open_build_preparation_completed',
                        'source_and_runtime_unchanged_at_completion': True, 'n_layers': 1,
                        'parameters': {'layer_height_mm': .06}, 'supports': [{}], 'fits_500mm_square_plate': True,
                        'part_hatch_segments': 2, 'support_scan_segments': 3,
                        'outputs_sha256': {name: guide.sha(self.run / 'process' / name)
                                           for name in ('layers/layer-00000.npz', 'support-000.stl')}}
        self.write('process/report.json', self.process)
        self.patch = patch.object(guide, 'ROOT', self.root)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def write(self, name, value):
        (self.run / name).write_text(json.dumps(value))

    def test_packaging_binds_the_same_revision_and_preserves_vector_bytes(self):
        with patch.object(guide, 'build', return_value={}) as build:
            guide.package(self.run)
        data = json.loads((self.run / 'guide-description.json').read_text())
        self.assertEqual(data['metrics'][0]['value'], '1,250 kg')
        with zipfile.ZipFile(self.run / 'delivery-assets/scanpaths.zip') as archive:
            self.assertEqual(archive.read('layers/layer-00000.npz'), b'known vectors')
        self.assertEqual(build.call_args.args[1], self.run / 'guide')

    def test_mixed_surface_identity_is_refused_before_packaging(self):
        self.process['input_sha256'] = '0' * 64
        self.write('process/report.json', self.process)
        with self.assertRaisesRegex(ValueError, 'Mixed surface'):
            guide.package(self.run)
        self.assertFalse((self.run / 'delivery-assets').exists())

    def test_changed_layer_is_refused_before_packaging(self):
        (self.run / 'process/layers/layer-00000.npz').write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError, 'Slicing artifact identity'):
            guide.package(self.run)
        self.assertFalse((self.run / 'delivery-assets').exists())


if __name__ == '__main__':
    unittest.main()
