"""Independent inter-walk input and owned-controller shutdown controls."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/research/935-interwalk-admission-20261106/source'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ControllerTests(unittest.TestCase):
    def exercise(self, number=None, ignore=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ready, report = root / 'ready.json', root / 'phase-report.json'
            script = ('import os,json,signal,time,pathlib; '
                      + ('signal.signal(signal.SIGTERM,signal.SIG_IGN); ' if ignore else '')
                      + f'pathlib.Path({str(ready)!r}).write_text(json.dumps(dict(pid=os.getpid()))); '
                      + ('time.sleep(120)' if number else f'pathlib.Path({str(report)!r}).write_text("{{}}")'))
            plan = root / 'plan.json'
            plan.write_text(json.dumps(dict(schema='935-local-source-delivery-1', inputs=[],
                phases=[dict(name='fixture', command=[sys.executable, '-B', '-c', script],
                             expected_report=str(report))])))
            output = root / 'execution'
            child = subprocess.Popen([sys.executable, '-B', str(SOURCE/'run_local_delivery_v2.py'),
                                      '--plan', str(plan), '--output', str(output)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            phase_pid = None
            try:
                deadline = time.monotonic()+8
                while not ready.exists():
                    self.assertIsNone(child.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.02)
                phase_pid = json.loads(ready.read_text())['pid']
                if number:
                    child.send_signal(number)
                code = child.wait(timeout=12)
                receipt = json.loads((output/'execution.json').read_text())
                self.assertEqual(receipt['complete'], number is None)
                self.assertTrue(receipt['all_owned_children_reaped'])
                self.assertEqual(receipt['requested_signals'], [number] if number else [])
                self.assertEqual(code == 0, number is None)
                self.assertEqual(receipt['phases'][0]['successful'], number is None)
                if number:
                    self.assertEqual(receipt['phases'][0]['stop_reason'], 'external_signal_'+str(number))
                with self.assertRaises(ProcessLookupError):
                    os.kill(phase_pid, 0)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
                if phase_pid is not None:
                    try:
                        os.killpg(phase_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_success(self):
        self.exercise()

    def test_sigterm_reaps_phase_and_writes_failure(self):
        self.exercise(signal.SIGTERM)

    def test_sigint_reaps_phase_and_writes_failure(self):
        self.exercise(signal.SIGINT)

    def test_sigterm_escalates_for_ignoring_phase(self):
        self.exercise(signal.SIGTERM, ignore=True)


class InputAdmissionTests(unittest.TestCase):
    def test_annular_wall_scope_and_topology_controls(self):
        import numpy as np
        checker = module('verify_interwalk_pairs')
        # Use the actual unchanged scalar predicate and its documented bounds.
        scalar_path = ROOT / 'docs/research/935-untried-acquired-pairs-20261106/source/verify_opposed_skins_v2.py'
        scalar = checker.module(str(scalar_path), 'test_scalar_material')
        bounds = dict(maximum_cross_endpoint_distance_nominal_mm=.5, maximum_tangent_dot=-.8,
                      maximum_opposed_skin_normal_dot=-.8, maximum_material_side_gap_dot=-.8,
                      minimum_outward_binormal_dot=.8, minimum_forward_wall_normal_dot=.8)
        result = checker.controls(bounds, scalar)
        self.assertEqual(result['annular_opposed_pairs'], 16)
        self.assertTrue(all(v for v in result.values()))

    def test_grid_matches_complete_enumeration(self):
        import numpy as np
        checker = module('verify_interwalk_pairs')
        points = np.random.default_rng(935).uniform(-1, 1, (100, 3))
        expected = np.array([(a, b) for a in range(100) for b in range(a+1, 100)
                             if np.sum((points[a]-points[b])**2) <= .25], dtype=np.int64)
        actual = checker.cell_radius_pairs(points, np.arange(100), .5, 10000)
        self.assertTrue(np.array_equal(actual, expected))
        with self.assertRaises(AssertionError):
            checker.cell_radius_pairs(points, np.arange(100), .5, 1)
        with self.assertRaises(AssertionError):
            checker.cell_radius_pairs(points, np.arange(100), 1., 10000)

    def test_dual_and_vertex_components_agree_on_disconnected_shells(self):
        import numpy as np
        checker = module('verify_interwalk_pairs')
        producer = module('census_interwalk_pairs')
        helper = checker.module(str(ROOT / 'docs/research/935-retained-boundaries-20261106/source/audit_retained_boundaries.py'), 'test_topology_helper')
        tetra = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        faces = np.concatenate((tetra, tetra+4))
        boundary = checker.fixture_boundary(faces)
        labels_a, cert_a = producer.surface_components(faces, 9, boundary, helper)
        labels_b, cert_b = checker.vertex_components(faces, 9, boundary)
        self.assertTrue(np.array_equal(labels_a, labels_b))
        self.assertTrue(np.array_equal(cert_a, cert_b))
        self.assertEqual(cert_a.tolist(), [[4, 6, 4, 0, 2, 0]]*2)

    def test_different_walk_does_not_authorize_component_fusion(self):
        checker = module('verify_interwalk_pairs')
        self.assertEqual(checker.scope_reason(0, 1, [0, 1], [0, 0]), 'different_walks_same_component')
        self.assertEqual(checker.scope_reason(0, 1, [0, 1], [0, 1]), 'separate_components')
        self.assertEqual(checker.scope_reason(0, 1, [0, 0], [0, 0]), 'same_walk')


class VersionedRegistryTests(unittest.TestCase):
    def test_append_and_independent_registry_fields(self):
        import numpy as np
        producer = module('record_interwalk_pairs')
        checker = module('verify_interwalk_registry')
        keys = np.arange(12).reshape(2, 6)
        previous = producer.append(None, keys[:1], np.ones(1, dtype=np.int8), 1, 'a'*64, 'b'*64, 'c'*64)
        current = producer.append(previous, keys[1:], np.ones(1, dtype=np.int8), 3, 'd'*64, 'e'*64, 'f'*64)
        initial = np.arange(1705*6).reshape(1705, 6)+100
        old_history = np.concatenate((initial, keys[:1]))
        next_history = np.concatenate((initial, keys))
        checker.inspect(previous, current, keys[1:], np.ones(1, dtype=np.int8), 3,
                        'd'*64, 'e'*64, 'f'*64, old_history, next_history)
        self.assertEqual(current['global_pair_ids'].tolist(), [0, 1])
        broken = dict(current)
        broken['birth_rounds'] = current['birth_rounds'].copy()
        broken['birth_rounds'][0] = 99
        with self.assertRaises(AssertionError):
            checker.inspect(previous, broken, keys[1:], np.ones(1, dtype=np.int8), 3,
                            'd'*64, 'e'*64, 'f'*64, old_history, next_history)


class TwoWalkIncidenceTests(unittest.TestCase):
    def test_exact_two_walks_retain_winding_and_origin_guards(self):
        import numpy as np
        builder = module('build_interwalk_strips')
        checker = module('verify_interwalk_pairs')
        helper = checker.module(str(ROOT / 'docs/research/935-retained-boundaries-20261106/source/audit_retained_boundaries.py'), 'two_walk_table')
        faces = np.array([[0, 1, 4], [2, 3, 5]])
        patch = np.array([[1, 0, 3], [1, 3, 2]])
        edges, order, first, codes, uses = helper.table(faces, 6)
        boundary = checker.fixture_boundary(faces)
        bedges = boundary['boundary']
        bc = bedges.min(axis=1)*6+bedges.max(axis=1)
        sort = np.argsort(bc)
        curves = np.array([0 if owner == 0 else 1 for owner in boundary['owners']])
        boundary['edge_origin_kind'] = np.ones(len(bedges), dtype=np.int8)
        def inspect(triangles, allowed):
            return builder.incidence_changes(triangles, 6, codes, uses, edges[order[first]],
                bc[sort], sort, boundary, curves, allowed)
        self.assertIsNotNone(inspect(patch, [0, 1]))
        self.assertIsNone(inspect(patch, 0))
        self.assertIsNone(inspect(patch, 1))
        self.assertIsNone(inspect(patch[:, ::-1], [0, 1]))
        boundary['edge_origin_kind'][np.flatnonzero(np.all(bedges == [2, 3], axis=1))[0]] = 9
        self.assertIsNone(inspect(patch, [0, 1]))


if __name__ == '__main__':
    unittest.main()
