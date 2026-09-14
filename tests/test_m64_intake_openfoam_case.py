import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/m64-cylinder-head/source/flowbench-intake/prepare_openfoam_case.py"
SPEC = importlib.util.spec_from_file_location("m64_intake_openfoam_case", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
RUN_SPEC = importlib.util.spec_from_file_location("m64_intake_openfoam_runner", SOURCE.with_name("run_openfoam_pilot.py"))
RUN = importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(RUN)
POLICY = json.loads((ROOT / "twins/m64-cylinder-head/targets/intake-flowbench-pilot.json").read_text())


class IntakeOpenFOAMCaseTests(unittest.TestCase):
    def test_total_pressure_and_temperature_not_static_inlet(self):
        files = MOD.case_files(POLICY, 600)
        self.assertIn("type totalPressure; psi psi; gamma 1.4", files["0/p"])
        self.assertIn("p0 uniform 101325", files["0/p"])
        self.assertIn("value uniform 94350.51052", files["0/p"])
        self.assertIn("type totalTemperature", files["0/T"])
        self.assertIn("T0 uniform 293.15", files["0/T"])
        self.assertIn("type pressureInletOutletVelocity", files["0/U"])

    def test_compressible_energy_sst_and_all_wall_fields(self):
        files = MOD.case_files(POLICY, 600)
        self.assertIn("perfectGas", files["constant/physicalProperties"])
        self.assertIn("sensibleEnthalpy", files["constant/physicalProperties"])
        self.assertIn("1004.675", files["constant/physicalProperties"])
        self.assertIn("kOmegaSST", files["constant/momentumTransport"])
        self.assertIn("type noSlip", files["0/U"])
        self.assertIn("walls\n    {\n        type zeroGradient", files["0/T"])
        self.assertIn("type wall", files["system/createPatchDict"])

    def test_mass_flow_every_patch_not_only_outlet(self):
        control = MOD.case_files(POLICY, 600)["system/controlDict"]
        for patch in MOD.PATCHES:
            self.assertIn(f"massFlow_{patch}", control)
            self.assertIn(f"patch {patch}; operation orientedSum; fields (phi)", control)
        self.assertNotIn("residualControl", MOD.case_files(POLICY, 600)["system/fvSolution"])
        self.assertIn("default steadyState", MOD.case_files(POLICY, 600)["system/fvSchemes"])
        self.assertIn("type volFieldValue", control)
        self.assertIn("cellZone all", control)
        self.assertNotIn("fieldMinMax", control)

    def test_reject_unphysical_inputs_and_changed_scope(self):
        for key, value in (("inlet_total_pressure_Pa", float("nan")), ("air_gamma_for_reference_normalization", 1),
                           ("pressure_drop_inH2O_conventional", 1000), ("pilot_lift_mm", 2),
                           ("receiver_bore_mm", 105), ("air_gas_constant_J_kg_K", 0)):
            policy = copy.deepcopy(POLICY)
            policy["inputs"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                MOD.case_files(policy, 600)
        for n in (0, 5001, 2.5, True):
            with self.assertRaises(ValueError):
                MOD.case_files(POLICY, n)

    def test_mesh_format_is_not_geometry_qualification(self):
        # Header-only fixture: this function deliberately does not bless a mesh.
        text = ('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n4\n'
                '2 1 "inlet"\n2 2 "receiver_outlet"\n2 3 "walls"\n3 100 "air"\n$EndPhysicalNames\n')
        MOD.check_mesh_format(text)
        for changed in (text.replace("2.2 0", "2.2 1"), text.replace('"walls"', '"unknown"'),
                        text.replace('2 2 "receiver_outlet"', '2 1 "receiver_outlet"')):
            with self.assertRaises(ValueError):
                MOD.check_mesh_format(changed)

    def test_boundary_zero_unexpected_or_wrong_type_rejected(self):
        text = "inlet {type patch; nFaces 10;} receiver_outlet {type patch; nFaces 12;} walls {type wall; nFaces 120;}"
        self.assertEqual(RUN.boundary_contract(text)["walls"]["faces"], 120)
        for bad in (text.replace("nFaces 10", "nFaces 0"), text.replace("type wall", "type patch"),
                    text + "defaultFaces {type patch; nFaces 0;}", text + "inlet {type patch; nFaces 1;}"):
            with self.assertRaises(ValueError):
                RUN.boundary_contract(bad)

    def test_checkmesh_success_requires_explicit_statement(self):
        self.assertTrue(RUN.mesh_ok("Mesh OK.\nEnd"))
        for bad in ("End", "Failed 1 mesh checks.\nEnd", "Mesh OK.\nFOAM FATAL ERROR", "Mesh OK.\nFailed 2 mesh checks"):
            self.assertFalse(RUN.mesh_ok(bad))

    def test_gmsh_wall_type_changes_only_one_metadata_word(self):
        text = "inlet {type patch; nFaces 10;} receiver_outlet {type patch; nFaces 12;} walls {type patch; nFaces 120;}"
        changed = RUN.set_wall_patch_type(text)
        self.assertEqual(changed, text.replace("walls {type patch", "walls {type wall"))
        with self.assertRaises(ValueError):
            RUN.set_wall_patch_type(changed)

    def test_head_run_requires_exact_mesh_and_native_boundary_review(self):
        manifest = {"purpose": "head_pilot", "mesh_sha256": "1" * 64}
        receipt = {"schema": "m64-intake-pilot-review/v1", "approved_for_diagnostic_cfd": True,
                   "boundary_assignment_accepted": True, "mesh_sha256": "1" * 64,
                   "native_domain_sha256": "2" * 64}
        RUN.require_head_review(manifest, receipt)
        RUN.require_head_review({"purpose": "synthetic_runtime_smoke"}, None)
        for bad in (None, {}, {**receipt, "mesh_sha256": "3" * 64},
                    {**receipt, "boundary_assignment_accepted": False}, {**receipt, "native_domain_sha256": ""}):
            with self.assertRaises(ValueError):
                RUN.require_head_review(manifest, bad)

    def test_runtime_receipt_identifies_executed_sources_without_head_claims(self):
        head = ROOT / "twins/m64-cylinder-head"
        receipt = json.loads((head / "evidence/intake-openfoam-runtime-smoke-20260908.json").read_text())
        for relative, expected in receipt["source_sha256"].items():
            self.assertEqual(hashlib.sha256((head / relative).read_bytes()).hexdigest(), expected)
        claims = receipt["claims"]
        self.assertTrue(claims["synthetic_runtime_executed"])
        for key in ("head_CFD_executed", "head_mesh_qualified", "poly_dual_qualified",
                    "convergence_demonstrated", "thermal_head_validation",
                    "mechanical_validation", "manufacturing_authorized"):
            self.assertIs(claims[key], False)
        self.assertIsNone(claims["head_mass_flow_kg_s"])
        self.assertIsNone(claims["engine_power_PS"])
        self.assertEqual(len(receipt["rejected_attempts_preserved"]), 6)


if __name__ == "__main__":
    unittest.main()
