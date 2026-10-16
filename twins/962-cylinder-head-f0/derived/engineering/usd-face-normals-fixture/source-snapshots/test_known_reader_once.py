"""Mocked one-off timeout/interruption cleanup; no native processes."""
import hashlib, importlib.util, json, signal, subprocess, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("known_reader_once", HERE / "run_known_reader_once.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


class KnownReaderLauncherTest(unittest.TestCase):
    def test_timeout_and_interruption_kill_owned_group_and_reap(self):
        for failure in [subprocess.TimeoutExpired("mock", 35), KeyboardInterrupt()]:
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); output = root / "step"
                interpreter = root / "python"; interpreter.write_bytes(b"mock interpreter")
                derivative = root / "tiny.usdc"; derivative.write_bytes(b"mock derivative")
                source = ROOT / "work/962-engineering/usd-normals-native-fixture-prep-001/source.usda"
                expected = source.with_name("expected-arrays.json")
                core = ROOT / "twins/962-cylinder-head-f0/source/run_usd_normal_step.py"
                reader = HERE / "read_known_fixture.py"
                paths = [Path(module.__file__).resolve(), Path(__file__).resolve(), core,
                         reader, interpreter, source, derivative, expected]
                pins = {str(p): sha(p) for p in paths}
                argv = [str(interpreter), "-B", str(reader), str(source), str(derivative),
                        str(expected), str(output / "readback-report.json"), "--source-sha256",
                        module.SOURCE_SHA, "--derivative-sha256", pins[str(derivative)],
                        "--expected-sha256", module.EXPECTED_SHA]
                d = {"root_reviewed": True, "peer_reviewed": True, "execution_authorized": True,
                     "not_after_epoch": time.time() + 60, "core": str(core), "reader": str(reader),
                     "test": str(Path(__file__).resolve()), "interpreter": str(interpreter),
                     "source": str(source), "derivative": str(derivative), "expected": str(expected),
                     "owned_root": str(root), "step_dir": str(output), "pins": pins,
                     "property_assignment_intent": "skip", "argv": argv,
                     "environment": {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                        "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
                        "PYTHONDONTWRITEBYTECODE": "1"}}
                child = root / "child.json"; child.write_text(json.dumps(d))
                worker = SimpleNamespace(pid=43210, returncode=None, kill=mock.Mock()); calls = []
                def wait(timeout):
                    calls.append(timeout)
                    if len(calls) == 1:
                        raise failure
                    worker.returncode = -9
                    return -9
                worker.wait = wait
                handlers = {s: signal.getsignal(s) for s in [signal.SIGINT, signal.SIGTERM]}
                with mock.patch.object(module.subprocess, "Popen", return_value=worker) as popen, \
                        mock.patch.object(module.os, "killpg") as killpg:
                    result = module.execute(child, sha(child))
                    killpg.assert_called_once_with(worker.pid, signal.SIGKILL)
                    self.assertEqual(popen.call_args.args[0], argv)
                    self.assertTrue(popen.call_args.kwargs["start_new_session"])
                self.assertLessEqual(calls[0], 35); self.assertEqual(calls[1], 5)
                self.assertEqual(result["native_returncode"], -9)
                self.assertEqual(result["error"]["type"], type(failure).__name__)
                self.assertTrue(result["cleanup"]["worker_reaped"])
                self.assertTrue(result["all_pins_unchanged"])
                self.assertFalse(result["known_array_result_assessed"])
                self.assertEqual({s: signal.getsignal(s) for s in handlers}, handlers)
                self.assertTrue((output / "execution.json").is_file())


if __name__ == "__main__":
    unittest.main()
