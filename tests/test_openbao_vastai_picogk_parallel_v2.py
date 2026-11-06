"""A failed inventory read must not destroy an otherwise verified owned job."""
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
import subprocess
import unittest
from unittest import mock
import test_openbao_vastai_picogk as baseline
import test_openbao_vastai_picogk_parallel as parallel


class ParallelGuardV2Tests(unittest.TestCase):
    def setUp(self):
        fixture = parallel.ParallelLeaseTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.manifest = fixture.manifest
        self.path = fixture.path
        self.own = fixture.w.safe_instance(fixture.raw)
        self.guard = baseline.load(
            'deploy/vast/picogk-parallel/deadline_guard_v2.py', 'parallel_guard_v2')
        self.wrapper = self.root / 'approved-wrapper'
        self.wrapper.write_text('# never executed\n')
        self.proof = dict(instance_id=999, destroyed=True, verified_absent=True)

    def exercise(self, responses, monotonic=None):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(redirect_stdout(io.StringIO()))
        stack.enter_context(mock.patch.object(self.guard, 'WRAPPER', self.wrapper))
        stack.enter_context(mock.patch.object(self.guard.time, 'sleep'))
        stack.enter_context(mock.patch.object(
            self.guard.time, 'monotonic', side_effect=monotonic or (lambda: 0)))
        calls = stack.enter_context(mock.patch.object(
            self.guard, 'wrapper_call', side_effect=responses))
        cleanup = stack.enter_context(mock.patch.object(
            self.guard, 'cleanup_until_absent', return_value=self.proof))
        return calls, cleanup

    def test_exact_show_recovers_one_failed_inventory_read(self):
        calls, cleanup = self.exercise(
            [[], [self.own], OSError('transport'), self.own, []])
        result = self.guard.guard(self.path)
        self.assertEqual(result['reason'], 'already_destroyed')
        cleanup.assert_called_once_with(999, self.manifest)
        self.assertIn(mock.call('show', '999', timeout_seconds=30),
                      calls.call_args_list)

    def test_one_dual_read_failure_recovers_without_early_cleanup(self):
        calls, cleanup = self.exercise(
            [[], [self.own], OSError('inventory'), OSError('show'), [self.own], []])
        result = self.guard.guard(self.path)
        self.assertEqual(result['reason'], 'already_destroyed')
        cleanup.assert_called_once_with(999, self.manifest)
        self.assertEqual(len(calls.call_args_list), 6)

    def test_three_dual_failures_trigger_exact_owned_cleanup(self):
        _, cleanup = self.exercise(
            [[], [self.own], *[OSError('read') for _ in range(6)]])
        result = self.guard.guard(self.path)
        self.assertEqual(result['reason'],
                         'owned_monitor_reads_failed_after_bounded_retries')
        cleanup.assert_called_once_with(999, self.manifest)

    def test_changed_owned_identity_is_never_retried_or_deleted(self):
        calls, cleanup = self.exercise(
            [[], [self.own], OSError('inventory'),
             {**self.own, 'image': 'changed-image'}])
        with self.assertRaises(self.guard.GuardError):
            self.guard.guard(self.path)
        cleanup.assert_not_called()
        self.assertEqual(len(calls.call_args_list), 4)

    def test_fallback_retains_immediate_cost_rejection(self):
        _, cleanup = self.exercise(
            [[], [self.own], OSError('inventory'), {**self.own, 'dph_total': .9}])
        result = self.guard.guard(self.path)
        self.assertEqual(result['reason'], 'contract_or_cost_guard')
        cleanup.assert_called_once_with(999, self.manifest)

    def test_deadline_during_read_failure_prevents_another_monitor_rpc(self):
        clock = [0]
        count = [0]

        def response(*args, **kwargs):
            count[0] += 1
            if count[0] == 1:
                return []
            if count[0] == 2:
                return [self.own]
            clock[0] = 10**9
            raise OSError('read reaches deadline')

        calls, cleanup = self.exercise(response, monotonic=lambda: clock[0])
        result = self.guard.guard(self.path)
        self.assertEqual(result['reason'], 'deadline_cleanup_reserve')
        self.assertFalse(any(c.args[0] == 'show' for c in calls.call_args_list))
        cleanup.assert_called_once_with(999, self.manifest)

    def test_dual_read_grace_cannot_overrun_ninety_seconds(self):
        clock, count, first_failure = [0], [0], []

        def response(*args, **kwargs):
            count[0] += 1
            if count[0] == 1:
                return []
            if count[0] == 2:
                return [self.own]
            if not first_failure:
                first_failure.append(clock[0])
            clock[0] += kwargs['timeout_seconds']
            raise OSError('bounded transport timeout')

        _, cleanup = self.exercise(response, monotonic=lambda: clock[0])
        with mock.patch.object(self.guard.time, 'sleep',
                               side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            result = self.guard.guard(self.path)
        self.assertEqual(result['reason'],
                         'owned_monitor_reads_failed_after_bounded_retries')
        self.assertLessEqual(clock[0] - first_failure[0], 90)
        cleanup.assert_called_once_with(999, self.manifest)

    def test_wrapper_read_timeout_is_explicit_and_bounded(self):
        result = subprocess.CompletedProcess([], 0, stdout=b'[]', stderr=b'')
        with mock.patch.object(self.guard.subprocess, 'run', return_value=result) as run:
            self.assertEqual(self.guard.wrapper_call('instances', timeout_seconds=7), [])
        self.assertEqual(run.call_args.kwargs['timeout'], 7)
        for value in (0, 181, True):
            with self.assertRaises(self.guard.GuardError):
                self.guard.wrapper_call('instances', timeout_seconds=value)


if __name__ == '__main__':
    unittest.main()
