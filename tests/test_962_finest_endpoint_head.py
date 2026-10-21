"""A changed source must be refused before creating outputs or native workers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/run_finest_endpoint_head.py"
SPEC = importlib.util.spec_from_file_location("finest_endpoint_head", PATH)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class HeadDriftRefusal(unittest.TestCase):
    def test_drift_stops_before_output_creation_or_native_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/"original.bin"; source.write_bytes(b"declared original")
            pins = {"original.bin": M.BOUNDED.digest(source)}
            contract = root/"child.json"; contract.write_text("{}\n")
            expected = M.BOUNDED.digest(contract)
            source.write_bytes(b"changed after freeze")
            output = root/"work/962-engineering/head-attempt"
            with patch.object(M, "ROOT", root), patch.object(M, "reviewed_child", return_value=({}, pins)), \
                    patch.object(M.BOUNDED, "execute") as native:
                with self.assertRaisesRegex(ValueError, "before output creation"):
                    M.run(contract, expected, output)
            self.assertFalse(output.exists())
            native.assert_not_called()
            self.assertEqual(source.read_bytes(), b"changed after freeze")

    def test_head_delegates_deadline_cleanup_and_restores_attributed_metadata_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); source = root/"original.bin"; source.write_bytes(b"declared original")
            pins = {"original.bin": M.BOUNDED.digest(source)}
            child = root/"child.json"; child.write_text("{}\n")
            output = root/"work/962-engineering/head-attempt"; identifier = "d"*64
            metadata = {}; calls = []; process = Mock(pid=12345, returncode=None)
            process.poll.return_value = None
            def command(argv, **_kwargs):
                calls.append(argv)
                if argv[1] == "create":
                    mounts = []
                    for i, value in enumerate(argv):
                        if value == "--mount":
                            parts = argv[i+1].split(","); fields = dict(v.split("=", 1) for v in parts if "=" in v)
                            mounts.append(dict(Type="bind", Source=fields["src"], Destination=fields["dst"], RW="readonly" not in parts))
                    metadata.update(Id=identifier, Owner=argv[argv.index("--label")+1].split("=", 1)[1],
                        Image=M.BOUNDED.IMAGE, Mounts=mounts,
                        Controls=dict(NanoCpus=2000000000, Memory=4294967296, MemorySwap=4294967296,
                                      NetworkMode="none", ReadonlyRootfs=True, Tmpfs=None),
                        State=dict(Status="created", Running=False, Pid=0, ExitCode=0, OOMKilled=False))
                if argv[1] == "inspect":
                    self.assertEqual(argv[-1], M.METADATA.CORRECTED_FORMAT)
                    return subprocess.CompletedProcess(argv, 0, json.dumps(metadata), "")
                if argv[1] == "kill":
                    metadata["State"].update(Status="exited", Running=False, Pid=0, ExitCode=137)
                return subprocess.CompletedProcess(argv, 0, identifier+"\n", "")
            def start(*_args, **_kwargs):
                metadata["State"].update(Status="running", Running=True, Pid=99)
                return process
            def reap(timeout):
                process.returncode = 137; process.poll.return_value = 137
                return 137
            process.wait.side_effect = reap
            with patch.object(M, "ROOT", root), patch.object(M, "reviewed_child", return_value=({}, pins)), \
                    patch.object(M.BOUNDED.subprocess, "run", side_effect=command), \
                    patch.object(M.BOUNDED.subprocess, "Popen", side_effect=start), \
                    patch.object(M.BOUNDED, "monitor", side_effect=TimeoutError("declared deadline")):
                self.assertEqual(M.run(child, M.BOUNDED.digest(child), output), 2)
            self.assertIn(["docker", "kill", identifier], calls)
            self.assertIn(["docker", "rm", identifier], calls)
            process.wait.assert_called_once_with(timeout=10)
            self.assertEqual(M.BOUNDED.INSPECT, M.METADATA.ORIGINAL_FORMAT)
            summary = json.loads((output/"head-execution-summary.json").read_text())
            self.assertIs(summary["native_pass_finished"], False)
            self.assertIs(summary["candidate_surface_admitted"], False)
            self.assertEqual(summary["CUB_or_volume_calls"], 0)
            self.assertEqual(summary["source_attribution"]["metadata_source_sha256"], M.METADATA_SHA)


if __name__ == "__main__":
    unittest.main()
