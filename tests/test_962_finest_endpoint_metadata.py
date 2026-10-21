"""An absent optional Tmpfs key must use index lookup while preserving all else."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/run_finest_endpoint_metadata.py"
SPEC = importlib.util.spec_from_file_location("finest_metadata_companion", PATH)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class OptionalTmpfsMetadata(unittest.TestCase):
    def test_absent_key_uses_only_index_substitution_and_core_inspect_retains_null(self):
        self.assertEqual(M.CORRECTED_FORMAT, M.ORIGINAL_FORMAT.replace(M.OLD, M.NEW))
        self.assertEqual(M.CORRECTED_FORMAT.count(M.NEW), 1)
        self.assertNotIn(M.OLD, M.CORRECTED_FORMAT)
        host = {"Memory": 536870912}  # Docker may omit Tmpfs entirely.
        def query(argv, **_kwargs):
            self.assertEqual(argv[:3], ["docker", "inspect", "owned-id"])
            self.assertEqual(argv[-1], M.CORRECTED_FORMAT)
            # Mock documented index-missing semantics, not a native Go/Docker test.
            return subprocess.CompletedProcess(argv, 0, json.dumps(dict(
                Id="owned-id", Controls=dict(Memory=host["Memory"], Tmpfs=host.get("Tmpfs")))), "")
        calls = []
        with patch.object(M.CORE, "INSPECT", M.CORRECTED_FORMAT), patch.object(M.CORE.subprocess, "run", side_effect=query):
            metadata = M.CORE.inspect("owned-id", calls)
        self.assertIs(metadata["Controls"]["Tmpfs"], None)
        self.assertEqual(metadata["Controls"]["Memory"], 536870912)
        self.assertEqual(json.loads(calls[0]["stdout"]), metadata)
        self.assertEqual(M.CORE.INSPECT, M.ORIGINAL_FORMAT)

    def test_existing_output_refusal_preserves_old_companion_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root/"old-output"; output.mkdir()
            sentinel = output/"metadata-companion-executed.py"; sentinel.write_bytes(b"immutable old evidence")
            child = root/"child.json"
            child.write_text(json.dumps(dict(phase="fixtures", root_authorized=True,
                                             metadata_companion=M.companion_binding())))
            with patch.object(M.CORE, "run") as native:
                with self.assertRaisesRegex(ValueError, "Existing fixture output preserved"):
                    M.run(child, M.CORE.digest(child), output)
            native.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b"immutable old evidence")


if __name__ == "__main__":
    unittest.main()
