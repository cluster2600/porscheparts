import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_catalogue_part_twins.py"
SPEC = importlib.util.spec_from_file_location("generate_catalogue_part_twins", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class CataloguePartTwinTests(unittest.TestCase):
    def test_current_catalogue_yields_four_wheels_and_fourteen_envelopes(self) -> None:
        components = [record["component_id"] for _, record in generator.component_candidates()]
        references, stats = generator.reference_candidates()
        self.assertEqual(
            components,
            [
                "COMP-FUCHS-37024.013",
                "COMP-FUCHS-37026.013",
                "COMP-FUCHS-37027.011",
                "COMP-FUCHS-37028.011",
            ],
        )
        self.assertEqual(len(references), 14)
        self.assertIn(
            "993-ENGINE-CARRIER-TURBO",
            [record["entry_id"] for _, record in references],
        )
        self.assertEqual(stats["dimensioned_reference_entries"], 14)
        self.assertEqual(stats["unresolved_material_entries"], 13)
        self.assertEqual(stats["excluded_for_placeholder_material"], 0)

    def test_porschefanatics_context_confirms_identity_not_geometry(self) -> None:
        payload, records = generator.porschefanatics_context()
        carrier = records["993 115 021 53"]
        self.assertTrue(carrier["pet_verified"])
        self.assertEqual(carrier["pet_group"], "Engine suspension Turbo")
        self.assertEqual(carrier["pet_position"], 17)
        self.assertEqual(
            payload["catalogue_observations"]["part_records_with_993_fitment_and_top_level_dimensions"],
            0,
        )

    def test_generated_index_keeps_all_eighteen_assets_unvalidated(self) -> None:
        outputs = generator.build_outputs()
        index = json.loads(outputs[generator.OUTPUT / "index.json"])
        self.assertEqual(index["summary"]["generated_twins"], 18)
        self.assertEqual(index["summary"]["declared_reference_twins"], 14)
        self.assertEqual(index["summary"]["editable_proxy_sources"], 18)
        self.assertEqual(len(index["twins"]), 18)
        for twin in index["twins"]:
            self.assertEqual(twin["fidelity"], "F1_envelope")
            self.assertFalse(twin["validation"]["geometry_fit_validated"])
            self.assertEqual(twin["validation"]["physics_assignment"], "intentionally_absent")
            self.assertEqual(twin["validation"]["simready_status"], "not_evaluated")
            self.assertIn(generator.ROOT / twin["geometry"]["file"], outputs)
            self.assertIn(generator.ROOT / twin["geometry"]["editable_proxy_file"], outputs)

    def test_usd_assets_have_units_material_and_no_physics_schema(self) -> None:
        outputs = generator.build_outputs()
        usd_assets = [content for path, content in outputs.items() if path.suffix == ".usda"]
        self.assertEqual(len(usd_assets), 18)
        for content in usd_assets:
            self.assertIn("metersPerUnit = 0.001", content)
            self.assertIn('upAxis = "Z"', content)
            self.assertIn('def Material "DocumentaryMaterial"', content)
            self.assertIn('custom string documentationStatus = "F1_documentary_proxy_not_simready"', content)
            self.assertNotIn("UsdPhysics", content)
            self.assertNotIn("CollisionAPI", content)

    def test_every_proxy_has_an_editable_scad_envelope(self) -> None:
        outputs = generator.build_outputs()
        scad_assets = [content for path, content in outputs.items() if path.suffix == ".scad"]
        self.assertEqual(len(scad_assets), 18)
        for content in scad_assets:
            self.assertIn("Not manufacturing geometry", content)
            self.assertIn("proxy_id", content)

    def test_unknown_materials_remain_unresolved(self) -> None:
        outputs = generator.build_outputs()
        index = json.loads(outputs[generator.OUTPUT / "index.json"])
        declared = [
            twin
            for twin in index["twins"]
            if twin["subject"]["kind"] == "declared_reference_entry"
        ]
        self.assertEqual(
            sum(twin["physical"]["material_status"] == "unresolved" for twin in declared),
            13,
        )
        for twin in declared:
            if twin["physical"]["material_status"] == "unresolved":
                self.assertIsNone(twin["physical"]["material"]["family"])

    def test_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(generator.run(write=False), 0)


if __name__ == "__main__":
    unittest.main()
