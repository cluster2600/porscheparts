from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/validate_head_architecture_authority_f45.py"
SPEC = importlib.util.spec_from_file_location("validate_head_architecture_authority_f45", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HeadArchitectureAuthorityF45Tests(unittest.TestCase):
    def test_tracked_contract_passes_and_locks_two_variants(self) -> None:
        self.assertEqual(MODULE.validate(ROOT), [])
        contract = json.loads((ROOT / MODULE.CONTRACT).read_text(encoding="utf-8"))
        self.assertEqual(
            [variant["valve_count_per_cylinder"] for variant in contract["head_variants"]],
            [2, 4],
        )

    def test_global_ovalization_cannot_be_enabled(self) -> None:
        contract = json.loads((ROOT / MODULE.CONTRACT).read_text(encoding="utf-8"))
        for key in (
            "global_ellipse_or_oval_envelope_allowed",
            "ellipse_extrusion_allowed_for_head_body_or_fins",
            "f39_ellipse_volume_lineage_accepted",
        ):
            self.assertIs(contract["morphology_authority"][key], False)

    def test_print_release_cannot_be_predeclared(self) -> None:
        contract = json.loads((ROOT / MODULE.CONTRACT).read_text(encoding="utf-8"))
        self.assertTrue(contract["release_gates"])
        self.assertTrue(all(value is False for value in contract["release_gates"].values()))
        self.assertTrue(
            all(variant["metal_print_authorized"] is False for variant in contract["head_variants"])
        )


if __name__ == "__main__":
    unittest.main()
