"""No observer/setup interruption may leave a verified owned worker running."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/run_finest_endpoint_preflight.py"
SPEC = importlib.util.spec_from_file_location("finest_endpoint_controller", PATH)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class BoundedOwnedCleanup(unittest.TestCase):
    def test_monitor_failure_deadline_and_interrupt_kill_reap_and_retain_exact_state(self):
        for failure in [RuntimeError("observer failed"), TimeoutError("deadline"), KeyboardInterrupt()]:
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp); identifier = "a"*64; owner = "owned-nonce"
                controls = dict(example="exact reviewed controls"); mounts = [("/input", "/input.bin", False, "bind")]
                state = dict(Status="created", Running=False, Pid=0, ExitCode=0, OOMKilled=False)
                metadata = dict(Id=identifier, Owner=owner, Image=M.IMAGE, State=state, Controls=controls,
                                Mounts=[dict(Source="/input", Destination="/input.bin", RW=False, Type="bind")])
                calls = []
                process = Mock(pid=12345, returncode=None)
                process.poll.return_value = None
                def reaped(timeout):
                    process.returncode = -9; process.poll.return_value = -9
                    return -9
                process.wait.side_effect = reaped
                def start(*_args, **_kwargs):
                    state.update(Status="running", Running=True, Pid=99)
                    return process
                def command(argv, **_kwargs):
                    calls.append(argv)
                    if argv[1] == "create":
                        return subprocess.CompletedProcess(argv, 0, identifier+"\n", "")
                    if argv[1] == "inspect":
                        return subprocess.CompletedProcess(argv, 0, json.dumps(metadata), "")
                    if argv[1] == "kill":
                        state.update(Status="exited", Running=False, Pid=0, ExitCode=137)
                    return subprocess.CompletedProcess(argv, 0, identifier+"\n", "")
                with patch.object(M.subprocess, "run", side_effect=command), \
                        patch.object(M.subprocess, "Popen", side_effect=start), \
                        patch.object(M, "monitor", side_effect=failure):
                    result = M.execute(["docker", "create"], "fresh-owned-name", owner, output, "case", 60, controls, mounts)
                self.assertIn(["docker", "kill", identifier], calls)
                self.assertIn(["docker", "rm", identifier], calls)
                process.wait.assert_called_once_with(timeout=10)
                self.assertIs(result["attach_reaped"], True)
                self.assertIs(result["owned_container_removed"], True)
                self.assertEqual(result["final_metadata"]["State"], state)
                self.assertEqual(result["final_metadata"]["State"]["Running"], False)
                self.assertIn(type(failure).__name__, result["error"])
                self.assertEqual(result["native_log_sha256"], M.digest(output/"case.native.log"))
                self.assertEqual(json.loads((output/"case.execution.json").read_text()), result)

    def test_owned_setup_failure_removes_only_verified_unstarted_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            identifier = "c"*64; calls = []
            metadata = dict(Id=identifier, Owner="ours", Image=M.IMAGE, Controls={}, Mounts=[],
                            State=dict(Status="created", Running=False, Pid=0, ExitCode=0, OOMKilled=False))
            def command(argv, **_kwargs):
                calls.append(argv)
                stdout = json.dumps(metadata) if argv[1] == "inspect" else identifier+"\n"
                return subprocess.CompletedProcess(argv, 0, stdout, "")
            with patch.object(M.subprocess, "run", side_effect=command), \
                    patch.object(M.subprocess, "Popen", side_effect=OSError("attach setup failed")):
                result = M.execute(["docker", "create"], "fresh-name", "ours", Path(tmp), "setup", 60, {}, [])
            self.assertIn(["docker", "rm", identifier], calls)
            self.assertFalse(any(argv[1] == "kill" for argv in calls))
            self.assertIs(result["attach_process_started"], False)
            self.assertIs(result["attach_reaped"], True)
            self.assertEqual(result["final_metadata"]["State"]["Status"], "created")
            self.assertIn("OSError", result["error"])

    def test_setup_refusal_does_not_start_kill_or_remove_foreign_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def command(argv, **_kwargs):
                calls.append(argv)
                if argv[1] == "create":
                    return subprocess.CompletedProcess(argv, 1, "", "name conflict")
                return subprocess.CompletedProcess(argv, 0, json.dumps(dict(
                    Id="b"*64, Owner="somebody-else", Image=M.IMAGE)), "")
            with patch.object(M.subprocess, "run", side_effect=command), \
                    patch.object(M.subprocess, "Popen") as launch:
                result = M.execute(["docker", "create"], "fresh-name", "ours", Path(tmp), "refusal", 60, {}, [])
            launch.assert_not_called()
            self.assertFalse(any(argv[1] in ["kill", "rm"] for argv in calls))
            self.assertIs(result["owned_container_removed"], False)
            self.assertIs(result["attach_process_started"], False)
            self.assertIn("Container creation refused", result["error"])


if __name__ == "__main__":
    unittest.main()
