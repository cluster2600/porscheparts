import importlib.util
import importlib.util
import json
import math
import os
import re
import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/rotating-assembly-cad-f35.json"
FACTS_PATH = ROOT / "twins/reference-917-engine/classical-solver-cases-f13.json"
MATH_PATH = ROOT / "twins/reference-917-engine/source/rotating_assembly_f35_math.py"
CAD_BUILDER_PATH = ROOT / "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py"
USD_AUTHOR_PATH = ROOT / "twins/reference-917-engine/source/author_rotating_assembly_usd_f35.py"

MATH_SPEC = importlib.util.spec_from_file_location("rotating_assembly_f35_math_test", MATH_PATH)
assert MATH_SPEC is not None and MATH_SPEC.loader is not None
MATH_MODULE = importlib.util.module_from_spec(MATH_SPEC)
MATH_SPEC.loader.exec_module(MATH_MODULE)
SOURCE_PATH = ROOT / "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py"
SOURCE_DIR = SOURCE_PATH.parent
MAKEFILE_PATH = ROOT / "Makefile"

EXPECTED_VARIANTS = {
    "type_912_4_5_na": "naturally_aspirated_flat_12",
    "917_30_turbo_5374": "twin_turbo_flat_12",
}
EXPECTED_PARAMETERS = {
    "cylinder_count",
    "bore_mm",
    "stroke_mm",
    "crank_radius_mm",
    "crankpin_count",
    "main_bearing_count",
    "cylinder_pitch_mm",
    "central_pair_pitch_mm",
    "crankshaft_envelope_length_mm",
    "rod_center_distance_mm",
    "crankpin_diameter_mm",
    "main_journal_diameter_mm",
    "crankpin_width_mm",
    "main_journal_width_mm",
    "rod_big_end_outer_diameter_mm",
    "rod_small_end_bore_mm",
    "rod_width_mm",
    "piston_pin_diameter_mm",
    "piston_pin_length_mm",
    "piston_crown_to_pin_axis_mm",
    "piston_skirt_below_pin_mm",
    "piston_radial_clearance_mm",
    "ring_count",
    "ring_axial_height_mm",
    "ring_radial_thickness_mm",
}
PARAMETER_FIELDS = {"value", "unit", "classification", "source_refs", "note"}
CLASSIFICATIONS = {
    "documentary_candidate",
    "derived_from_documentary_candidate",
    "design_hypothesis",
}
EXPECTED_COMPONENT_COUNTS = {
    "crankshaft": 1,
    "main_bearing": 8,
    "connecting_rod": 12,
    "piston": 12,
    "piston_pin": 12,
    "piston_ring": 36,
}
EXPECTED_INTERFACE_FRAME_COUNTS = {
    "crankshaft_axis": 1,
    "main_journal_centres_01_to_08": 8,
    "crankpin_centres_01_to_06": 6,
    "rod_big_end_axis": 12,
    "rod_small_end_axis": 12,
    "piston_pin_axis": 12,
    "piston_crown_datum": 12,
    "piston_ring_groove_datums": 36,
}


