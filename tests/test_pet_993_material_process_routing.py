import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_material_process_routing.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_material_process_routing", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993MaterialProcessRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, _ = generator.build()
        cls.routes = []
        for shard in cls.manifest["output"]["shards"]:
            path = ROOT / shard["path"]
            with path.open("r", encoding="utf-8") as handle:
                cls.routes.extend(
                    json.loads(line) for line in handle if line.strip()
                )

    def test_every_part_master_has_one_material_process_route(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(scope["part_master_routing_tasks"], 6013)
        self.assertEqual(scope["archetype_profiles"], 42)
        self.assertEqual(scope["profile_groups"], 15)
        self.assertEqual(len(self.routes), 6013)
        self.assertEqual(
            len({item["screening_task_id"] for item in self.routes}), 6013
        )
        self.assertEqual(
            sum(self.manifest["coverage"]["tasks_by_profile_group"].values()),
            6013,
        )

    def test_candidates_cover_catalogue_without_becoming_selections(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(scope["tasks_with_material_family_candidates"], 6013)
        self.assertEqual(scope["tasks_with_manufacturing_route_candidates"], 5738)
        self.assertEqual(scope["tasks_with_additive_route_candidate"], 5405)
        self.assertEqual(scope["tasks_with_titanium_family_candidate"], 450)
        for key in (
            "selected_materials",
            "selected_manufacturing_routes",
            "passed_reference_simulations",
            "trained_or_validated_physicsnemo_models",
            "omniverse_material_or_physics_validations",
            "manufacturing_releases",
        ):
            self.assertEqual(scope[key], 0)
        for route in self.routes:
            self.assertTrue(
                route["routing_profile"]["candidate_material_families"]
            )
            self.assertTrue(route["selection_inputs"]["missing"])
            self.assertEqual(route["selection_inputs"]["complete"], [])
            for key, value in route["selection"].items():
                if key.startswith("selected_"):
                    self.assertIsNone(value)
            self.assertTrue(all(value is False for value in route["claims"].values()))

    def test_titanium_candidates_carry_all_extra_controls(self) -> None:
        requirements = self.manifest["selection_policy"][
            "titanium_extra_requirements"
        ]
        self.assertEqual(len(requirements), 8)
        titanium_routes = [
            route
            for route in self.routes
            if route["routing_profile"]["titanium_extra_requirements"]
        ]
        self.assertEqual(len(titanium_routes), 450)
        for route in titanium_routes:
            self.assertEqual(
                route["routing_profile"]["titanium_extra_requirements"],
                requirements,
            )
            self.assertIsNone(route["selection"]["selected_material"])

    def test_service_and_label_rows_are_not_forced_into_part_manufacture(self) -> None:
        service_routes = [
            route
            for route in self.routes
            if route["routing_profile"]["group_id"] == "label_service"
        ]
        self.assertEqual(len(service_routes), 275)
        for route in service_routes:
            profile = route["routing_profile"]
            self.assertEqual(profile["candidate_manufacturing_routes"], [])
            self.assertEqual(
                profile["disposition"],
                "specification_or_qualified_supplier_item_not_part_geometry",
            )

    def test_exact_commercial_alternatives_remain_unqualified_evidence(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(
            scope["tasks_with_exact_commercial_alternative_evidence"], 2
        )
        self.assertEqual(scope["exact_commercial_alternative_links"], 6)
        self.assertEqual(
            scope["commercial_alternative_links_with_qualified_material_basis"],
            0,
        )
        linked_routes = [
            route
            for route in self.routes
            if route["commercial_alternative_evidence"][
                "exact_replacement_link_count"
            ]
        ]
        self.assertEqual(len(linked_routes), 2)
        self.assertEqual(
            sum(
                route["commercial_alternative_evidence"][
                    "exact_replacement_link_count"
                ]
                for route in linked_routes
            ),
            6,
        )
        for route in self.routes:
            evidence = route["commercial_alternative_evidence"]
            self.assertEqual(evidence["qualified_material_basis_link_count"], 0)
            self.assertFalse(
                evidence["proves_oem_geometry_material_or_equivalence"]
            )
        self.assertEqual(
            self.manifest["commercial_alternative_boundary"]["link_method"],
            "exact_normalized_replacesOem",
        )
        self.assertTrue(
            all(
                value is False
                for key, value in self.manifest[
                    "commercial_alternative_boundary"
                ].items()
                if key != "link_method"
            )
        )

    def test_reference_models_are_routes_not_solver_results(self) -> None:
        self.assertFalse(
            self.manifest["selection_policy"][
                "system_fallback_archetype_is_part_classification"
            ]
        )
        self.assertTrue(
            self.manifest["selection_policy"][
                "reference_solver_precedes_physicsnemo"
            ]
        )
        for route in self.routes:
            self.assertTrue(route["reference_model_routes"])
            self.assertTrue(
                all(
                    item["reference_solver_status"] == "not_run"
                    for item in route["reference_model_routes"]
                )
            )
            physicsnemo = route["physicsnemo_route"]
            self.assertIsNone(physicsnemo["selected_model"])
            self.assertFalse(physicsnemo["execution_enabled"])
            self.assertTrue(
                set(physicsnemo["candidate_models"])
                <= set(
                    self.manifest["physicsnemo_boundary"][
                        "verified_model_families"
                    ]
                )
            )
        self.assertTrue(
            all(value is False for value in self.manifest["claim_boundary"].values())
        )

    def test_physicsnemo_axes_are_current_and_remain_disabled(self) -> None:
        boundary = self.manifest["physicsnemo_boundary"]
        self.assertEqual(
            boundary["discovered_commit"],
            "4fbfcfd62bf050b48ceec6b438da409b9f4644b3",
        )
        self.assertEqual(
            set(boundary["verified_model_families"]),
            {"GeoTransolver", "Transolver", "MeshGraphNet", "FIGConvUNet", "DoMINO"},
        )
        self.assertIn("MeshReader", boundary["verified_data_interfaces"])
        self.assertIn("DomainMeshReader", boundary["verified_data_interfaces"])
        self.assertIn("VTKReader", boundary["verified_data_interfaces"])
        self.assertTrue(boundary["model_and_datapipe_are_independent_axes"])
        self.assertFalse(boundary["execution_enabled"])

    def test_checked_in_manifest_and_work_shards_are_current(self) -> None:
        self.assertEqual(generator.main(["--check-index"]), 0)
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
