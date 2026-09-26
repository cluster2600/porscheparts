"""Trust-boundary tests only: no candidate solve and no platform monkeypatch."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import candidate as c


def passed():
    return dict(classification='native_arm64_macOS_CPU_reference_pilot_not_G13_Linux_GPU_qualification',
        error=None, complete=True, all_native_CPU_comparisons_passed=True,
        dynamic_libraries_verified_before=True, dynamic_libraries_verified_after=True,
        CUDA_executed=False, G13_Linux_reference_promoted=False,
        rows=[dict(id=ident, direction=direction, passed=True, compared=True, threads=1,
            direct=dict(threads=1, observed_cpu_counts=[1], exit_code=0, thread_environment={k:'1' for k in c.reference.THREAD_KEYS}),
            mechanics=dict(equilibrium_passed=True, force_balance_relative_error=1e-6, moment_balance_F_times_100mm_error=1e-6),
            agreement=dict(max_nodal_difference_over_max_reference_U=1e-6, printed_dat_rounding_residual_bound=1e-5,
                           printed_dat_relative_residual=1e-6)) for ident, direction in c.PLAN],
        references={n:dict(passed=True, solver=dict(backend='cpu', info=0, dtype='float64'), relative_residual=1e-9)
                    for n in ('x','minus_z')})


class NativeCandidateTrust(unittest.TestCase):
    def test_success_flags_do_not_replace_plan_numeric_or_dependency_guards(self):
        c.require_passed_summary(passed())
        for mutate in (lambda r:r.update(complete=False), lambda r:r.update(dynamic_libraries_verified_after=False),
                lambda r:r['rows'].pop(), lambda r:r['rows'][0]['mechanics'].update(force_balance_relative_error=float('nan')),
                lambda r:r['rows'][0]['direct'].update(observed_cpu_counts=[4]),
                lambda r:r['references']['x']['solver'].update(backend='cuda')):
            value=copy.deepcopy(passed()); mutate(value)
            with self.assertRaises(ValueError):
                c.require_passed_summary(value)

    def test_missing_actual_reference_stops_before_output_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            args=SimpleNamespace(reference=root/'missing-summary.json', output=root/'must-not-exist')
            with patch.object(c.subprocess, 'Popen') as spawn:
                with self.assertRaises((FileNotFoundError, ValueError)):
                    c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())


if __name__ == '__main__':
    unittest.main()
