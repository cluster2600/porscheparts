"""UNRUN finite LINEAR source guards; no solver, data regeneration or field parser."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
PREP=Path(__file__).resolve().parent
OLD=PREP.parent/"cp1-oneway-cooling-release-prep-001"
DECK_SHA="de5c9ea62050645fb546fc650c01023913478c230011faa5172b76ffb36a4f7c"
ADAPTER_SHA="5ec0fe4684dd51dd7934ca3069e75497a481a08db5a9ee8a78646d81e3813f6c"
class Guards(unittest.TestCase):
    def test_exact_solver_delta_and_final_residual_options(self):
        old=(OLD/"thermoelastic-birth.i").read_text()
        new=(PREP/"thermoelastic-birth.i").read_text()
        before="  solve_type = NEWTON\n  petsc_options_iname = '-ksp_type -pc_type'\n  petsc_options_value = 'preonly lu'\n"
        after="  solve_type = LINEAR\n  petsc_options = '-snes_monitor'\n  petsc_options_iname = '-ksp_type -pc_type -snes_norm_schedule'\n  petsc_options_value = 'preonly lu always'\n"
        self.assertEqual(old.count(before),1)
        self.assertEqual(new,old.replace(before,after,1))
        self.assertEqual(hashlib.sha256(new.encode()).hexdigest(),DECK_SHA)
        self.assertNotIn("-snes_always_compute_final_residual",new)
    def test_literal_NEWTON_values_retained_but_inactive(self):
        new=(PREP/"thermoelastic-birth.i").read_text()
        for token in ["nl_rel_tol = 1e-11","nl_abs_tol = 1e-10","nl_max_its = 30","line_search = none"]:
            self.assertEqual(new.count(token),1)
        c=json.loads((PREP/"case-contract.json").read_text())["solver_profile"]
        self.assertIs(c["original_nonlinear_tolerance_test_active"],False)
        self.assertEqual(c["formulation"],"LINEAR")
        self.assertTrue(c["final_updated_solution_residual_callback_required"])
    def test_model_birth_support_and_capture_entire_deck_unchanged(self):
        old=(OLD/"thermoelastic-birth.i").read_text();new=(PREP/"thermoelastic-birth.i").read_text()
        self.assertEqual(old[:old.index("[Executioner]")],new[:new.index("[Executioner]")])
        self.assertEqual(old[old.index("[Outputs]"):],new[new.index("[Outputs]"):])
        for token in ["dt = 0.0025","end_time = 0.455","start_time = 0.4525"]:
            self.assertIn(token,new)
        self.assertIn("restore_overridden_dofs = 'true true true true false'",new)
        self.assertIn("save_in = 'rx ry rz'",new)
    def test_reuse_accepted_card_and_temperature_metadata_no_preparer(self):
        for name in ["card.json","thermal-input-index.json"]:
            self.assertEqual((PREP/name).read_bytes(),(OLD/name).read_bytes())
        self.assertFalse((PREP/"prepare_continuation.py").exists())
        h=json.loads((PREP/"held-preparation.json").read_text())
        self.assertEqual(h["accepted_data"]["table_sha256"],{"old-end.grid":"c64b252894a88730ad1f6ec0311cc5fe58a2cb3a8831f67e61db9d20be95823e","born-end.grid":"9caf52c69d0b14db442571b11d72252f3431d57b3991ab90ed849ddb6178b63f","born-begin80.grid":"cf4d9df9c8ab66aa37c40ef4e9cf3be44607229ff901201017eba0ba176cfbe4"})
        self.assertFalse(h["data_preparation_authorized"])
    def test_exact_adapter_schema_output_delta_and_all_other_functions(self):
        old=(OLD/"run_mac.py").read_text();new=(PREP/"run_mac.py").read_text()
        expected=old.replace("962-macos-oneway-cooling-release-case-actual/v1","962-macos-oneway-cooling-release-linear-case-actual/v1").replace('output == ENGINEERING / "cp1-oneway-cooling-release-001"','output == ENGINEERING / "cp1-oneway-cooling-release-linear-001"')
        self.assertEqual(new,expected)
        self.assertEqual(hashlib.sha256(new.encode()).hexdigest(),ADAPTER_SHA)
        trees=[{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)} for s in [old,new]]
        self.assertEqual(set(trees[0]),set(trees[1]))
        for name in trees[0]:
            if name!="checked_contract":self.assertEqual(trees[0][name],trees[1][name])
    def test_contract_card_deck_correction_and_seven_limits(self):
        c=json.loads((PREP/"case-contract.json").read_text())
        self.assertEqual(c["card"],json.loads((PREP/"card.json").read_text()))
        self.assertEqual(c["card_sha256"],hashlib.sha256((PREP/"card.json").read_bytes()).hexdigest())
        self.assertEqual(c["source_input_sha256"]["thermoelastic-birth.i"],DECK_SHA)
        self.assertIn("step80..182",c["capture"]["quadrature_fields"]["rule"])
        self.assertEqual(c["solver_profile"]["independent_SI_limits"],{"temperature_K":1e-10,"displacement_m":1e-12,"QP_coordinate_m":2e-13,"strain":1e-10,"stress_Pa":.1,"force_N":1e-7,"moment_Nm":1e-7})
    def test_historical_failure_and_fresh_run_reference(self):
        h=json.loads((PREP/"held-preparation.json").read_text())
        self.assertEqual(h["planned_native_output"],"work/962-engineering/cp1-oneway-cooling-release-linear-001")
        self.assertIsNone(h["native_actual"]);self.assertIsNone(h["native_output"]);self.assertIsNone(h["observed_results"])
        self.assertIn("result-peer-acceptance.json",h["original_failed_native"]["acceptance"]["path"])
        self.assertTrue(h["new_run_must_capture_own_BEGIN80_reference"])
        self.assertFalse(h["reuse_failed_native_fields_as_initial_or_birth_state"])
    def test_no_authority_and_original_resource_limits(self):
        h=json.loads((PREP/"held-preparation.json").read_text())
        self.assertEqual(h["coupon_resources"],{"wall_seconds":100,"sampled_RSS_stop_bytes":2147483648,"sampled_output_stop_bytes":536870912})
        self.assertEqual((h["controls"]["native_outer_seconds"],h["controls"]["native_TERM_grace_seconds"],h["controls"]["threads"]),(115,10,1))
        for key in ["native_launch_authorized","coupon_solve_authorized","guard_execution_authorized","automatic_retry","head_authorized","engineering_accepted","physics_qualified","material_qualified","process_calibrated","manufacturing_authorized"]:
            self.assertIs(h[key],False)
        self.assertIsNone(h["independent_3D_assessment"]["source"])
if __name__=="__main__":unittest.main()