class RotatingAssemblyCadF35ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        fact_document = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
        cls.facts = {item["id"]: item for item in fact_document["fact_registry"]}
        cls.variants = {item["id"]: item for item in cls.contract["variants"]}
        sys.path.insert(0, str(SOURCE_DIR))
        spec = importlib.util.spec_from_file_location("build_rotating_assembly_cad_f35_test", SOURCE_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot import F35 CAD builder")
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    @classmethod
    def tearDownClass(cls):
        if sys.path and sys.path[0] == str(SOURCE_DIR):
            sys.path.pop(0)

    def test_contract_identity_and_two_separate_variants(self):
        self.assertEqual(self.contract["schema_version"], "1.0.0")
        self.assertEqual(self.contract["phase"], "F35")
        self.assertEqual(
            self.contract["status"],
            "parametric_rotating_assembly_research_contract_all_physical_release_gates_blocked",
        )
        self.assertEqual(self.contract["units"], "mm")
        self.assertEqual(
            {item["id"]: item["architecture"] for item in self.contract["variants"]},
            EXPECTED_VARIANTS,
        )
        self.assertEqual(len(self.contract["variants"]), len(self.variants))
        self.assertTrue(all(item["historicalCylinderId"] is None for item in self.variants.values()))

    def test_every_variant_has_the_exact_classified_parameter_set(self):
        for variant_id, variant in self.variants.items():
            with self.subTest(variant=variant_id):
                self.assertEqual(set(variant["parameters"]), EXPECTED_PARAMETERS)
                for parameter_id, parameter in variant["parameters"].items():
                    with self.subTest(variant=variant_id, parameter=parameter_id):
                        self.assertEqual(set(parameter), PARAMETER_FIELDS)
                        self.assertIn(parameter["classification"], CLASSIFICATIONS)
                        self.assertIsInstance(parameter["source_refs"], list)
                        self.assertIsInstance(parameter["note"], str)
                        self.assertTrue(parameter["note"].strip())
                        self.assertIsInstance(parameter["unit"], str)
                        self.assertTrue(parameter["unit"])
                        self.assertIsInstance(parameter["value"], (int, float))
                        self.assertNotIsInstance(parameter["value"], bool)
                        self.assertGreater(parameter["value"], 0)

    def test_design_hypotheses_never_carry_source_references(self):
        for variant_id, variant in self.variants.items():
            for parameter_id, parameter in variant["parameters"].items():
                with self.subTest(variant=variant_id, parameter=parameter_id):
                    if parameter["classification"] == "design_hypothesis":
                        self.assertEqual(parameter["source_refs"], [])
                    else:
                        self.assertTrue(parameter["source_refs"])

    def test_documentary_parameters_exactly_match_the_f13_fact_registry(self):
        for variant_id, bindings in self.contract["source_fact_bindings"].items():
            parameters = self.variants[variant_id]["parameters"]
            for parameter_id, fact_id in bindings.items():
                with self.subTest(variant=variant_id, parameter=parameter_id, fact=fact_id):
                    fact = self.facts[fact_id]
                    parameter = parameters[parameter_id]
                    self.assertEqual(parameter["classification"], "documentary_candidate")
                    self.assertEqual(parameter["value"], fact["candidate"]["value"])
                    self.assertEqual(parameter["unit"], fact["candidate"]["unit"])
                    self.assertEqual(parameter["source_refs"], fact["source_refs"])
                    self.assertIs(fact["design_lock"], False)

    def test_piston_group_mass_is_registered_without_physical_assignment_or_turbo_transfer(self):
        register = self.contract["documentary_mass_register"]
        self.assertEqual(set(register), set(EXPECTED_VARIANTS))

        na = register["type_912_4_5_na"]
        fact = self.facts["FACT-45-PISTON-GROUP-MASS"]
        self.assertEqual(na["component_group"], "piston_pin_ring_group")
        self.assertEqual(na["fact_id"], fact["id"])
        self.assertEqual(na["value"], fact["candidate"]["value"])
        self.assertEqual(na["unit"], fact["candidate"]["unit"])
        self.assertEqual(
            na["declared_tolerance"], fact["candidate"]["declared_tolerance"]
        )
        self.assertEqual(na["source_refs"], fact["source_refs"])
        self.assertEqual(
            na["status"], "documentary_candidate_not_assigned_to_geometry_or_usd"
        )
        self.assertIs(na["physical_mass_assignment_allowed"], False)

        turbo = register["917_30_turbo_5374"]
        self.assertEqual(turbo["component_group"], "piston_pin_ring_group")
        self.assertIsNone(turbo["fact_id"])
        self.assertIsNone(turbo["value"])
        self.assertIsNone(turbo["declared_tolerance"])
        self.assertEqual(turbo["source_refs"], [])
        self.assertEqual(
            turbo["status"], "unknown_not_transferred_from_type_912_4_5_na"
        )
        self.assertIs(turbo["physical_mass_assignment_allowed"], False)

    def test_crank_radius_is_only_the_half_stroke_derivation(self):
        for variant_id, variant in self.variants.items():
            parameters = variant["parameters"]
            radius = parameters["crank_radius_mm"]
            stroke = parameters["stroke_mm"]
            with self.subTest(variant=variant_id):
                self.assertEqual(radius["classification"], "derived_from_documentary_candidate")
                self.assertTrue(math.isclose(radius["value"], stroke["value"] / 2.0, abs_tol=1e-12))
                self.assertEqual(radius["source_refs"], stroke["source_refs"])
                self.assertIn("stroke_mm / 2", radius["note"])

    def test_variant_specific_geometry_and_topology_are_not_collapsed(self):
        na = self.variants["type_912_4_5_na"]["parameters"]
        turbo = self.variants["917_30_turbo_5374"]["parameters"]
        self.assertEqual((na["bore_mm"]["value"], na["stroke_mm"]["value"]), (85.0, 66.0))
        self.assertEqual((turbo["bore_mm"]["value"], turbo["stroke_mm"]["value"]), (90.0, 70.4))
        for parameters in (na, turbo):
            self.assertEqual(parameters["cylinder_count"]["value"], 12)
            self.assertEqual(parameters["crankpin_count"]["value"], 6)
            self.assertEqual(parameters["main_bearing_count"]["value"], 8)
            self.assertEqual(parameters["ring_count"]["value"], 3)
            self.assertEqual(
                parameters["rod_small_end_bore_mm"]["value"],
                parameters["piston_pin_diameter_mm"]["value"],
            )
            self.assertGreater(
                parameters["rod_big_end_outer_diameter_mm"]["value"],
                parameters["crankpin_diameter_mm"]["value"],
            )
            self.assertGreater(
                parameters["rod_center_distance_mm"]["value"],
                2.0 * parameters["crank_radius_mm"]["value"],
            )

    def test_one_axial_layout_authority_prevents_paired_rod_overlap(self):
        for variant_id, variant in self.variants.items():
            width = variant["parameters"]["rod_width_mm"]["value"]
            layout = MATH_MODULE.paired_rod_axial_layout_mm(width)
            offsets = layout["bank_offsets_mm"]
            center_separation = abs(offsets["bank_A"] - offsets["bank_B"])
            with self.subTest(variant=variant_id):
                self.assertGreater(center_separation, width)
                self.assertGreater(layout["clearance_mm"], 0.0)
                self.assertTrue(
                    math.isclose(
                        center_separation - width,
                        layout["clearance_mm"],
                        rel_tol=0.0,
                        abs_tol=1.0e-12,
                    )
                )
                self.assertIs(layout["shared_crankpin_width_validated"], False)

        cad_source = CAD_BUILDER_PATH.read_text(encoding="utf-8")
        usd_source = USD_AUTHOR_PATH.read_text(encoding="utf-8")
        for source in (cad_source, usd_source):
            self.assertIn("paired_rod_axial_offset_mm", source)
            self.assertIn("paired_rod_axial_layout_mm", source)
        self.assertNotIn('parameter(variant, "rod_width_mm") * 0.53', cad_source)

    def test_na_only_fia_interfaces_are_not_transferred_to_turbo(self):
        na = self.variants["type_912_4_5_na"]["parameters"]
        turbo = self.variants["917_30_turbo_5374"]["parameters"]
        for parameter_id, fact_id in (
            ("crankpin_diameter_mm", "FACT-45-CRANKPIN-BEARING-DIAMETER"),
            ("piston_crown_to_pin_axis_mm", "FACT-45-PISTON-COMPRESSION-HEIGHT"),
        ):
            with self.subTest(parameter=parameter_id):
                self.assertEqual(na[parameter_id]["classification"], "documentary_candidate")
                self.assertEqual(na[parameter_id]["source_refs"], ["SRC-FIA-917-HOMOLOGATION-250"])
                self.assertEqual(na[parameter_id]["value"], self.facts[fact_id]["candidate"]["value"])
                self.assertEqual(turbo[parameter_id]["classification"], "design_hypothesis")
                self.assertEqual(turbo[parameter_id]["source_refs"], [])
                self.assertNotEqual(turbo[parameter_id]["value"], na[parameter_id]["value"])
                self.assertIn("n'est pas transféré", turbo[parameter_id]["note"])

    def test_ambiguous_fia_value_is_explicitly_excluded(self):
        excluded = {item["id"]: item for item in self.contract["excluded_fact_refs"]}
        fact_id = "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER"
        self.assertIn(fact_id, excluded)
        self.assertEqual(self.facts[fact_id]["usage"], "ambiguous_label_not_geometry_input")
        self.assertIn("56 mm", excluded[fact_id]["reason"])
        for variant in self.variants.values():
            parameter = variant["parameters"]["rod_big_end_outer_diameter_mm"]
            self.assertEqual(parameter["classification"], "design_hypothesis")
            self.assertEqual(parameter["source_refs"], [])

    def test_component_counts_and_interface_frames_cover_the_rotating_group(self):
        self.assertEqual(self.contract["expected_component_counts_per_variant"], EXPECTED_COMPONENT_COUNTS)
        self.assertEqual(
            self.contract["expected_component_counts_per_variant"]["piston_ring"],
            12 * self.variants["type_912_4_5_na"]["parameters"]["ring_count"]["value"],
        )
        frames = set(self.contract["required_interface_frames_per_variant"])
        self.assertTrue(
            {
                "crankshaft_axis",
                "main_journal_centres_01_to_08",
                "crankpin_centres_01_to_06",
                "rod_big_end_axis",
                "rod_small_end_axis",
                "piston_pin_axis",
                "piston_crown_datum",
                "piston_ring_groove_datums",
            }
            <= frames
        )
        self.assertEqual(
            self.contract["required_interface_frame_counts_per_variant"],
            EXPECTED_INTERFACE_FRAME_COUNTS,
        )
        self.assertEqual(sum(EXPECTED_INTERFACE_FRAME_COUNTS.values()), 99)

    def test_every_required_interface_frame_is_materialised_and_validated(self):
        for variant_id, variant in self.variants.items():
            with self.subTest(variant=variant_id):
                records = self.builder.interface_frame_records(variant, 17.0)
                self.assertEqual(len(records), 99)
                self.assertEqual(len({item["id"] for item in records}), 99)
                counts = {
                    family: sum(item["family"] == family for item in records)
                    for family in EXPECTED_INTERFACE_FRAME_COUNTS
                }
                self.assertEqual(counts, EXPECTED_INTERFACE_FRAME_COUNTS)
                self.assertTrue(all(item["physical_joint_enabled"] is False for item in records))
                self.assertTrue(
                    all(item["classification"] == "design_hypothesis_frame_not_measured" for item in records)
                )
                for item in records:
                    self.assertEqual(len(item["origin_mm"]), 3)
                    self.assertTrue(all(math.isfinite(value) for value in item["origin_mm"]))
                    self.assertTrue(math.isclose(math.dist(item["axis"], [0.0, 0.0, 0.0]), 1.0, abs_tol=1e-12))

                crank = next(item for item in records if item["id"] == "crankshaft_axis")
                self.assertEqual(crank["origin_mm"], [0.0, 0.0, 0.0])
                self.assertEqual(crank["axis"], [1.0, 0.0, 0.0])
                states = {
                    item["geometric_id"]: item
                    for item in self.builder.mechanism_state(variant, 17.0)
                }
                crown = variant["parameters"]["piston_crown_to_pin_axis_mm"]["value"]
                for geometric_id, state in states.items():
                    crown_frame = next(
                        item
                        for item in records
                        if item["id"] == f"piston_crown_datum_{geometric_id}"
                    )
                    bank_axis = self.builder.BANK_AXES[state["bank"]]
                    delta = [
                        crown_frame["origin_mm"][index] - state["piston_pin_center_mm"][index]
                        for index in range(3)
                    ]
                    self.assertTrue(
                        all(
                            math.isclose(
                                delta[index],
                                crown * bank_axis[index],
                                abs_tol=1.0e-12,
                            )
                            for index in range(3)
                        ),
                        (geometric_id, delta, bank_axis, crown),
                    )

    def test_cad_runtime_provenance_is_injected_by_the_actual_docker_invocation(self):
        digest = "1" * 64
        image_ref = f"ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:{digest}"
        with mock.patch.dict(os.environ, {"F35_CAD_RUNTIME_IMAGE_REF": image_ref}, clear=False):
            provenance = self.builder.cad_runtime_provenance()
        self.assertEqual(provenance["image_ref"], image_ref)
        self.assertEqual(provenance["digest"], f"sha256:{digest}")
        self.assertIn("docker_run_image_argument", provenance["evidence"])

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "immutable_cad_runtime_image_required"):
                self.builder.cad_runtime_provenance()
        with mock.patch.dict(
            os.environ,
            {"F35_CAD_RUNTIME_IMAGE_REF": "ghcr.io/cluster2600/3dprinting993-cad-author-f28:latest"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "immutable_cad_runtime_image_required"):
                self.builder.cad_runtime_provenance()

        source = SOURCE_PATH.read_text(encoding="utf-8")
        makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57", source)
        self.assertIn('-e F35_CAD_RUNTIME_IMAGE_REF="$(F35_CAD_AUTHOR_IMAGE)"', makefile)
        self.assertIn('$(F35_CAD_AUTHOR_IMAGE) \\\n', makefile)

    def test_output_policy_is_work_only_and_contains_no_private_inputs(self):
        policy = self.contract["output_policy"]
        output = Path(policy["generated_root"])
        self.assertFalse(output.is_absolute())
        self.assertNotIn("..", output.parts)
        self.assertEqual(output.parts[:1], ("work",))
        self.assertIs(policy["derived_artifacts_committed"], False)
        self.assertIs(policy["raw_scan_required"], False)
        self.assertIs(policy["raw_scan_in_output"], False)
        self.assertIs(policy["source_pdf_in_output"], False)
        self.assertIs(policy["private_absolute_paths_allowed"], False)
        self.assertEqual(set(policy["derived_formats"]), {"STEP", "STL", "JSON", "USD", "USDC"})
        self.assertEqual(
            policy["derived_output_layout"]["converted_usd_prototype"],
            "usd-conversion/{variant}/prototypes/{family}/{family}.usd",
        )
        self.assertEqual(
            policy["derived_output_layout"]["animated_usdc_stage"],
            "{variant}/usd/rotating-assembly-f35.usdc",
        )

    def test_cad_policy_keeps_the_static_review_non_physical(self):
        policy = self.contract["cad_policy"]
        self.assertEqual(policy["static_review_crank_angle_deg"], 17.0)
        self.assertEqual(policy["static_review_angle_classification"], "design_hypothesis")
        self.assertIn("arbitraire", policy["static_review_angle_note"])
        self.assertIs(policy["separate_variant_output_required"], True)
        self.assertIs(policy["analytical_linkage_closure_required"], True)
        self.assertIs(policy["physical_joint_authoring_allowed"], False)
        self.assertIs(policy["mass_or_inertia_assignment_allowed"], False)

    def test_every_physical_release_gate_is_false(self):
        gates = self.contract["release_gates"]
        self.assertEqual(len(gates), 17)
        self.assertTrue(gates)
        self.assertTrue(all(value is False for value in gates.values()))
        self.assertIs(gates["manufacturing_geometry_ready"], False)
        self.assertIs(gates["engine_start_authorized"], False)
        self.assertIs(gates["performance_1600_hp_claim_authorized"], False)

    def test_required_prohibitions_and_no_private_or_secret_payload(self):
        prohibited = set(self.contract["prohibited_use"])
        self.assertEqual(self.contract["prohibited_claims"], self.contract["prohibited_use"])
        self.assertTrue(
            {
                "historical_replica_claim",
                "claim_that_design_hypotheses_are_sourced_dimensions",
                "transfer_of_type_912_fia_dimensions_to_917_30_turbo",
                "manufacturing_or_metal_print_release",
                "engine_start_release",
                "claim_that_F35_proves_1600_hp",
            }
            <= prohibited
        )
        serialized = json.dumps(self.contract, sort_keys=True)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("raw-scans", serialized)
        self.assertNotRegex(serialized, re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"))
        self.assertNotIn("bao kv", serialized.lower())
        self.assertNotIn("base64,", serialized.lower())


if __name__ == "__main__":
    unittest.main()
