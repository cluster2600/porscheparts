import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_reference_frame_usd.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_993_reference_frame_usd", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class ReferenceFrameUsdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope = generator.load_json(generator.REFERENCE_ENVELOPE)
        self.measurements = generator.load_json(generator.MEASUREMENTS)
        self.preflight = generator.load_json(generator.PREFLIGHT)
        self.stage = generator.render_stage(self.envelope, self.measurements)
        self.contract = generator.build_contract(
            self.envelope, self.measurements, self.preflight, self.stage
        )
        generator.validate(
            self.envelope,
            self.measurements,
            self.preflight,
            self.stage,
            self.contract,
        )

    def test_stage_contains_seven_sourced_dimensions_and_five_reference_curves(self) -> None:
        self.assertEqual(self.stage.count("sourceMeasurementId"), 11)
        self.assertEqual(self.stage.count("def BasisCurves"), 5)
        for name in generator.PARAMETERS:
            self.assertIn(f'def Scope "{name}"', self.stage)

    def test_stage_uses_meters_and_preserves_unknown_longitudinal_datum(self) -> None:
        self.assertIn("metersPerUnit = 1", self.stage)
        self.assertIn('upAxis = "Z"', self.stage)
        self.assertIn(
            'longitudinalPosition = "display_centered_assumption"', self.stage
        )
        self.assertIn("bool axleLongitudinalPositionsAreSourced = false", self.stage)
        self.assertIsNone(
            self.contract["uncertainty_boundary"][
                "body_to_axle_longitudinal_transform"
            ]
        )

    def test_mathematical_envelope_checks_close_without_becoming_simulation(self) -> None:
        checks = self.contract["mathematical_sanity_checks"]
        for key in (
            "wheelbase_inside_overall_length",
            "front_track_inside_overall_width",
            "rear_track_inside_overall_width",
            "ground_clearance_inside_overall_height",
        ):
            self.assertTrue(checks[key])
        self.assertEqual(self.contract["scope"]["positioned_vehicle_parts"], 0)
        self.assertEqual(self.contract["scope"]["body_surface_count"], 0)

    def test_four_documented_mass_constraints_are_not_mass_properties(self) -> None:
        constraints = self.contract["documented_mass_constraints"]
        self.assertEqual(set(constraints), set(generator.MASS_PARAMETERS))
        self.assertEqual(self.contract["scope"]["sourced_mass_constraints"], 4)
        self.assertEqual(self.contract["scope"]["mass_property_count"], 0)
        self.assertEqual(
            self.contract["mathematical_sanity_checks"][
                "declared_payload_difference_kg"
            ],
            320.0,
        )
        self.assertEqual(
            self.contract["mathematical_sanity_checks"][
                "combined_axle_capacity_margin_kg"
            ],
            95.0,
        )
        for item in constraints.values():
            self.assertFalse(item["is_mass_distribution_measurement"])
            self.assertFalse(item["is_usd_mass_property"])

    def test_no_physics_material_or_simready_claim_is_authored(self) -> None:
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, self.stage)
        self.assertTrue(
            all(value is False for value in self.contract["claim_boundary"].values())
        )
        self.assertEqual(
            self.contract["validation"]["minimum_usd_validation"],
            "not_run_preflight_blocked",
        )

    def test_contract_uses_the_blocked_preflight_as_a_guardrail(self) -> None:
        self.assertEqual(self.preflight["status"], "blocked")
        self.assertEqual(
            self.contract["source_boundary"]["simready_preflight_status"],
            "blocked",
        )
        self.assertEqual(
            self.contract["validation"]["property_assignment_intent"],
            "run_for_end_to_end_request",
        )

    def test_checked_in_stage_and_contract_are_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(
            json.loads(generator.CONTRACT.read_text(encoding="utf-8")),
            self.contract,
        )
        self.assertEqual(generator.OUTPUT.read_text(encoding="utf-8"), self.stage)


if __name__ == "__main__":
    unittest.main()
