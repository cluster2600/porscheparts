"""Relocation may move interior nodes; it must not admit a flat or changed boundary."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None
SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('interior_relocation', SOURCE / 'audit_interior_relocation.py')
module = importlib.util.module_from_spec(spec)
if np is not None:
    spec.loader.exec_module(module)


@unittest.skipIf(np is None, 'NumPy unavailable')
class InteriorRelocationTests(unittest.TestCase):
    def fixture(self, folder, interior):
        parent, optimized = folder / 'parent', folder / 'optimized'
        parent.mkdir(); optimized.mkdir()
        vertices = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [.1, .1, .1]])
        boundary = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        cells = np.column_stack((np.full(4, 4), boundary))
        moved = vertices.copy(); moved[4] = interior
        for path, points in ((parent, vertices), (optimized, moved)):
            np.savez_compressed(path / 'volume.npz', vertices=points, tetrahedra=cells, boundary=boundary)
        sha = module.sha
        baseline = dict(schema='935-conforming-volume-audit-v1', status='topology_and_exact_orientation_passed',
                        volume_npz_sha256=sha(parent / 'volume.npz'), scale_verified=False,
                        geometry_sha256='a' * 64, prepared_receipt_sha256='b' * 64,
                        exact_orientation=module.exact_orientation(vertices, cells))
        worker = sha(SOURCE / 'relocate_conforming_volume.py')
        proposal = dict(status='interior_relocated_not_audited', optimizer='Relocate3D', source_sha256=worker,
                        input_sha256=baseline['volume_npz_sha256'], volume_npz_sha256=sha(optimized / 'volume.npz'),
                        mechanical_mesh_admitted=False, manufacturing_authorized=False)
        execution = dict(input_sha256=baseline['volume_npz_sha256'], exit=0, stop_reason=None, worker_sha256=worker)
        for path, record in ((parent / 'assessment.json', baseline), (optimized / 'assessment.json', proposal),
                             (optimized / 'execution.json', execution)):
            path.write_text(json.dumps(record))
        return parent, optimized

    def test_positive_interior_move_preserves_exact_volume_without_mechanical_admission(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); parent, optimized = self.fixture(base, [.2, .2, .2])
            self.assertTrue(module.audit(parent, optimized, base / 'audited'))
            report = json.loads((base / 'audited/assessment.json').read_text())
            self.assertTrue(report['exact_volume_matches_parent'])
            self.assertEqual(report['relocation']['moved_interior_nodes'], 1)
            self.assertFalse(report['mechanical_mesh_admitted'])

    def test_flat_or_inverted_cell_is_refused_even_when_exact_total_volume_matches(self):
        for coordinate, count in ((0., 'zero'), (-.1, 'negative')):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as folder:
                base = Path(folder); parent, optimized = self.fixture(base, [coordinate, .2, .2])
                self.assertFalse(module.audit(parent, optimized, base / 'refused'))
                report = json.loads((base / 'refused/assessment.json').read_text())
                self.assertTrue(report['exact_volume_matches_parent'])
                self.assertGreater(report['exact_orientation'][count], 0)
                self.assertEqual(report['status'], 'volume_refused')

    def test_star_kernel_provenance_is_checked_and_unknown_optimizer_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); parent, optimized = self.fixture(base, [.2, .2, .2])
            proposal = json.loads((optimized / 'assessment.json').read_text())
            execution = json.loads((optimized / 'execution.json').read_text())
            proposal['optimizer'] = 'StarKernelLinearProgram'
            proposal['source_sha256'] = module.sha(SOURCE / 'optimize_interior_stars.py')
            execution['worker_sha256'] = proposal['source_sha256']
            (optimized / 'assessment.json').write_text(json.dumps(proposal))
            (optimized / 'execution.json').write_text(json.dumps(execution))
            self.assertTrue(module.audit(parent, optimized, base / 'audited'))
            proposal['optimizer'] = 'unqualified'
            (optimized / 'assessment.json').write_text(json.dumps(proposal))
            with self.assertRaises(ValueError): module.audit(parent, optimized, base / 'refused')
            self.assertFalse((base / 'refused').exists())

    def test_boundary_connectivity_and_nonfinite_changes_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            parent, optimized = self.fixture(Path(folder), [.2, .2, .2])
            with np.load(parent / 'volume.npz') as old, np.load(optimized / 'volume.npz') as new:
                original = {key: old[key].copy() for key in old.files}
                candidate = {key: new[key].copy() for key in new.files}
            for kind in ('boundary', 'connectivity', 'nonfinite'):
                changed = {key: value.copy() for key, value in candidate.items()}
                if kind == 'boundary': changed['vertices'][0, 0] = .01
                elif kind == 'connectivity': changed['tetrahedra'][0, [1, 2]] = changed['tetrahedra'][0, [2, 1]]
                else: changed['vertices'][4, 0] = np.nan
                with self.assertRaises(ValueError, msg=kind): module.fixed_geometry(original, changed)

    def test_tampered_parent_receipt_is_refused_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); parent, optimized = self.fixture(base, [.2, .2, .2])
            record = json.loads((parent / 'assessment.json').read_text()); record['volume_npz_sha256'] = 'c' * 64
            (parent / 'assessment.json').write_text(json.dumps(record))
            with self.assertRaises(ValueError): module.audit(parent, optimized, base / 'refused')
            self.assertFalse((base / 'refused').exists())
