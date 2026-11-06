"""Reject invalid qualification evidence before constructing a GPU workload."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/prepare_conditioned_ported_warp_oracle.py'


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('igl'),
                     'Pinned numerical oracle dependencies are optional')
class ConditionedPortedAdmissionTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.archive = self.directory / 'candidate.npz'
        np.savez(self.archive, vertices=np.zeros((4, 3)), triangles=np.array([[0, 1, 2]]))
        self.binding = self.directory / 'independent-receipt.json'
        self.binding.write_text('{}\n')
        self.record = dict(status='conditioned_ported_geometry_checked',
                           manufacturing_authorized=False,
                           output_sha256=self.sha(self.archive),
                           protected_original_oriented_triangles_exact=True,
                           final_oriented_triangle_roundtrip_exact=True,
                           independent_complete_surface_check_passed=True,
                           complete_surface_fidelity_bound_mm=.008,
                           nominal_mass_kg=1.2934, positive_material_shells=1,
                           negative_closed_void_shells=0,
                           input_sha256={str(self.binding): self.sha(self.binding)})

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def rejected(self, message):
        (self.directory / 'assessment.json').write_text(json.dumps(self.record))
        result = subprocess.run([sys.executable, str(SCRIPT), '--variant-directory',
                                 str(self.directory), '--output', str(self.directory / 'oracle')],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertFalse((self.directory / 'oracle/carrier-queries.npz').exists())

    def test_closed_chamber_status_cannot_admit_a_ported_model(self):
        self.record['status'] = 'complete_closed_chamber_variant_geometry_checked'
        self.rejected('Checked conditioned ported variant identity required')

    def test_nan_fidelity_cannot_bypass_the_limit(self):
        self.record['complete_surface_fidelity_bound_mm'] = float('nan')
        self.rejected('Ported geometry limits differ')

    def test_changed_independent_receipt_is_rejected(self):
        self.binding.write_text('{"changed": true}\n')
        self.rejected('Ported qualification input changed')

    def test_empty_independent_bindings_are_rejected(self):
        self.record['input_sha256'] = {}
        self.rejected('Independent qualification bindings required')


if __name__ == '__main__':
    unittest.main()
