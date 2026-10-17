"""Mock-only owned-container and absolute-budget checks; no native calls."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().with_name('run_cgal_phase.py')
spec = importlib.util.spec_from_file_location('held_cgal_phase', SOURCE)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
B = M.B


class FakeProcess:
    pid = 4242

    def __init__(self, engine, code):
        self.engine = engine
        self.returncode = code
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.returncode is None:
            self.engine.now = self.engine.wait_finish
            self.returncode = 0
        return self.returncode


class FakeEngine:
    container = 'a'*64
    owner = 'unit-owned-container'

    def __init__(self, setup=10., launch=12., finish=13., already_exited=False,
                 cleanup_finish=None):
        self.now = 0.
        self.setup = setup
        self.launch = launch
        self.wait_finish = finish
        self.already_exited = already_exited
        self.cleanup_finish = cleanup_finish
        self.inspect_calls = 0
        self.process = None
        self.calls = []
        self.controls = {}

    def run(self, command, **_):
        self.calls.append(command)
        if command[:2] == ['docker', 'create']:
            self.now = self.setup
            return SimpleNamespace(returncode=0, stdout=self.container+'\n', stderr='')
        if command == ['docker', 'kill', self.container]:
            self.process.returncode = 137
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        if command == ['docker', 'rm', self.container]:
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        raise AssertionError('Unexpected subprocess call: '+repr(command))

    def inspect(self, reference, calls):
        self.inspect_calls += 1
        if self.cleanup_finish is not None and self.inspect_calls >= 2:
            self.now = self.cleanup_finish
        alive = self.process is not None and self.process.returncode is None
        return dict(Id=self.container, Owner=self.owner, Image=B.IMAGE,
                    State=dict(Running=alive, Pid=4242 if alive else 0,
                               ExitCode=self.process.returncode if self.process else 0,
                               OOMKilled=False), Controls=self.controls, Mounts=[])

    def popen(self, command, **kwargs):
        self.calls.append(command)
        if command != ['docker', 'start', '--attach', self.container]:
            raise AssertionError('Only the owned container may start')
        if kwargs.get('start_new_session') is not True:
            raise AssertionError('Owned attach session required')
        self.now = self.launch
        self.process = FakeProcess(self, 0 if self.already_exited else None)
        return self.process


class CGALControllerTests(unittest.TestCase):
    def execute_fake(self, engine, monitor_error=None):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            with patch.object(B.time, 'monotonic', side_effect=lambda: engine.now), \
                    patch.object(B.subprocess, 'run', side_effect=engine.run), \
                    patch.object(B.subprocess, 'Popen', side_effect=engine.popen) as started, \
                    patch.object(B, 'inspect', side_effect=engine.inspect), \
                    patch.object(B.os, 'killpg') as host_kill:
                if monitor_error is None:
                    result = B.execute(['docker', 'create'], 'fresh-name', engine.owner,
                                       output, 'case', 60, {}, [])
                else:
                    with patch.object(B, 'monitor', side_effect=monitor_error):
                        result = B.execute(['docker', 'create'], 'fresh-name', engine.owner,
                                           output, 'case', 60, {}, [])
            saved = json.loads((output/'case.execution.json').read_text())
            self.assertEqual(saved, result)
            self.assertTrue(result['owned_container_removed'])
            self.assertTrue(result['attach_reaped'])
            self.assertEqual(result['cleanup_errors'], [])
            host_kill.assert_not_called()
            return result, started.call_count

    def test_setup_consumes_budget_refuses_before_popen(self):
        engine = FakeEngine(setup=60.)
        result, starts = self.execute_fake(engine)
        self.assertEqual(starts, 0)
        self.assertFalse(result['attach_process_started'])
        self.assertIn('TimeoutError', result['error'])
        self.assertEqual(result['wall_seconds'], 60.)
        self.assertNotIn(['docker', 'start', '--attach', engine.container], engine.calls)

    def test_already_exited_popen_at_or_after_absolute_deadline_refuses(self):
        for when in (60., 61.):
            with self.subTest(launch=when):
                engine = FakeEngine(launch=when, already_exited=True)
                result, starts = self.execute_fake(engine)
                self.assertEqual(starts, 1)
                self.assertEqual(result['attach_returncode'], 0)
                self.assertIn('TimeoutError', result['error'])
                self.assertEqual(engine.process.wait_calls, [10])

    def test_wait_completes_after_absolute_deadline_refuses(self):
        engine = FakeEngine(finish=61.)
        result, starts = self.execute_fake(engine)
        self.assertEqual(starts, 1)
        self.assertEqual(result['attach_returncode'], 0)
        self.assertIn('TimeoutError', result['error'])
        self.assertEqual(engine.process.wait_calls, [1, 10])

    def test_final_elapsed_latch_refuses_late_cleanup_completion(self):
        engine = FakeEngine(already_exited=True, cleanup_finish=61.)
        result, _ = self.execute_fake(engine)
        self.assertIn('at completion', result['error'])
        self.assertEqual(result['wall_seconds'], 61.)

    def test_normal_owned_job_completes_with_same_setup_started_clock(self):
        engine = FakeEngine()
        result, starts = self.execute_fake(engine)
        self.assertEqual(starts, 1)
        self.assertIsNone(result['error'])
        self.assertEqual(result['wall_seconds'], 13.)
        self.assertEqual(result['attach_returncode'], 0)
        self.assertNotIn(['docker', 'kill', engine.container], engine.calls)

    def test_monitor_exception_kills_reaps_only_verified_owned_id(self):
        engine = FakeEngine()
        result, starts = self.execute_fake(engine, RuntimeError('mock observer failure'))
        self.assertEqual(starts, 1)
        self.assertEqual(result['error'], 'RuntimeError: mock observer failure')
        self.assertEqual(result['attach_returncode'], 137)
        self.assertIn(['docker', 'kill', engine.container], engine.calls)
        self.assertIn(['docker', 'rm', engine.container], engine.calls)
        self.assertEqual(engine.process.wait_calls, [10])

    def test_held_controls_and_changed_pin_refuse_before_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            child = root/'child.json'
            card = dict(input_sha256={}, root_authorized=False, root_and_peer_review_complete=True,
                        phase='head', image_id=B.IMAGE, automatic_retry=False, limits={})
            child.write_text(json.dumps(card))
            with self.assertRaisesRegex(ValueError, 'Reviewed fixed phase'):
                M.validated_child(child, B.digest(child))
            card['root_authorized'] = True
            child.write_text(json.dumps(card))
            with self.assertRaisesRegex(ValueError, 'phase controls changed'):
                M.validated_child(child, B.digest(child))
            source = root/'input'; source.write_bytes(b'old')
            pins = {'input': B.digest(source)}; source.write_bytes(b'changed')
            with patch.object(M, 'ROOT', root), \
                    patch.object(M, 'validated_child', return_value=({}, pins)), \
                    patch.object(B, 'execute') as native:
                output = root/'work/962-engineering/new'
                with self.assertRaisesRegex(ValueError, 'Input drift'):
                    M.run(child, B.digest(child), output)
                self.assertFalse(output.exists())
                native.assert_not_called()

    def test_first_failed_fixture_prevents_second_job_and_restores_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); child = root/'child.json'; child.write_text('{}')
            jobs = [dict(label='fixture-'+str(i), entrypoint='/bounded-distance',
                         arguments=['--literal-'+str(i)], read_only_mounts={}, expected_returncodes=[0])
                    for i in range(4)]
            card = dict(phase='fixtures', jobs=jobs)
            refusal = dict(error='TimeoutError: mock deadline', cleanup_errors=[], attach_reaped=True,
                           owned_container_removed=True, attach_returncode=0,
                           final_metadata=dict(State=dict(ExitCode=0, Running=False, OOMKilled=False)))
            output = root/'work/962-engineering/new'
            with patch.object(M, 'ROOT', root), \
                    patch.object(M, 'validated_child', return_value=(card, {})), \
                    patch.object(B, 'execute', return_value=refusal) as native:
                self.assertEqual(M.run(child, B.digest(child), output), 2)
            self.assertEqual(native.call_count, 1)
            self.assertEqual(B.INSPECT, M.M.ORIGINAL_FORMAT)
            result = json.loads((output/'phase-summary.json').read_text())
            self.assertEqual(len(result['jobs']), 1)
            self.assertFalse(result['procedural_phase_finished'])
            self.assertFalse(result['head_surface_admitted'])


if __name__ == '__main__':
    unittest.main()
