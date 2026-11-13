"""Offline checks of the private-release backup tool (no network, no gh)."""
import os
import runpy
import tempfile
import time
import unittest
from pathlib import Path

TOOL = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/private_release_backup.py"))


class PrivateReleaseBackupTests(unittest.TestCase):
    def test_collect_skips_excluded_and_recent_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp)
            (src / "private/stack-c").mkdir(parents=True)
            old = time.time() - 3600
            for rel in ("private/a.stl", "private/stack-c/band.npz", "private/fresh.json"):
                (src / rel).write_bytes(b"x" * 10)
            for rel in ("private/a.stl", "private/stack-c/band.npz"):
                os.utime(src / rel, (old, old))
            (src / "private/link.stl").symlink_to("a.stl")
            files, skipped, links = TOOL["collect"](src, ["private"], ["private/stack-c"], 900, time.time())
            self.assertEqual([f["path"] for f in files], ["private/a.stl"])
            self.assertEqual(links, [{"path": "private/link.stl", "target": "a.stl"}])
            self.assertEqual({s["path"]: s["reason"] for s in skipped}, {
                "private/stack-c/band.npz": "excluded by prefix",
                "private/fresh.json": "modified during the quiet window",
            })
            with self.assertRaises(FileNotFoundError):
                TOOL["collect"](src, ["missing"], [], 0, time.time())

    def test_batches_respect_the_part_limit_and_keep_every_file(self):
        files = [{"path": f"f{i}", "size": s} for i, s in enumerate([700, 600, 500, 400, 300])]
        groups = TOOL["batches"](files, 1000)
        self.assertTrue(all(sum(f["size"] for f in g) <= 1000 for g in groups))
        self.assertEqual(sorted(f["path"] for g in groups for f in g), sorted(f["path"] for f in files))
        with self.assertRaises(ValueError):
            TOOL["batches"]([{"path": "huge", "size": 1001}], 1000)


if __name__ == "__main__":
    unittest.main()
