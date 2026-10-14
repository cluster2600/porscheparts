import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/"models/917-engine-reconstruction/fia"
SPEC = importlib.util.spec_from_file_location("fia917",HERE/"run.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FIAReferenceTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((HERE/"reference-assumptions.json").read_text())
        self.review = json.loads((HERE/"source-review.json").read_text())

    def test_documentary_height_exposes_previous_provisional_barrel_mismatch(self):
        d = MODULE.validate_reference(self.config,self.review)
        self.assertEqual(d["piston_height"]/2,43)
        self.assertEqual(d["crankpin_diameter"],52)
        self.assertEqual(d["rod_big_bore"],54)
        result = MODULE.PROTOTYPE.motion_report(self.config)
        self.assertEqual([r["minimum_axial_skirt_coverage_residual_mm"] for r in result["rod_length_sensitivity"]],[-26,-16,-28])
        self.assertFalse(any(r["hypothesis_consistent_with_full_skirt_coverage"] for r in result["rod_length_sensitivity"]))

    def test_dimension_substitution_and_extension_transfer_are_rejected(self):
        for key,value in (("bore",86),("stroke",70.4),("piston_pin_axis_to_crown",22),("crankpin_diameter",40),
                          ("rod_big_bore",56),("piston_height",77),("rod_length",130)):
            config = copy.deepcopy(self.config);config["dimensions_mm"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):MODULE.validate_reference(config,self.review)

    def test_review_cannot_override_existing_fia_registry_or_promote_ambiguous_dimension(self):
        for key,value in (("pin_axis_to_crown",44),("rod_mass",float("nan"))):
            config,review = copy.deepcopy(self.config),copy.deepcopy(self.review)
            review["facts"][key]["value"]=value
            if key=="pin_axis_to_crown":
                config["dimensions_mm"].update(piston_pin_axis_to_crown=44,piston_skirt_below_pin=44,piston_height=88)
            with self.assertRaises(ValueError):MODULE.validate_reference(config,review)
        review = copy.deepcopy(self.review);review["ambiguous_excluded"]["geometry_binding_allowed"]=True
        with self.assertRaises(ValueError):MODULE.validate_reference(self.config,review)

    def test_mass_envelope_preserves_group_scope_and_declared_interval(self):
        rows = MODULE.documentary_mass_cases(self.config,self.review)
        self.assertEqual(len(rows),9)
        case = rows[-1]
        self.assertAlmostEqual(case["documentary_reciprocating_mass_kg"],.6)
        self.assertAlmostEqual(case["declared_mass_bound_kg"][0],.6-.02-.02/3)
        self.assertAlmostEqual(case["declared_mass_bound_kg"][1],.6+.02+.02/3)
        self.assertAlmostEqual(case["gas_force_N"],80e5*math.pi/4*.085**2)
        self.assertLess(case["independent_peak_sum_bound_N"][0],case["gas_force_N"]+case["nominal_peak_inertia_N"])
        self.assertGreater(case["independent_peak_sum_bound_N"][1],case["gas_force_N"]+case["nominal_peak_inertia_N"])

    def test_execution_binds_reviewed_inputs_without_promoting_geometry_or_material(self):
        record = json.loads((HERE/"execution-20261011.json").read_text())
        for name,value in record["fia_input_sha256"].items():
            self.assertEqual(value,hashlib.sha256((HERE/name).read_bytes()).hexdigest())
        for name,value in record["source_sha256"].items():
            self.assertEqual(value,hashlib.sha256((MODULE.PROTOTYPE.HERE/name).read_bytes()).hexdigest())
        self.assertEqual(record["fia_reference"],self.review)
        self.assertFalse(record["geometry_coverage_criterion_pass"])
        self.assertFalse(any(record["release_gates"].values()))
        self.assertFalse(record["reused_generator_modified"])
        self.assertFalse(record["geometry_and_pdf_payload_published"])
        self.assertEqual(record["documentary_mass_cases"],MODULE.documentary_mass_cases(self.config,self.review))


if __name__ == "__main__":
    unittest.main()
