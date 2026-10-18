"""Mocked process cleanup and before-output drift; no subprocess or USD run."""
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "usd_normal_step", ROOT / "twins/962-cylinder-head-f0/source/run_usd_normal_step.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class NormalStepTests(unittest.TestCase):
    def child(self, root):
        interpreter = root / "python"; interpreter.write_bytes(b"mock-only interpreter")
        script = ROOT / "twins/962-cylinder-head-f0/source/author_usd_face_normals.py"
        source = root / "source.usda"; source.write_bytes(b"mock-only input")
        preflight = root / "preflight.json"; preflight.write_text('{"status":"ready"}')
        snapshots = [str(Path(module.__file__).resolve()), str(Path(__file__).resolve()), str(script)]
        paths = snapshots + [str(interpreter), str(source), str(preflight)]
        child = {"root_reviewed": True, "peer_reviewed": True, "execution_authorized": True,
                 "not_after_epoch": time.time() + 60, "stage": "author",
                 "owned_root": str(root), "step_dir": str(root / "step"),
                 "controller_test": str(Path(__file__).resolve()), "interpreter": str(interpreter),
                 "script": str(script), "input_paths": [str(source), str(preflight)],
                 "snapshot_paths": snapshots, "pins": {p: module.sha(p) for p in paths},
                 "args": ["author", str(source), str(root / "step/derivative.usdc")],
                 "environment": {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                    "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
                    "PYTHONDONTWRITEBYTECODE": "1", "PHYSICAL_AI_REQUIRE_PREFLIGHT": "1",
                    "PHYSICAL_AI_PREFLIGHT_MANIFEST": str(preflight)},
                 "property_assignment_intent": "skip"}
        path = root / "child.json"; path.write_text(json.dumps(child))
        return path, child

    def test_pin_drift_refuses_before_output_or_process_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, child = self.child(Path(temporary)); expected = module.sha(path)
            Path(child["interpreter"]).write_bytes(b"drift")
            with mock.patch.object(module.subprocess, "Popen") as popen:
                with self.assertRaisesRegex(ValueError, "drift before output creation"):
                    module.execute(path, expected)
                popen.assert_not_called()
            self.assertFalse(Path(child["step_dir"]).exists())

    def test_timeout_interruption_and_setup_refusals_retain_cleanup(self):
        for failure in [subprocess.TimeoutExpired("mock", 90), KeyboardInterrupt(), OSError("setup")]:
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as temporary:
                path, child = self.child(Path(temporary))
                worker = SimpleNamespace(pid=43210, returncode=None, kill=mock.Mock())
                calls = []
                def wait(timeout):
                    calls.append(timeout)
                    if len(calls) == 1:
                        raise failure
                    worker.returncode = -9
                    return -9
                worker.wait = wait
                old = {s: signal.getsignal(s) for s in [signal.SIGINT, signal.SIGTERM]}
                with mock.patch.object(module.subprocess, "Popen", return_value=worker) as popen, \
                        mock.patch.object(module.os, "killpg") as killpg:
                    if isinstance(failure, OSError):
                        popen.side_effect = failure
                    result = module.execute(path, module.sha(path))
                    if isinstance(failure, OSError):
                        killpg.assert_not_called(); self.assertIsNone(result["native_returncode"])
                    else:
                        killpg.assert_called_once_with(worker.pid, signal.SIGKILL)
                        self.assertTrue(result["cleanup"]["worker_reaped"])
                        self.assertEqual(result["native_returncode"], -9)
                        self.assertEqual(calls[1], 5)
                        self.assertLessEqual(calls[0], 90)
                    self.assertTrue(popen.call_args.kwargs["start_new_session"])
                    self.assertEqual(popen.call_args.kwargs["env"], child["environment"])
                self.assertEqual({s: signal.getsignal(s) for s in old}, old)
                self.assertEqual(result["error"]["type"], type(failure).__name__)
                self.assertTrue(result["all_pins_unchanged"])
                self.assertFalse(result["stage_result_assessed"])
                self.assertFalse(result["physical_or_manufacturing_qualification"])
                output = Path(child["step_dir"])
                self.assertTrue((output / "execution.json").is_file())
                self.assertEqual(module.sha(output / "frozen-child.json"), module.sha(path))


if __name__ == "__main__":
    unittest.main()
