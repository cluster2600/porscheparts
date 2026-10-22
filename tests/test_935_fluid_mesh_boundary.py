import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/935-horizontal-cooling-system-f0/source'
STUDY = SOURCE / 'fluid-mesh-study-20261022'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    spec = importlib.util.spec_from_file_location('fluid_boundary_case', STUDY / 'export-fluid-plc-005.py')
    boundary_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boundary_module)
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires NumPy')
class FluidBoundaryTests(unittest.TestCase):
    def test_published_checkpoint_preserves_refusals_and_source_hashes(self):
        import hashlib
        record = json.loads((ROOT / 'docs/research/935-horizontal-cooling/fluid-mesh-correction-20261022.json').read_text())
        for name, digest in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        self.assertTrue(all(value is False for value in record['scope'].values()))
        for candidate in record['volume_candidates'].values():
            self.assertTrue(candidate['all_cells_positive'])
            self.assertTrue(candidate['exact_PLC_volume_equal'])
            self.assertTrue(candidate['complete_boundary_coordinate_triangle_marker_bijection'])
            self.assertTrue(candidate['original_quality_dictionary_unchanged'])
            self.assertFalse(candidate['extended_mesh_quality_passed'])
            self.assertGreater(candidate['failed_native_checks'], 0)
        self.assertEqual(record['new_rotor_PDE_runs'], 0)
        self.assertEqual(record['runtime']['new_Vast_rentals'], 0)

    def test_ascii_mode_and_header_capacity_are_strict(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'points'
            p.write_text('/* comment */ FoamFile {format ascii;class vectorField;object points;}\n4\n((0 0 0)(1 0 0)(0 1 0)(0 0 1))\n// footer\n')
            count, body = boundary_module.foam_list(p)
            self.assertEqual(count, 4)
            self.assertEqual(len(np.fromstring(body.replace('(', ' ').replace(')', ' '), sep=' ')), 12)
            self.assertEqual(boundary_module.foam_list(p, maximum_count=4)[0], 4)
            for capacity in (False, 0, 10_000_001):
                with self.assertRaises(ValueError):
                    boundary_module.foam_list(p, maximum_count=capacity)
            for text in ('FoamFile {format binary;}\n4\n()','FoamFile {format ascii;}\n0\n()','FoamFile {format ascii;}\n2000001\n()'):
                p.write_text(text)
                with self.assertRaises(ValueError):
                    boundary_module.foam_list(p)

    def test_solid_and_fluid_winding_are_independent(self):
        v = np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        f = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        self.assertAlmostEqual(boundary_module.winding(v, f, np.array([.1,.1,.1])), 1)
        self.assertAlmostEqual(boundary_module.winding(v, f, np.array([2.,2,2])), 0)
        self.assertAlmostEqual(boundary_module.winding(v, f[:,::-1], np.array([.1,.1,.1])), -1)

    def test_complete_tet_and_marker_audit_rejects_changed_marker(self):
        try:
            import scipy
        except ImportError:
            self.skipTest('Requires SciPy connectivity helper')
        import os
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepared, meshed = root / 'prepared', root / 'meshed'
            prepared.mkdir(); meshed.mkdir()
            v = np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
            f = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
            np.savez(prepared / 'boundary.npz', vertices=v, triangles=f, markers=np.arange(1,5))
            import hashlib
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            (prepared / 'fluid.smesh').write_text('synthetic fixture; the native surface guard is a separate step\n')
            (meshed / 'fluid.smesh').write_bytes((prepared / 'fluid.smesh').read_bytes())
            (prepared / 'receipt.json').write_text(json.dumps({'output_sha256': {name:digest(prepared/name) for name in ['boundary.npz','fluid.smesh']}}))
            (meshed / 'execution.json').write_text(json.dumps({'exit':0,'stop_reason':None,'input_file_unchanged':True,'input_smesh_sha256':digest(prepared/'fluid.smesh')}))
            (meshed / 'fluid.1.node').write_text('4 3 0 0\n0 0 0 0\n1 1 0 0\n2 0 1 0\n3 0 0 1\n')
            (meshed / 'fluid.1.ele').write_text('1 4 0\n0 0 1 2 3\n')
            path = meshed / 'fluid.1.face'
            rows = [f'{i} {a} {b} {c} {i+1}\n' for i,(a,b,c) in enumerate(f)]
            path.write_text('4 1\n' + ''.join(rows))
            env = dict(os.environ, PYTHONPATH=str(SOURCE))
            command = [sys.executable, str(STUDY / 'audit-tetgen-002.py'), str(prepared), str(meshed)]
            done = subprocess.run(command + [str(root / 'accepted')], env=env, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            report = json.loads((root / 'accepted/assessment.json').read_text())
            self.assertEqual(report['exact_cell_orientation']['signed_volume_exact'], '1/6')
            self.assertTrue(report['complete_boundary_coordinate_triangle_marker_bijection'])
            self.assertFalse(report['CFD_accepted'])
            rows[0] = rows[0].replace(' 1\n', ' 2\n')
            path.write_text('4 1\n' + ''.join(rows))
            rejected = subprocess.run(command + [str(root / 'rejected')], env=env, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse((root / 'rejected').exists())
            path.write_text('4 1\n' + ''.join([f'{i} {a} {b} {c} {i+1}\n' for i,(a,b,c) in enumerate(f)]))
            (prepared / 'boundary.npz').write_bytes(b'changed reference')
            tampered = subprocess.run(command + [str(root / 'tampered')], env=env, capture_output=True, text=True)
            self.assertNotEqual(tampered.returncode, 0)
            self.assertFalse((root / 'tampered').exists())


if __name__ == '__main__':
    unittest.main()
