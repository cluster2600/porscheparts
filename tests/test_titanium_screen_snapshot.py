"""Historical replay remains separate from live fail-closed catalogue screening."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_titanium_screen_snapshot as snapshot


PART_FILE = "993-exh-oval-tip-ti-f1-0001.json"


class TitaniumScreenSnapshotTests(unittest.TestCase):
    def test_actual_historical_replay_passes_without_writing_frozen_files(self):
        before = {path: path.read_bytes() for path in (snapshot.INPUTS, snapshot.SELECTION, snapshot.ZONE_OUTPUT)}
        for mode in ("selection", "pet-zone-triage"):
            with self.subTest(mode=mode):
                result = subprocess.run(
                    [sys.executable, str(snapshot.ROOT / "scripts/check_titanium_screen_snapshot.py"), "--mode", mode],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("44 retained judgements; live catalogue not screened", result.stdout)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    def test_default_live_screen_still_rejects_the_new_unjudged_964_part(self):
        result = subprocess.run([
            sys.executable, str(snapshot.SCREEN), "--output", str(snapshot.SELECTION), "--check",
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("964-CENTRAL-CELL-ASSUMED-F1", result.stderr)
        self.assertIn("ne couvre pas le catalogue", result.stderr)

    def test_missing_or_duplicate_historical_catalogue_part_is_rejected(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as temp:
                catalog = Path(temp) / "catalog"
                shutil.copytree(snapshot.CATALOG, catalog)
                if duplicate:
                    shutil.copyfile(catalog / PART_FILE, catalog / "duplicate.json")
                else:
                    (catalog / PART_FILE).unlink()
                with self.assertRaisesRegex(ValueError, "Duplicate historical" if duplicate else "Missing historical"):
                    snapshot.historical_records(catalog)

    def test_default_live_zone_check_still_refuses_the_changed_catalogue_count(self):
        result = subprocess.run([
            sys.executable, str(snapshot.ZONE_SCREEN), "--output", str(snapshot.ZONE_OUTPUT), "--check",
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("perime:", result.stderr)

    def test_duplicate_historical_ranking_id_is_rejected(self):
        selection = json.loads(snapshot.SELECTION.read_text(encoding="utf-8"))
        selection["ranking"][-1]["part_id"] = selection["ranking"][0]["part_id"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "selection.json"
            path.write_text(json.dumps(selection), encoding="utf-8")
            with patch.object(snapshot, "SELECTION", path):
                with self.assertRaisesRegex(ValueError, "44 unique"):
                    snapshot.historical_records(snapshot.CATALOG)


if __name__ == "__main__":
    unittest.main()
