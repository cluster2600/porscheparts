import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_openusd_federation.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_openusd_federation", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993OpenUsdFederationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root_stage, cls.shards, cls.manifest = generator.build()

    def test_every_part_master_has_exactly_one_metadata_prim(self) -> None:
        self.assertEqual(self.manifest["scope"]["part_master_prims"], 6013)
        self.assertEqual(
            sum(text.count('def Xform "TWIN_') for text in self.shards.values()),
            6013,
        )
        self.assertEqual(len(self.shards), 16)
        self.assertEqual(
            sum(
                item["part_master_prim_count"]
                for item in self.manifest["output"]["shards"]
            ),
            6013,
        )

    def test_root_federates_all_shards_and_ten_systems(self) -> None:
        for shard_id in generator.SHARD_IDS:
            self.assertIn(f"@shards/{shard_id}.usda@", self.root_stage)
        self.assertEqual(self.root_stage.count('def Scope "System_'), 10)
        self.assertEqual(self.manifest["scope"]["system_scope_count"], 10)
        self.assertEqual(self.manifest["scope"]["documentary_occurrences"], 12879)

    def test_federation_exposes_engineering_state_without_physics_claims(self) -> None:
        combined = self.root_stage + "\n" + "\n".join(self.shards.values())
        self.assertIn("custom string nextRequiredGate", combined)
        self.assertIn("custom string engineeringArchetype", combined)
        self.assertIn("custom int declaredBoundingBoxCount", combined)
        self.assertIn("custom asset[] candidateProxyUsdAssets", combined)
        self.assertIn("custom bool candidateProxyComposed = false", combined)
        self.assertNotIn("custom bool editableEnvelopeCandidatePresent = true", combined)
        self.assertIn("custom bool editableEnvelopeCandidatePresent = false", combined)
        self.assertIn(
            "custom bool editableValveDimensionalSurrogatePresent = true", combined
        )
        self.assertIn(
            "custom bool editableK16EnvelopeDiameterGuidesPresent = true", combined
        )
        self.assertIn(
            "custom bool editableHeatShieldEnvelopeThermalReadinessPresent = true",
            combined,
        )
        self.assertIn(
            "custom bool turboLubricationControlTopologyReadinessPresent = true",
            combined,
        )
        self.assertIn(
            "custom bool oilTankCircuitTopologyReadinessPresent = true", combined
        )
        self.assertIn(
            "custom bool oilCoolerCircuitTopologyReadinessPresent = true", combined
        )
        self.assertIn(
            "custom bool massConstrainedStructuralSurrogateVirtualF2ReadinessPresent = true",
            combined,
        )
        self.assertIn("custom bool F2InterfaceGeometryPresent = false", combined)
        self.assertIn("custom bool physicsNeMoValidated = false", combined)
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MaterialBindingAPI",
            "xformOp:translate",
            "def Mesh",
            "def Cube",
        ):
            self.assertNotIn(prohibited, combined)

    def test_counts_match_the_engineering_readiness_contract(self) -> None:
        scope = self.manifest["scope"]
        readiness = json.loads(generator.READINESS_INDEX.read_text(encoding="utf-8"))
        source_scope = readiness["scope"]
        self.assertEqual(scope["part_master_prims"], source_scope["engineering_tasks"])
        self.assertEqual(
            scope["with_turbo_integration_evidence"],
            source_scope["tasks_with_turbo_integration_evidence"],
        )
        self.assertEqual(
            scope["with_declared_bounding_box"],
            source_scope["tasks_with_declared_bounding_box"],
        )
        self.assertEqual(
            scope["with_non_placeholder_material_observation"],
            source_scope["tasks_with_non_placeholder_declared_material_label"],
        )

    def test_detailed_identity_output_stays_untracked_and_fail_closed(self) -> None:
        self.assertFalse(self.manifest["output"]["tracked"])
        self.assertEqual(
            self.manifest["rights_boundary"]["detailed_pet_identity_text_location"],
            "work_only_untracked",
        )
        self.assertTrue(
            all(value is False for value in self.manifest["claim_boundary"].values())
        )
        self.assertFalse(self.manifest["validation"]["simready_validated"])

    def test_exact_oem_proxy_links_are_candidates_not_composed_geometry(self) -> None:
        scope = self.manifest["scope"]
        linkage = self.manifest["proxy_linkage"]
        self.assertEqual(scope["catalogue_proxy_assets"], 18)
        self.assertEqual(scope["catalogue_proxy_assets_with_oem_reference"], 9)
        self.assertEqual(scope["with_exact_oem_proxy_candidate"], 9)
        self.assertEqual(scope["exact_oem_proxy_candidate_links"], 9)
        self.assertEqual(
            scope["by_current_fidelity"],
            {
                "F0_reference": 5842,
                "F1_charge_air_chain_guides_unvalidated": 5,
                "F1_heat_shield_envelope_thermal_readiness_unvalidated": 1,
                "F1_k16_envelope_diameter_guides_unvalidated": 4,
                "F1_mass_constrained_structural_surrogate_virtual_F2_readiness": 1,
                "F1_oil_tank_circuit_topology_readiness_unvalidated": 81,
                "F1_oil_cooler_circuit_topology_readiness_unvalidated": 41,
                "F1_turbo_lubrication_control_topology_readiness_unvalidated": 35,
                "F1_valve_dimensional_surrogate_unvalidated": 3,
            },
        )
        self.assertEqual(len(linkage["links"]), 9)
        self.assertTrue(linkage["candidate_only"])
        self.assertFalse(linkage["geometry_composed_into_federation"])
        for link in linkage["links"]:
            self.assertFalse(link["geometry_fit_validated"])
            self.assertEqual(link["link_status"], "identity_candidate_not_geometry_fit")

    def test_checked_in_manifest_and_work_layers_are_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
