"""Boundary preservation cannot be inferred from matching counts or point sets."""
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import subprocess
import sys
import tarfile
import io
from unittest.mock import Mock,patch
import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/optimize_tetrahedra_gmsh.py'
spec = importlib.util.spec_from_file_location('carrier_optimizer', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoundaryIdentityTests(unittest.TestCase):
    def test_native_replay_keeps_hash_overflow_failure_and_unconverged_fields_explicit(self):
        evidence=SOURCE.parents[5]/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025'
        read=lambda name:json.loads((evidence/name).read_text())
        self.assertTrue(read('mac-ccx-2.21-002/hash64-vanilla-assessment.json')['signed_integer_overflow_detected'])
        self.assertTrue(read('mac-ccx-2.21-003/hash64-fixed-assessment.json')['passed'])
        self.assertEqual(read('mac-h0-P2-reference-001/actual-terminal.json')['actual_returncode'],-11)
        self.assertFalse(read('local-worker-exit-race-refusal-001.json')['accepted_for_comparison'])
        self.assertTrue(read('mac-clean-replay-identity-001.json')['binary_byte_identity_passed'])
        self.assertTrue(read('mac-linux-reference-comparison-001.json')['within_all_limits'])
        self.assertEqual(read('mac-remeshed-P2-assessment-001/assessment.json')['status'],
                         'complete_linear_C3D10_results_equilibrium_and_energy_passed')
        self.assertFalse(read('remeshed-P1-comparison-001.json')['convergence_demonstrated'])

    def test_native_builder_rejects_source_path_escape_before_creating_destination(self):
        spec=importlib.util.spec_from_file_location('local_ccx_worker',SOURCE.with_name('run_local_ccx_serial.py'))
        worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
        spec=importlib.util.spec_from_file_location('mac_ccx_builder',SOURCE.with_name('build_macos_ccx.py'))
        builder=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'run_local_ccx_serial':worker}):spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);archive=base/'bad.tar';destination=base/'destination'
            with tarfile.open(archive,'w') as output:
                item=tarfile.TarInfo('../escape');item.size=1
                output.addfile(item,io.BytesIO(b'x'))
            with self.assertRaises(ValueError):builder.unpack(archive,destination)
            self.assertFalse(destination.exists());self.assertFalse((base/'escape').exists())

    def test_local_memory_probe_refuses_missing_or_invalid_measurements(self):
        spec = importlib.util.spec_from_file_location('local_ccx_worker', SOURCE.with_name('run_local_ccx_serial.py'))
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        self.assertEqual(worker.rss_bytes(' 1234\n'),1234*1024)
        self.assertEqual(worker.rss_bytes('0'),0)
        for text in ['', '-1', 'nan', '12 34']:
            with self.assertRaises(ValueError):worker.rss_bytes(text)
        for error in [ProcessLookupError,PermissionError]:
            child=Mock(pid=123)
            child.poll.return_value=None
            child.wait.return_value=0
            with patch.object(worker.os,'killpg',side_effect=error):worker.stop_and_reap(child)
            child.terminate.assert_not_called()
            child.kill.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            binary = base/'binary'
            binary.write_text('not executable')
            output = base/'output'
            result = subprocess.run([sys.executable,str(SOURCE.with_name('run_local_ccx_serial.py')),
                '--binary',str(binary),'--expected-binary','0'*64,'--deck',str(base/'absent.inp'),
                '--output',str(output),'--seconds','1','--rss-gib','1'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(output.exists())

    def test_doubled_volume_is_refused_before_the_extracted_candidate_is_admitted(self):
        evidence = SOURCE.parents[5]/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025'
        raw = json.loads((evidence/'carrier-Netgen-exact-002/assessment.json').read_text())
        candidate = json.loads((evidence/'carrier-Netgen-appended-exact-001/assessment.json').read_text())
        self.assertEqual(raw['status'], 'volume_screen_refused')
        self.assertGreater(raw['indexed_connectivity']['nonmanifold_faces'], 0)
        self.assertEqual(candidate['status'], 'full_exact_orientation_and_indexed_volume_screens_passed')
        self.assertEqual(candidate['exact_orientation']['negative'], 0)
        self.assertEqual(candidate['exact_orientation']['zero'], 0)
        self.assertTrue(candidate['indexed_connectivity']['boundary_matches'])
        self.assertAlmostEqual(raw['exact_orientation']['total_signed_volume_mm3_float'],
                               2*candidate['exact_orientation']['total_signed_volume_mm3_float'], places=8)
        self.assertFalse(candidate['mechanical_mesh_admitted'])

    def test_reindexing_and_reversed_faces_preserve_geometry(self):
        vertices = np.array([[0., 0, 0], [1., 0, 0], [1., 1, 0], [0., 1, 0]])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        permutation = np.array([3, 1, 0, 2])
        inverse = np.argsort(permutation)
        self.assertEqual(module.boundary_coordinates(vertices, faces),
                         module.boundary_coordinates(vertices[permutation], inverse[faces[::-1, ::-1]]))

    def test_same_counts_with_changed_diagonal_or_moved_point_are_refused(self):
        vertices = np.array([[0., 0, 0], [1., 0, 0], [1., 1, 0], [0., 1, 0]])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        baseline = module.boundary_coordinates(vertices, faces)
        self.assertNotEqual(baseline, module.boundary_coordinates(vertices, np.array([[0, 1, 3], [1, 2, 3]])))
        changed = vertices.copy()
        changed[0, 2] = 1e-12
        self.assertNotEqual(baseline, module.boundary_coordinates(changed, faces))

    def test_appended_extraction_requires_every_original_cell_and_coordinate(self):
        spec = importlib.util.spec_from_file_location('netgen_extraction', SOURCE.with_name('extract_appended_netgen.py'))
        extraction = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extraction)
        v = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0], [0, 0, 1.]])
        t = np.array([[0, 1, 2, 3]])
        f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        combined = np.vstack([t, t])
        result = extraction.extract((v, t, f), (v.copy(), combined, f.copy()))
        np.testing.assert_array_equal(result[1], t)
        changed = v.copy()
        changed[0, 0] = 1e-12
        with self.assertRaises(ValueError):
            extraction.extract((v, t, f), (changed, combined, f))
        with self.assertRaises(ValueError):
            extraction.extract((v, t, f), (v, combined[:, ::-1], f))

    def test_distance_transfer_refuses_reversed_winding_and_tiny_surface_movement(self):
        spec = importlib.util.spec_from_file_location('remeshed_quadratic', SOURCE.with_name('prepare_remeshed_quadratic.py'))
        conversion = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conversion)
        v = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0]])
        f = np.array([[0, 1, 2]])
        record = dict(whole_surface_reference_distance_upper_mm=.059,
                      complete_corner_transport_L1_bound_mm='1/1000000000')
        bound = conversion.inherited_bound(v, np.array([[1, 2, 0]]), v, f, record)
        self.assertGreaterEqual(bound, .059000001)
        with self.assertRaises(ValueError):
            conversion.inherited_bound(v, f[:, ::-1], v, f, record)
        changed = v.copy()
        changed[0, 2] = 1e-12
        with self.assertRaises(ValueError):
            conversion.inherited_bound(changed, f, v, f, record)


if __name__ == '__main__':
    unittest.main()
