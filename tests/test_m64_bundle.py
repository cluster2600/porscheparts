"""Pure offline bundle checks; no provider, GPU or solver execution."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/remote-simready/prepare_bundle.py"
SPEC = importlib.util.spec_from_file_location("m64_bundle", SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "m64-test"
        self.skill = self.base / "upstream-skill"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text("Synthetic skill fixture, never used to execute NVIDIA")
        (self.skill / "example.py").write_text("# synthetic code\n")
        self.assembly = self.base / "assembly.step"
        self.assembly.write_text("synthetic STEP fixture, not geometry")
        self.context = self.base / "context.json"
        self.context.write_text(json.dumps({"manufacturing_authorized": False,
                                            "source_step_sha256": M.digest(self.assembly)}))
        self.prompt = self.base / "prompt.txt"
        self.prompt.write_text("Synthetic non-secret test context")

    def prepare(self):
        return M.prepare(self.root, self.assembly, self.skill, self.context, self.prompt, self.prompt)

    def test_prepare_snapshots_and_hashes_complete_code(self):
        result = self.prepare()
        self.assertFalse(result["cloud_instance_created"])
        code = json.loads((self.root / "code-manifest.json").read_text())
        entries = {x["path"]: x for x in code["files"]}
        self.assertIn("phases/preflight.py", entries)
        self.assertIn("phases/profile-initial.py", entries)
        self.assertEqual(entries["skill/example.py"]["sha256"], M.digest(self.skill / "example.py"))
        self.assertEqual(result["assembly_sha256"], M.digest(self.assembly))
        self.assertEqual((self.root / "inputs/assembly.step").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_context_cannot_identify_a_different_step(self):
        self.context.write_text(json.dumps({"manufacturing_authorized": False, "source_step_sha256": "0" * 64}))
        with self.assertRaisesRegex(ValueError, "different STEP"):
            self.prepare()

    def test_hidden_or_symlink_skill_source_is_refused(self):
        (self.skill / "extra.py").symlink_to(self.assembly)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.prepare()

    def test_bound_identity_deadline_and_budget(self):
        self.prepare()
        now = int(time.time())
        image = "ghcr.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:" + "a" * 64
        with self.assertRaisesRegex(ValueError, "allocation"):
            M.bind(self.root, 123, "test", image, now, now + 7200, 1, 2.5)
        result = M.bind(self.root, 123, "test", image, now, now + 7200, 6, 2.5)
        self.assertFalse(result["cloud_instance_created"])
        manifest = json.loads((self.root / "job-manifest.json").read_text())
        self.assertEqual(manifest["instance_id"], 123)
        self.assertIn("results/wrapper", [x["path"] for x in manifest["outputs"]])
        self.assertLessEqual(sum(x["max_bytes"] for x in manifest["outputs"]), 128 * 1024 * 1024)
        with self.assertRaisesRegex(ValueError, "already bound"):
            M.bind(self.root, 456, "other", image, now, now + 7200, 6, 2.5)


if __name__ == "__main__":
    unittest.main()
