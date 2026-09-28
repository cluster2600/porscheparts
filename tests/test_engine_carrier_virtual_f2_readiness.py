"""Tests du contrat F2 virtuel et fail-closed du berceau moteur 993 Turbo."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "parts"
    / "993-eng-carrier-0001"
    / "source"
    / "build_virtual_f2_readiness.py"
)
REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engine-carrier-virtual-f2-readiness.json"
)
USD = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-engine-carrier-virtual-f2-readiness.usda"
)


spec = importlib.util.spec_from_file_location("engine_carrier_virtual_f2", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EngineCarrierVirtualF2ReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.usd = USD.read_text(encoding="utf-8")

    def test_checked_contract_is_current_and_deterministic(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(module.render_json(module.build_report(module.render_usd())), REPORT.read_text(encoding="utf-8"))
        self.assertEqual(module.render_usd(), self.usd)

    def test_every_upstream_is_digest_bound(self) -> None:
        files = self.report["source_boundary"]["files"]
        self.assertEqual(len(files), 8)
        for item in files:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(
                item["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_catalogue_links_two_companion_identities_without_claiming_interfaces(self) -> None:
        self.assertEqual(self.report["subject"]["oem_reference"], "993 115 021 53")
        self.assertEqual(self.report["subject"]["variant"], "993-turbo")
        interfaces = self.report["interface_hypotheses"]
        self.assertEqual(
            {item["peer_oem_reference"] for item in interfaces},
            {"993 115 103 52", "993 375 049 05"},
        )
        for item in interfaces:
            self.assertIsNone(item["coordinates_mm"])
            self.assertIsNone(item["contact_geometry"])
            self.assertIsNone(item["tolerance_mm"])
            self.assertFalse(item["confirmed_interface_geometry"])

    def test_symbolic_gravity_bound_is_reproducible_but_not_a_strength_result(self) -> None:
        model = self.report["mathematical_model"]
        bounds = model["computed_documentary_bounds"]
        expected = round(195.0 * 9.80665, 6)
        self.assertEqual(bounds["static_gravity_force_range_N"], [0.0, expected])
        self.assertEqual(
            bounds["conditional_equal_mount_reaction_range_N_each"],
            [0.0, round(expected / 2.0, 6)],
        )
        self.assertIsNone(bounds["component_strength_or_life_conclusion"])
        self.assertFalse(
            self.report["documentary_inputs"]["tightening_candidate"]["used_to_compute_preload"]
        )

    def test_unknowns_and_load_cases_remain_fail_closed(self) -> None:
        parameters = self.report["parameter_registry"]
        self.assertEqual(len(parameters), 19)
        self.assertTrue(
            all(item["value"] is None and item["uncertainty"] is None for item in parameters)
        )
        cases = self.report["load_cases"]
        self.assertEqual(len(cases), 8)
        self.assertTrue(all(item["status"].startswith("blocked") for item in cases))
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))

    def test_mass_constrained_surrogate_closes_mass_without_F2_credit(self) -> None:
        surrogate = self.report["mass_constrained_surrogate"]
        self.assertTrue(surrogate["mass_constraint_closed"])
        self.assertAlmostEqual(surrogate["equivalent_wall_mm"], 2.175319724, places=9)
        self.assertEqual(surrogate["interface_search_domain_count"], 2)
        self.assertEqual(surrogate["selected_interface_point_count"], 0)
        self.assertFalse(surrogate["component_geometry_credit"])
        self.assertFalse(surrogate["reference_CAE_credit"])

    def test_llm_physicsnemo_and_openusd_have_no_physical_authority(self) -> None:
        roles = self.report["model_roles"]
        self.assertEqual(roles["llm"]["output_authority"], "hypothesis_only")
        self.assertFalse(roles["physicsnemo"]["training_enabled"])
        self.assertFalse(roles["physicsnemo"]["inference_enabled"])
        self.assertFalse(roles["physicsnemo"]["validated"])
        self.assertFalse(roles["omniverse"]["F2_interface_geometry_present"])
        self.assertTrue(
            roles["omniverse"]["F1_mass_constrained_surrogate_composed"]
        )
        self.assertEqual(
            roles["omniverse"]["semantic_layer_sha256"],
            hashlib.sha256(self.usd.encode("utf-8")).hexdigest(),
        )
        for forbidden in ("Physics", "Mesh", "xformOp:", "translate ="):
            self.assertNotIn(forbidden, self.usd)
        self.assertIn("f2InterfaceGeometryPresent = false", self.usd)
        self.assertIn("coordinatesKnown = false", self.usd)


if __name__ == "__main__":
    unittest.main()
