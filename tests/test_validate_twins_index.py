"""Tests for scripts/validate_twins_index.py (issue #555)."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_twins_index", ROOT / "scripts/validate_twins_index.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def entry(index, name):
    return next(e for e in index["directories"] if e["directory"] == name)


class TwinsIndexTests(unittest.TestCase):
    def setUp(self):
        self.index = json.loads((ROOT / "twins/index.json").read_text(encoding="utf-8"))
        self.readme = (ROOT / "twins/README.md").read_text(encoding="utf-8")

    def errors(self, index=None, **kwargs):
        index = self.index if index is None else index
        readme = kwargs.pop("readme", None)
        if readme is None:
            twins = MODULE.load_records(ROOT, "catalog/twins", "twin_id")
            parts = MODULE.load_records(ROOT, "catalog/parts", "part_id")
            start, stop = self.readme.find(MODULE.BEGIN), self.readme.find(MODULE.END)
            readme = self.readme[:start] + MODULE.render(index, twins, parts) + self.readme[stop + len(MODULE.END):]
        return MODULE.validate(ROOT, index=index, readme=readme, **kwargs)

    def test_repository_index_is_consistent(self):
        self.assertEqual(MODULE.validate(ROOT), [])

    def test_every_twins_directory_is_indexed(self):
        names = [e["directory"] for e in self.index["directories"]]
        self.assertEqual(sorted(names), MODULE.twin_dirs(ROOT))

    def test_new_directory_without_entry_is_refused(self):
        dirs = MODULE.twin_dirs(ROOT) + ["993-new-workstream"]
        self.assertTrue(any("993-new-workstream/ has no entry" in e for e in self.errors(directories=dirs)))

    def test_removed_directory_is_refused(self):
        dirs = [d for d in MODULE.twin_dirs(ROOT) if d != "993-reference-envelope"]
        self.assertTrue(any("does not exist" in e for e in self.errors(directories=dirs)))

    def test_stale_fidelity_is_refused(self):
        index = copy.deepcopy(self.index)
        entry(index, "964-chassis")["records"][0]["fidelity"] = "F2_interface"
        entry(index, "964-chassis")["fidelity"] = "F2_interface"
        self.assertTrue(any("fidelity is 'F1_envelope' in its record" in e for e in self.errors(index)))

    def test_fidelity_without_record_is_refused(self):
        index = copy.deepcopy(self.index)
        entry(index, "993-installed-cooling-f1")["fidelity"] = "F1_envelope"
        self.assertTrue(any("must be 'none_declared'" in e for e in self.errors(index)))

    def test_unaccounted_twin_record_is_refused(self):
        index = copy.deepcopy(self.index)
        index["records_without_directory"] = []
        self.assertTrue(any("TWIN-993-WHEEL-HUB-INTERFACES-0001 is not accounted for" in e for e in self.errors(index)))

    def test_physical_correlation_needs_a_correlated_record(self):
        index = copy.deepcopy(self.index)
        entry(index, "964-chassis")["physical_correlation"] = "bench"
        self.assertTrue(any("physical correlation claimed" in e for e in self.errors(index)))

    def test_archived_flag_follows_record(self):
        index = copy.deepcopy(self.index)
        entry(index, "993-engine-cooling-fan-system-f0")["records"][0]["archived"] = False
        self.assertTrue(any("archived flag disagrees" in e for e in self.errors(index)))

    def test_part_citing_directory_must_be_listed(self):
        index = copy.deepcopy(self.index)
        entry(index, "993-engine-mount-system-f0")["part_ids"] = ["993-ENG-BRACKET-0001"]
        self.assertTrue(any("993-ENG-MOUNTING-0001" in e and "not listed" in e for e in self.errors(index)))

    def test_active_entry_needs_an_issue(self):
        index = copy.deepcopy(self.index)
        entry(index, "993-reference-envelope")["issues"] = []
        self.assertTrue(any("active entries must link" in e for e in self.errors(index)))

    def test_stale_readme_table_is_refused(self):
        readme = self.readme.replace("| research register | active |", "| research register | study |", 1)
        self.assertNotEqual(readme, self.readme)
        self.assertTrue(any("generated table is stale" in e for e in self.errors(readme=readme)))

    def test_no_entry_is_a_physical_twin(self):
        for e in self.index["directories"]:
            self.assertEqual(e["physical_correlation"], "none", e["directory"])
            self.assertNotEqual(e["kind"], "physical_twin", e["directory"])


if __name__ == "__main__":
    unittest.main()
