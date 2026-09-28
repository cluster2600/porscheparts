import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_visual_proxy_atlas.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_visual_proxy_atlas", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993VisualProxyAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (
            cls.root_stage,
            cls.prototype_stage,
            cls.shards,
            cls.composed_stage,
            cls.manifest,
        ) = generator.build()

    def test_every_part_master_has_one_renderable_visual_proxy(self) -> None:
        atlas = self.manifest["atlas"]
        self.assertEqual(atlas["part_master_proxy_instances"], 6013)
        self.assertEqual(atlas["catalogue_master_coverage_ratio"], 1.0)
        self.assertEqual(
            sum(text.count('def Xform "TWIN_') for text in self.shards.values()),
            6013,
        )
        token = "prepend references = @../pet-993-visual-proxy-prototypes-f0.usda@"
        self.assertEqual(sum(text.count(token) for text in self.shards.values()), 6013)
        self.assertEqual(
            sum(item["proxy_instance_count"] for item in self.manifest["output"]["shards"]),
            6013,
        )

    def test_archetype_and_system_partitions_close(self) -> None:
        atlas = self.manifest["atlas"]
        self.assertEqual(atlas["archetype_prototypes"], 42)
        self.assertEqual(
            atlas["archetype_prototypes"],
            len(atlas["by_engineering_archetype"]),
        )
        self.assertEqual(atlas["system_groups"], 10)
        self.assertEqual(atlas["shard_layers"], 16)
        self.assertEqual(sum(atlas["by_engineering_archetype"].values()), 6013)
        self.assertEqual(sum(atlas["by_primary_system"].values()), 6013)
        readiness = json.loads(generator.READINESS_INDEX.read_text(encoding="utf-8"))
        self.assertEqual(
            atlas["by_engineering_archetype"],
            readiness["coverage"]["tasks_by_engineering_archetype"],
        )
        self.assertEqual(self.root_stage.count('def Xform "System_'), 10)

    def test_symbols_are_explicitly_non_dimensional_and_non_physical(self) -> None:
        combined = self.prototype_stage + "\n" + "\n".join(self.shards.values())
        self.assertIn('custom string representation = "archetype_display_symbol_not_part_geometry"', combined)
        self.assertIn('custom string positionSemantics = "catalogue_grid_index_not_vehicle_transform"', combined)
        self.assertIn("custom bool displayGeometryOnly = true", combined)
        self.assertIn("custom bool dimensionallyAccurate = false", combined)
        self.assertIn("custom bool vehicleTransformKnown = false", combined)
        self.assertIn("custom bool referenceSimulationPassed = false", combined)
        self.assertIn("custom bool physicsNeMoValidated = false", combined)
        self.assertIn("custom bool simreadyValidated = false", combined)
        self.assertIn("custom bool manufacturingReleased = false", combined)
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, combined)

    def test_composed_stage_federates_documentary_visual_and_flow_layers(self) -> None:
        for prim in (
            "DocumentaryCatalogue",
            "VisualProxyAtlas",
            "FunctionalFlowTopology",
        ):
            self.assertIn(f'def Xform "{prim}"', self.composed_stage)
        self.assertIn("partMasterTwinCount = 6013", self.composed_stage)
        self.assertIn("visualProxyInstanceCount = 6013", self.composed_stage)
        self.assertIn("engineeringGeometryCount = 0", self.composed_stage)
        self.assertIn("positionedVehiclePartCount = 0", self.composed_stage)
        self.assertIn("functioningVehicle = false", self.composed_stage)

    def test_physicsnemo_contract_routes_meshes_but_rejects_atlas_as_data(self) -> None:
        boundary = self.manifest["physicsnemo_dataset_boundary"]
        self.assertEqual(
            boundary["discovered_commit"],
            "4fbfcfd62bf050b48ceec6b438da409b9f4644b3",
        )
        self.assertEqual(
            boundary["candidate_model_families"],
            ["GeoTransolver", "Transolver", "MeshGraphNet", "DoMINO"],
        )
        self.assertIn("MeshReader", boundary["candidate_data_interfaces"])
        self.assertIn("VTKReader", boundary["candidate_data_interfaces"])
        self.assertFalse(boundary["atlas_is_training_or_validation_data"])
        self.assertFalse(boundary["execution_enabled"])

    def test_tracked_manifest_contains_no_pet_identity_payload(self) -> None:
        rendered = json.dumps(self.manifest, ensure_ascii=False)
        self.assertNotIn("normalized_oem_reference", rendered)
        self.assertNotIn("display_references", rendered)
        self.assertNotIn('"descriptions"', rendered)
        self.assertFalse(self.manifest["output"]["tracked"])
        self.assertTrue(
            all(value is False for value in self.manifest["claim_boundary"].values())
        )

    def test_checked_in_manifest_and_work_layers_are_current(self) -> None:
        self.assertEqual(generator.main(["--check-index"]), 0)
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
