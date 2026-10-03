"""Stdlib checks of native D's registration, scheduling and fail-closed controls.

These are synthetic integrity fixtures. No MLX import, model load, GPU execution
or reserved question is involved.
"""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "training/qwen3-continuation-20261003"
SPEC = importlib.util.spec_from_file_location("qwen3_native_mlx_controls", PACKAGE / "mlx_run.py")
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)


class NativeControlsTest(unittest.TestCase):
    def test_warmup_is_zero_on_first_update_then_decays(self):
        rates = [native.learning_rate(update) for update in range(1, 11)]
        self.assertEqual(rates[0], 0)
        self.assertEqual(rates[1], 1e-5)
        self.assertAlmostEqual(rates[-1], 1e-5 / 9)
        self.assertTrue(all(left > right for left, right in zip(rates[1:], rates[2:])))
        for update in (0, 11, True):
            with self.subTest(update=update), self.assertRaises(ValueError):
                native.learning_rate(update)

    def test_predeclared_shuffle_preserves_all_rows(self):
        records = native.rows(PACKAGE / "data/train-records.jsonl")
        protocol = native.load(PACKAGE / "protocol-candidate-d.json")
        actual = native.shuffled_ids(records)
        self.assertEqual(actual, protocol["training"]["shuffled_row_ids"])
        self.assertEqual(set(actual), {record["id"] for record in records})
        self.assertEqual(len(actual), 20)
        with self.assertRaisesRegex(ValueError, "Duplicate training ID"):
            native.shuffled_ids([records[0], records[0]])

    def test_only_all_36_q_v_rank_matrix_keys_are_convertible(self):
        converted = {native.conversion_name(f"base_model.model.model.layers.{layer}.self_attn.{projection}_proj.lora_{matrix}.weight")
                     for layer in range(36) for projection in ("q", "v") for matrix in ("A", "B")}
        self.assertEqual(converted, native.expected_lora_keys())
        self.assertEqual(len(converted), 144)
        for key in ("base_model.model.model.layers.36.self_attn.q_proj.lora_A.weight",
                    "base_model.model.model.layers.0.self_attn.k_proj.lora_A.weight",
                    "base_model.model.model.layers.0.self_attn.q_proj.weight"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "adapter key"):
                native.conversion_name(key)

    def test_wrapper_names_map_to_original_frozen_tensor_names(self):
        self.assertEqual(native.canonical_base_name("model.layers.35.self_attn.v_proj.linear.weight"),
                         "model.layers.35.self_attn.v_proj.weight")
        self.assertEqual(native.canonical_base_name("model.embed_tokens.weight"), "model.embed_tokens.weight")

    def test_gpu_errors_quarantine_even_if_exit_status_would_be_zero(self):
        for message in ("[METAL] Command buffer exited with error status 5", "IOGPU restart", "MTLCommandBufferErrorDomain"):
            with self.subTest(message=message):
                self.assertTrue(native.gpu_error_detected(message))
        self.assertFalse(native.gpu_error_detected("All gradients finite; 10 updates completed."))

    def test_reserved_amendment_and_selection_pin_original_pool_and_candidate(self):
        cfg = {"experiment_id": "synthetic-D", "evaluation": {"minimum_rows": 24, "minimum_net_gain": 2}}
        registration = {"suite": "reserved", "independent_custodian": True, "roster": [{"id": "synthetic-roster-item"}], "questions_sha256": "questions"}
        amendment = {"original_reservation_sha256": "original-reserve", "protocol_sha256": "protocol-D",
                     "runner_sha256": "runner-D", "experiment_id": "synthetic-D",
                     "roster_sha256": native.object_sha(registration["roster"]), "questions_sha256": "questions",
                     "acceptance_rules_sha256": native.object_sha(cfg["evaluation"])}
        selection = {"decision": "selected_for_reserved_evaluation", "protocol_sha256": "protocol-D",
                     "runner_sha256": "runner-D", "adapter_sha256": "candidate-D",
                     "reservation_sha256": "original-reserve", "reservation_amendment_sha256": "amendment-D"}
        def verify(a=amendment, s=selection):
            native.validate_reserved(cfg, "protocol-D", registration, "original-reserve", a, "amendment-D", s, "candidate-D", "runner-D")
        verify()
        for key in amendment:
            changed = copy.deepcopy(amendment)
            changed[key] = "changed"
            with self.subTest(amendment_field=key), self.assertRaisesRegex(ValueError, "amendment D"):
                verify(a=changed)
        for key in selection:
            changed = copy.deepcopy(selection)
            changed[key] = "changed"
            with self.subTest(selection_field=key), self.assertRaisesRegex(ValueError, "selection"):
                verify(s=changed)

    def test_gate_rejects_missing_row_nonfinite_gradient_update_or_hardware_failure(self):
        records = [{"id": "synthetic-train-" + str(index)} for index in range(20)]
        cfg = {"initial_adapter_sha256": "original", "amendment_d": {"gate_probe_sha256": "probe"}}
        gate = {"status": "pass_without_optimizer_updates", "optimizer_updates": 0, "reserved_opened": False,
                "initial_adapter_sha256": "original", "runner_sha256": "probe", "precision_policy": native.POLICY,
                "libraries": {"mlx": "0.32.3", "mlx-lm": "0.31.3"}, "base_tensor_count": 398,
                "base_parameters": 4022468096, "tied_embeddings": True, "trainable_tensor_count": 144,
                "trainable_parameters": 2949120, "actual_trainable_dtypes": ["mlx.core.float32"],
                "rows": [{"id": record["id"], "all_144_gradients_finite": True, "loss": 1.0} for record in records]}
        supervisor = {"status": "completed", "exit_code": 0, "gpu_error_observed": False, "resource_stop": None}
        native.verify_gate(gate, supervisor, cfg, records)
        for mutate in (lambda g: g["rows"].pop(), lambda g: g["rows"][0].update(all_144_gradients_finite=False),
                       lambda g: g.update(optimizer_updates=1), lambda g: g["rows"][0].update(loss=float("nan"))):
            changed = copy.deepcopy(gate)
            mutate(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                native.verify_gate(changed, supervisor, cfg, records)
        for key, value in (("status", "failed"), ("exit_code", 137), ("gpu_error_observed", True), ("resource_stop", "swap_growth")):
            changed = {**supervisor, key: value}
            with self.subTest(supervisor_field=key), self.assertRaisesRegex(ValueError, "hardware/resource"):
                native.verify_gate(gate, changed, cfg, records)

    def test_registration_keeps_thresholds_and_explicit_fourth_authorization(self):
        d = native.load(PACKAGE / "protocol-candidate-d.json")
        original = native.load(PACKAGE / "protocol-cpu-registration.json")
        self.assertEqual(d["evaluation"], original["evaluation"])
        self.assertEqual(d["amendment_d"]["original_a_b_ceiling"], 2)
        self.assertEqual(d["amendment_d"]["candidate_c_authorized_number"], 3)
        self.assertEqual(d["amendment_d"]["candidate_d_authorized_number"], 4)
        self.assertFalse(d["amendment_d"]["reserved_tests_opened"])
        self.assertFalse(d["training"]["output_projection_fp32"])
        self.assertTrue(d["training"]["optimizer"]["bias_correction"])


if __name__ == "__main__":
    unittest.main()
