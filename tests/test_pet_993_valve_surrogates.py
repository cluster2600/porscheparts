import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_valve_surrogates.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_valve_surrogates", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993ValveSurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = generator.derive()
        self.scad = generator.render_scad(self.data)
        self.usd = generator.render_usd(self.data)
        self.report = generator.build_report(self.data, self.scad, self.usd)
        generator.validate(self.data, self.scad, self.usd, self.report)

    def test_three_variants_preserve_declared_dimensions_and_hypothesis_status(self) -> None:
        by_id = {item["variant_id"]: item for item in self.report["variants"]}
        self.assertEqual(len(by_id), 3)
        self.assertEqual(
            by_id["993-carrera-exhaust-42_5-f1"]["dimensions_mm"],
            {
                "head_diameter": 42.5,
                "stem_diameter": 8.0,
                "overall_length": 109.0,
                "overall_length_status": "supplier_declared",
            },
        )
        self.assertEqual(
            by_id["993-intake-49-f1"]["dimensions_mm"]["overall_length_status"],
            "hypothesis_from_110_mm_product_envelope",
        )

    def test_exact_oem_links_cover_three_pet_masters_without_filling_gaps(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(summary["oem_references_in_scope"], 5)
        self.assertEqual(summary["pet_linked_oem_references"], 3)
        self.assertEqual(summary["pet_unmatched_oem_references"], 2)
        self.assertEqual(summary["pet_linked_part_masters"], 3)
        turbo = next(
            item
            for item in self.report["variants"]
            if item["variant_id"] == "993-turbo-exhaust-43_5-f1"
        )
        self.assertEqual(turbo["linked_pet_oem_references"], ["99310541952"])
        self.assertEqual(
            turbo["unmatched_pet_oem_references"],
            ["99310541953", "99310541984"],
        )

    def test_intake_mass_is_only_an_arithmetic_consistency_check(self) -> None:
        intake = next(
            item
            for item in self.report["variants"]
            if item["variant_id"] == "993-intake-49-f1"
        )
        check = intake["declared_mass_consistency"]
        self.assertAlmostEqual(check["equivalent_density_g_cm3"], 7.668128851, places=9)
        self.assertAlmostEqual(check["generic_steel_residual_g"], 2.063676582, places=9)
        self.assertEqual(
            check["interpretation"],
            "arithmetic_consistency_only_not_material_identification",
        )

    def test_editable_scad_and_openusd_remain_guides(self) -> None:
        self.assertEqual(self.scad.count("valve_surrogate("), 4)
        self.assertEqual(self.usd.count('kind = "component"'), 3)
        self.assertEqual(self.usd.count('purpose = "guide"'), 9)
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, self.usd)

    def test_materials_and_all_downstream_claims_fail_closed(self) -> None:
        for variant in self.report["variants"]:
            for material in variant["mass_comparisons"]:
                self.assertEqual(
                    material["qualification_status"],
                    "candidate_or_placeholder_not_part_qualified",
                )
        self.assertFalse(any(self.report["claim_boundary"].values()))
        self.assertFalse(self.report["interface_readiness"]["F2_interface_geometry"])
        self.assertEqual(self.report["summary"]["reference_solver_results"], 0)
        self.assertEqual(self.report["summary"]["physicsnemo_results"], 0)

    def test_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
