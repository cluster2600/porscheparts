"""Bounded official native MLX candidate D, with no downloads or installation.

Run the supervisor with the existing Torch environment (psutil), supplying the
existing official MLX interpreter through --mlx-python. Model operations only
occur in its child. All candidate and scientific controls use the same native
BF16 tied-base/FP32-LoRA policy; PEFT functional parity is not claimed.
"""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_PROTOCOL = HERE / "protocol-candidate-d.json"
OLD = ROOT / "training/qwen-metal-additive-20261002"
PACK = OLD / "runs/qwen3-fidelity-001"
POLICY = "Native MLX BF16 tied base with FP32 LoRA; official delta cast before addition differs from PEFT; no cross-runtime parity claimed"
ROSTER_KEYS = ("id", "suite", "source_family", "critical", "input_sha256")
BASE_TENSORS, BASE_PARAMETERS = 398, 4022468096
LORA_TENSORS, LORA_PARAMETERS = 144, 2949120


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def helper(name):
    spec = importlib.util.spec_from_file_location("_qwen3_d_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def learning_rate(update, total=10, peak=1e-5):
    """One warmup step: update1=0, update2=peak, update10=peak/9."""
    require(type(update) is int and 1 <= update <= total and total > 1, "Invalid optimizer update")
    return 0.0 if update == 1 else peak * (total - update + 1) / (total - 1)


def shuffled_ids(records, seed=42):
    identifiers = [record["id"] for record in records]
    require(len(set(identifiers)) == len(identifiers), "Duplicate training ID")
    random.Random(seed).shuffle(identifiers)
    return identifiers


def conversion_name(name):
    match = re.fullmatch(r"base_model\.model\.model\.layers\.(\d+)\.self_attn\.([qv])_proj\.lora_([AB])\.weight", name)
    require(match is not None and 0 <= int(match[1]) < 36, "Unexpected historical adapter key")
    return "model.layers." + match[1] + ".self_attn." + match[2] + "_proj.lora_" + match[3].lower()


def expected_lora_keys():
    return {f"model.layers.{layer}.self_attn.{projection}_proj.lora_{matrix}"
            for layer in range(36) for projection in ("q", "v") for matrix in ("a", "b")}


def gpu_error_detected(text):
    lowered = text.lower()
    return any(marker in lowered for marker in ("command buffer exited with error", "iogpu", "metal device error",
                                                "mtlcommandbuffererror", "gpu execution error", "gpu restart"))


def verify_gate(gate, supervisor, cfg, records):
    require(gate.get("status") == "pass_without_optimizer_updates" and gate.get("optimizer_updates") == 0,
            "All-training native gate is incomplete or updated weights")
    require(gate.get("reserved_opened") is False, "Gate opened reserved evaluation")
    require(gate["initial_adapter_sha256"] == cfg["initial_adapter_sha256"], "Gate used another warm start")
    require(gate["runner_sha256"] == cfg["amendment_d"]["gate_probe_sha256"], "Gate used another probe")
    require(gate["precision_policy"] == POLICY, "Gate numeric policy differs")
    require(gate["libraries"]["mlx"] == "0.32.3" and gate["libraries"]["mlx-lm"] == "0.31.3", "Gate used other native libraries")
    require(gate["base_tensor_count"] == BASE_TENSORS and gate["base_parameters"] == BASE_PARAMETERS and
            gate["tied_embeddings"] is True, "Gate base identity differs")
    require(gate["trainable_tensor_count"] == LORA_TENSORS and gate["trainable_parameters"] == LORA_PARAMETERS and
            gate["actual_trainable_dtypes"] == ["mlx.core.float32"], "Gate LoRA identity differs")
    require([item["id"] for item in gate["rows"]] == [record["id"] for record in records], "Gate must cover all twenty rows in original order")
    require(len(gate["rows"]) == 20 and all(item["all_144_gradients_finite"] is True and
            isinstance(item["loss"], (int, float)) and math.isfinite(item["loss"]) for item in gate["rows"]), "Gate loss or gradients failed")
    require(supervisor.get("status") == "completed" and supervisor.get("exit_code") == 0 and
            supervisor.get("gpu_error_observed") is False and supervisor.get("resource_stop") is None,
            "Gate supervisor reported a hardware/resource failure")


def verify_registration(cfg, protocol_path):
    require(cfg["experiment_id"] == "qwen3-scientific-continuation-20261003-d" and cfg["native_policy"] == POLICY,
            "Unregistered native candidate")
    require(cfg["runner_sha256"] == sha(Path(__file__)), "Native runner changed after registration")
    for name, digest in cfg["source_scripts_sha256"].items():
        require(sha(HERE / name) == digest, "Pinned preparation helper changed: " + name)
    require(cfg["model_id"] == "Qwen/Qwen3-4B-Instruct-2507" and
            cfg["revision"] == "cdbee75f17c01a7cc42f958dc650907174af0554", "Other model family/revision")
    require(cfg["training"]["epochs"] == 1 and cfg["training"]["gradient_accumulation_steps"] == 2 and
            cfg["training"]["optimizer_steps"] == 10 and cfg["training"]["max_optimizer_steps"] == 12,
            "Other native optimizer budget")
    require(cfg["decoding"] == {"do_sample": False, "max_new_tokens": 192}, "Other decoding policy")
    helper("audit").verify_profile(ROOT, cfg)
    require(sha(HERE / "data/manifest.json") == cfg["data_manifest_sha256"], "Prepared data manifest changed")
    require(sha(HERE / "data/train-records.jsonl") == cfg["train_records_sha256"], "Prepared training data changed")
    require(sha(PACK / "adapter/adapter_model.safetensors") == cfg["initial_adapter_sha256"], "Historical adapter changed")
    return sha(protocol_path)


def inventory(cfg):
    import mlx.core as mx
    import mlx_lm.models.qwen3 as model_module
    import mlx_lm.sample_utils as sample_module
    import mlx_lm.tuner.lora as lora_module
    import mlx_lm.tuner.trainer as trainer_module
    import mlx_lm.tuner.utils as tuner_module
    import mlx_lm.utils as load_module
    import mlx.optimizers.optimizers as optimizer_module
    modules = (model_module, sample_module, lora_module, trainer_module, tuner_module, load_module, optimizer_module)
    # The package exports a generate function; use the source module explicitly.
    generate_path = Path(importlib.util.find_spec("mlx_lm.generate").origin)
    return {"python": sys.version, "platform": sys.platform,
            "libraries": {name: importlib.metadata.version(name) for name in ("mlx", "mlx-lm", "transformers", "tokenizers", "numpy")},
            "source_sha256": {module.__name__: sha(module.__file__) for module in modules} | {"mlx_lm.generate": sha(generate_path)},
            "mlx_native_extension_sha256": sha(mx.__file__), "device": str(mx.default_device()),
            "device_info": mx.device_info(), "numeric_policy": POLICY, "runner_sha256": sha(Path(__file__)),
            "cpu_threads_target": 2, "cpu_threads_scope": "Environment target only; actual CPU utilization recorded by supervisor",
            "nice": os.getpriority(os.PRIO_PROCESS, 0), "memory_limits": cfg["resources"]}


def canonical_base_name(name):
    return re.sub(r"\.([qv]_proj)\.linear\.", r".\1.", name)


def frozen_signature(model):
    """Stream exact native BF16 bits of every frozen base tensor in row chunks."""
    import mlx.core as mx
    import numpy as np
    from mlx.utils import tree_flatten
    base = [(canonical_base_name(name), value) for name, value in tree_flatten(model.parameters())
            if not name.endswith((".lora_a", ".lora_b"))]
    require(len(base) == BASE_TENSORS and sum(value.size for _, value in base) == BASE_PARAMETERS,
            "Frozen base tensor count differs")
    require(len({name for name, _ in base}) == BASE_TENSORS and all(value.dtype == mx.bfloat16 for _, value in base),
            "Frozen base keys or native BF16 dtypes differ")
    require(model.args.tie_word_embeddings is True and "lm_head" not in model, "Native tied output was replaced")
    proof = {}
    for name, value in sorted(base):
        digest = hashlib.sha256()
        for start in range(0, value.shape[0], 1024):
            bits = value[start:start + 1024].view(mx.uint16)
            mx.eval(bits)
            digest.update(np.asarray(bits).tobytes(order="C"))
        proof[name] = {"shape": list(value.shape), "dtype": str(value.dtype), "raw_bf16_sha256": digest.hexdigest()}
    require("model.embed_tokens.weight" in proof, "Embedding tensor missing")
    return {"tensor_count": BASE_TENSORS, "parameters": BASE_PARAMETERS, "tied_embeddings": True,
            "embedding_raw_sha256": proof["model.embed_tokens.weight"]["raw_bf16_sha256"],
            "tensors": proof, "signature_sha256": object_sha(proof)}


def finite_tree(tree, expected):
    import mlx.core as mx
    from mlx.utils import tree_flatten
    flattened = dict(tree_flatten(tree))
    require(set(flattened) == set(expected) and len(flattened) == LORA_TENSORS, "Missing or excess trainable gradients/parameters")
    checks = mx.stack([mx.all(mx.isfinite(value)) for value in flattened.values()])
    mx.eval(checks)
    require(bool(mx.all(checks).item()), "Nonfinite native trainable gradient/parameter")
    require(all(value.dtype == mx.float32 for value in flattened.values()), "Trainable tensor dtype is not FP32")
    return flattened


def convert_original(model):
    import mlx.core as mx
    import numpy as np
    from mlx.utils import tree_flatten, tree_unflatten
    from mlx_lm.tuner.utils import linear_to_lora_layers
    model.freeze()
    require(not tree_flatten(model.trainable_parameters()), "Base freeze failed before wrapping")
    linear_to_lora_layers(model, 36, {"rank": 8, "scale": 2.0, "dropout": .05,
                                    "keys": ["self_attn.q_proj", "self_attn.v_proj"]})
    originals = mx.load(str(PACK / "adapter/adapter_model.safetensors"))
    converted, proof = {}, []
    for name, value in sorted(originals.items()):
        target_name = conversion_name(name)
        require(value.dtype == mx.float32, "Historical LoRA tensor must be FP32")
        target = value.T
        original_bytes = np.asarray(value).tobytes(order="C")
        require(np.asarray(target.T).tobytes(order="C") == original_bytes, "LoRA transpose changed raw FP32 bytes")
        converted[target_name] = target
        proof.append({"original_name": name, "mlx_name": target_name, "original_shape": list(value.shape),
                      "mlx_shape": list(target.shape), "original_raw_sha256": hashlib.sha256(original_bytes).hexdigest(),
                      "roundtrip_raw_sha256": hashlib.sha256(np.asarray(target.T).tobytes(order="C")).hexdigest(),
                      "exact_transpose": True, "dtype": str(value.dtype)})
    require(set(converted) == expected_lora_keys() and len(converted) == LORA_TENSORS and
            sum(value.size for value in converted.values()) == LORA_PARAMETERS, "Historical adapter key/count mismatch")
    require(set(dict(tree_flatten(model.trainable_parameters()))) == set(converted), "LoRA wrappers expose other trainable parameters")
    model.update(tree_unflatten(list(converted.items())))
    mx.eval(model.parameters())
    finite_tree(model.trainable_parameters(), converted)
    model.eval()
    delta_checks = []
    for layer in range(36):
        for projection in ("q", "v"):
            wrapper = getattr(model.layers[layer].self_attn, projection + "_proj")
            require(wrapper.scale == 2.0 and math.isclose(1 - wrapper.dropout._p_1, .05, abs_tol=1e-12),
                    "Native LoRA scale/dropout differs")
            stem = f"base_model.model.model.layers.{layer}.self_attn.{projection}_proj."
            a, b = originals[stem + "lora_A.weight"], originals[stem + "lora_B.weight"]
            x = mx.linspace(-.2, .2, wrapper.lora_a.shape[0], dtype=mx.float32)[None, :].astype(mx.bfloat16)
            expected_delta = ((x.astype(mx.float32) @ a.T) @ b.T) * 2.0
            actual_delta = ((wrapper.dropout(x) @ wrapper.lora_a) @ wrapper.lora_b) * wrapper.scale
            expected_forward = wrapper.linear(x) + expected_delta.astype(x.dtype)
            checks = mx.stack([mx.all(actual_delta == expected_delta), mx.all(wrapper(x) == expected_forward)])
            mx.eval(checks)
            require(bool(mx.all(checks).item()), "Native LoRA differential scale/orientation check failed")
            delta_checks.append({"layer": layer, "projection": projection, "delta_equal": True, "native_forward_equal": True})
    return converted, {"matrix_count": LORA_TENSORS, "trainable_parameters": LORA_PARAMETERS,
                       "rank": 8, "scale": 2.0, "dropout": .05, "matrices": proof,
                       "differential_checks": delta_checks, "cross_runtime_functional_parity_claim": False}


def prepare(args, cfg):
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from mlx_lm import load as mlx_load
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(cfg["resources"]["mlx_active_limit_bytes"])
    mx.set_cache_limit(cfg["resources"]["mlx_cache_limit_bytes"])
    mx.random.seed(cfg["training"]["seed"])
    baseline = helper("run")
    files = baseline.verify_snapshot(args.snapshot)
    config = load(args.snapshot / "config.json")
    require(not config.get("quantization") and not config.get("quantization_config"), "Quantized model is forbidden")
    model, tokenizer = mlx_load(str(args.snapshot), tokenizer_config={"trust_remote_code": False})
    runtime = inventory(cfg)
    require(runtime["libraries"]["mlx"] == "0.32.3" and runtime["libraries"]["mlx-lm"] == "0.31.3", "Unregistered native libraries")
    require(hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() ==
            load(OLD / "compact-qwen3-v5/model-profile.json")["chat_template_sha256"], "Tokenizer template differs")
    parameters = tree_flatten(model.parameters())
    require(len(parameters) == BASE_TENSORS and sum(value.size for _, value in parameters) == BASE_PARAMETERS and
            all(value.dtype == mx.bfloat16 for _, value in parameters), "Native base tensor identity differs")
    before = frozen_signature(model)
    require(before["embedding_raw_sha256"] == cfg["expected_embedding_raw_sha256"], "Official input embedding BF16 bytes differ")
    save(args.output / "frozen-base-before.json", before)
    converted, proof = convert_original(model)
    save(args.output / "conversion-receipt.json", proof)
    require(frozen_signature(model)["signature_sha256"] == before["signature_sha256"], "Wrapping changed frozen base bits")
    return model, tokenizer, files, converted, before, proof, runtime


def save_adapter(model, directory, cfg, expected, step):
    import mlx.core as mx
    import numpy as np
    directory.mkdir(parents=True, exist_ok=False)
    tensors = finite_tree(model.trainable_parameters(), expected)
    mx.save_safetensors(str(directory / "adapters.safetensors"), tensors)
    loaded = mx.load(str(directory / "adapters.safetensors"))
    finite_tree(loaded, expected)
    require(all(np.asarray(loaded[name]).tobytes() == np.asarray(tensors[name]).tobytes() for name in expected),
            "Saved adapter bytes differ")
    save(directory / "adapter_config.json", {"fine_tune_type": "lora", "num_layers": 36,
         "lora_parameters": {"rank": 8, "scale": 2.0, "dropout": .05, "keys": ["self_attn.q_proj", "self_attn.v_proj"]},
         "model_id": cfg["model_id"], "revision": cfg["revision"], "native_policy": POLICY})
    return {"step": step, "adapter_sha256": sha(directory / "adapters.safetensors"),
            "adapter_config_sha256": sha(directory / "adapter_config.json"), "all_144_tensors_finite": True}


def train(args, cfg, protocol_hash):
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx.utils import tree_map
    from mlx_lm.tuner.trainer import grad_checkpoint
    baseline = helper("run")
    helper("audit").audit_data(HERE)
    records = rows(HERE / "data/train-records.jsonl")
    require(len(records) == 20 and shuffled_ids(records) == cfg["training"]["shuffled_row_ids"], "Predeclared row order differs")
    require(sha(args.gate_receipt) == cfg["amendment_d"]["gate_receipt_sha256"] and
            sha(args.gate_supervisor) == cfg["amendment_d"]["gate_supervisor_sha256"], "Native gate receipts changed")
    verify_gate(load(args.gate_receipt), load(args.gate_supervisor), cfg, records)
    gate_log = args.gate_supervisor.parent / "worker.log"
    require(sha(gate_log) == load(args.gate_supervisor)["log_sha256"] and
            not gpu_error_detected(gate_log.read_text(encoding="utf-8", errors="replace")), "Native gate hardware log changed or failed")
    started = time.monotonic()
    model, tokenizer, files, original, before, conversion, runtime = prepare(args, cfg)
    require(load(args.gate_receipt)["model_files_sha256"] == files, "Gate source snapshot differs")
    grad_checkpoint(model.layers[0])
    optimizer = optim.AdamW(learning_rate=0.0, betas=[.9, .999], eps=1e-8, weight_decay=0.0, bias_correction=True)

    def loss_fn(model, inputs, labels):
        logits = model(inputs).astype(mx.float32)
        mask = labels >= 0
        targets = mx.where(mask, labels, 0)
        return mx.sum(nn.losses.cross_entropy(logits, targets, reduction="none") * mask) / mx.sum(mask)

    value_and_grad = nn.value_and_grad(model, loss_fn)
    by_id = {record["id"]: record for record in records}
    history, checkpoints, accumulation, step = [], [], None, 0
    receipt = {"status": "training", "protocol_sha256": protocol_hash, "runner_sha256": sha(Path(__file__)),
               "model_id": cfg["model_id"], "revision": cfg["revision"], "runtime": runtime,
               "native_policy": POLICY, "initial_adapter_sha256": cfg["initial_adapter_sha256"],
               "model_files_sha256": files, "data_manifest_sha256": cfg["data_manifest_sha256"],
               "gate_receipt_sha256": sha(args.gate_receipt), "optimizer_steps": 0,
               "scientific_gain_demonstrated": False, "reserved_test_opened": False}
    save(args.output / "training-receipt.json", receipt)
    for index, identifier in enumerate(cfg["training"]["shuffled_row_ids"]):
        require(time.monotonic() - started < cfg["training"]["deadline_seconds"], "Native training deadline exceeded")
        record = by_id[identifier]
        tokenized = baseline.supervised_tokens(record, tokenizer)
        require(any(label >= 0 for label in tokenized["labels"][1:]), "No assistant/EOS target")
        x = mx.array([tokenized["input_ids"][:-1]], dtype=mx.int32)
        y = mx.array([tokenized["labels"][1:]], dtype=mx.int32)
        model.train()
        tick = time.monotonic()
        value, gradients = value_and_grad(model, x, y)
        mx.eval(value, gradients)
        require(math.isfinite(value.item()), "Nonfinite native training loss")
        finite_tree(gradients, original)
        accumulation = gradients if accumulation is None else tree_map(lambda a, b: a + b, accumulation, gradients)
        item = {"id": identifier, "sequence_tokens": len(tokenized["input_ids"]), "loss": value.item(),
                "all_144_gradients_finite": True, "seconds": time.monotonic() - tick}
        if (index + 1) % 2 == 0:
            averaged = tree_map(lambda value: value / 2.0, accumulation)
            finite_tree(averaged, original)
            clipped, norm = optim.clip_grad_norm(averaged, max_norm=1.0)
            mx.eval(norm, clipped)
            require(math.isfinite(norm.item()), "Nonfinite native gradient norm")
            finite_tree(clipped, original)
            finite_tree(model.trainable_parameters(), original)
            step += 1
            require(step <= cfg["training"]["max_optimizer_steps"], "Native optimizer step ceiling exceeded")
            lr = learning_rate(step, 10, cfg["training"]["learning_rate"])
            optimizer.learning_rate = lr
            updated = optimizer.apply_gradients(clipped, model.trainable_parameters())
            finite_tree(updated, original)
            model.update(updated)
            mx.eval(model.trainable_parameters(), optimizer.state)
            finite_tree(model.trainable_parameters(), original)
            require(int(optimizer.step.item()) == step, "Native optimizer step mismatch")
            item.update(optimizer_step=step, learning_rate=lr, pre_clip_global_norm=norm.item(),
                        all_144_gradients_finite_before_update=True)
            if step in (4, 8):
                checkpoints.append(save_adapter(model, args.output / "checkpoints" / f"step-{step:04d}", cfg, original, step))
            accumulation = None
            del averaged, clipped, updated
        history.append(item)
        receipt.update(optimizer_steps=step, seconds=time.monotonic() - started)
        save(args.output / "trainer-history.json", history)
        save(args.output / "training-receipt.json", receipt)
        save(args.output / "status.json", {"status": "training", "optimizer_steps": step, "row": identifier})
        del value, gradients, x, y
        mx.clear_cache()
    require(step == 10 and accumulation is None, "Incomplete native epoch")
    final = save_adapter(model, args.output / "adapter", cfg, original, step)
    after = frozen_signature(model)
    save(args.output / "frozen-base-after.json", after)
    require(after["signature_sha256"] == before["signature_sha256"], "Native training modified frozen base bits")
    receipt.update(status="trained_integrity_verified_not_selected_or_evaluated", adapter_sha256=final["adapter_sha256"],
                   adapter_config_sha256=final["adapter_config_sha256"], frozen_integrity_verified=True,
                   frozen_signature_sha256=before["signature_sha256"], embedding_raw_sha256=before["embedding_raw_sha256"],
                   checkpoints=checkpoints + [final], rows=20, optimizer_steps=step, seconds=time.monotonic() - started,
                   active_memory_bytes=mx.get_active_memory(), peak_mlx_memory_bytes=mx.get_peak_memory(),
                   optimizer_config=cfg["training"]["optimizer"], conversion_receipt_sha256=sha(args.output / "conversion-receipt.json"))
    save(args.output / "training-receipt.json", receipt)
    save(args.output / "status.json", {"status": receipt["status"], "optimizer_steps": step})


def validate_reserved(cfg, protocol_hash, registration, registration_hash, amendment, amendment_hash,
                      selection, candidate_sha, runner_hash):
    require(registration.get("suite") == "reserved" and registration.get("independent_custodian") is True,
            "Independent original reservation required")
    require(amendment.get("original_reservation_sha256") == registration_hash and
            amendment.get("protocol_sha256") == protocol_hash and amendment.get("runner_sha256") == runner_hash and
            amendment.get("experiment_id") == cfg["experiment_id"] and
            amendment.get("roster_sha256") == object_sha(registration["roster"]) and
            amendment.get("questions_sha256") == registration["questions_sha256"] and
            amendment.get("acceptance_rules_sha256") == object_sha(cfg["evaluation"]), "Reserved amendment D binding differs")
    require(selection.get("decision") == "selected_for_reserved_evaluation" and
            selection.get("protocol_sha256") == protocol_hash and selection.get("runner_sha256") == runner_hash and
            selection.get("adapter_sha256") == candidate_sha and selection.get("reservation_sha256") == registration_hash and
            selection.get("reservation_amendment_sha256") == amendment_hash, "Reserved selection is not frozen to candidate D")


def evaluate(args, cfg, protocol_hash):
    import mlx.core as mx
    from mlx.utils import tree_unflatten
    from mlx_lm import stream_generate
    from mlx_lm.sample_utils import make_sampler
    registration = load(args.registration)
    candidate_sha = sha(args.adapter / "adapters.safetensors")
    suite = registration["suite"]
    require(suite in ("development", "reserved"), "Unregistered evaluation suite")
    if suite == "reserved":
        require(not args.historical_control, "Historical three-arm control is development only")
        require(args.selection is not None and args.reservation_amendment is not None, "Reserved D requires selection and reservation amendment")
        validate_reserved(cfg, protocol_hash, registration, sha(args.registration), load(args.reservation_amendment),
                          sha(args.reservation_amendment), load(args.selection), candidate_sha, sha(Path(__file__)))
    require(sha(args.questions) == registration["questions_sha256"], "Questions changed after registration")
    questions = rows(args.questions)
    roster = [{key: question[key] for key in ROSTER_KEYS} for question in questions]
    require(roster == registration["roster"] and object_sha(roster) == registration["roster_sha256"], "Evaluation roster changed")
    audit = helper("audit")
    for question in questions:
        require(object_sha(question["messages"]) == question["input_sha256"], "Evaluation input hash differs")
        require(audit.expanded_messages(OLD, question)[0] == question["messages"], "Evaluation profile expansion differs")
    started = time.monotonic()
    model, tokenizer, files, original, before, conversion, runtime = prepare(args, cfg)
    candidate = mx.load(str(args.adapter / "adapters.safetensors"))
    finite_tree(candidate, original)
    require(load(args.adapter / "adapter_config.json")["native_policy"] == POLICY, "Candidate uses another native policy")
    train_receipt = load(args.adapter.parent / "training-receipt.json")
    require(train_receipt["protocol_sha256"] == protocol_hash and train_receipt["runner_sha256"] == sha(Path(__file__)) and
            train_receipt["adapter_sha256"] == candidate_sha and train_receipt["frozen_integrity_verified"] is True and
            train_receipt["frozen_signature_sha256"] == before["signature_sha256"], "Candidate training integrity/identity differs")
    require(load(args.adapter.parent / "supervisor-receipt.json")["status"] == "completed", "Candidate runtime was quarantined")
    train_log = args.adapter.parent / "worker.log"
    require(sha(train_log) == load(args.adapter.parent / "supervisor-receipt.json")["log_sha256"] and
            not gpu_error_detected(train_log.read_text(encoding="utf-8", errors="replace")), "Candidate hardware log changed or failed")
    wrappers = {f"model.layers.{layer}.self_attn.{projection}_proj": getattr(model.layers[layer].self_attn, projection + "_proj")
                for layer in range(36) for projection in ("q", "v")}
    require(len(wrappers) == 72, "Incorrect LoRA wrapper roster")
    runtime_hash = object_sha(runtime)
    roles = ("base", "historical_adapter", "adapter") if args.historical_control else ("base", "adapter")
    for role in roles:
        if role == "base":
            model.update_modules(tree_unflatten([(name, wrapper.linear) for name, wrapper in wrappers.items()]))
        else:
            model.update_modules(tree_unflatten(list(wrappers.items())))
            model.update(tree_unflatten(list((original if role == "historical_adapter" else candidate).items())))
        model.eval()
        results = []
        for question in questions:
            tick = time.monotonic()
            prompt = tokenizer.apply_chat_template(question["messages"], tokenize=True, add_generation_prompt=True, enable_thinking=False)
            segments, token_ids, last = [], [], None
            for chunk in stream_generate(model, tokenizer, prompt=prompt, max_tokens=192, sampler=make_sampler(temp=0.0)):
                segments.append(chunk.text)
                token_ids.append(int(chunk.token))
                last = chunk
            require(last is not None and last.finish_reason in ("stop", "length"), "Incomplete native generation")
            require(last.generation_tokens == len(token_ids) and 0 < len(token_ids) <= 192, "Native generation token count mismatch")
            response = "".join(segments).strip()
            eos = last.finish_reason == "stop"
            require(not eos or int(last.token) in tokenizer.eos_token_ids, "Native EOS metadata differs")
            results.append({**{key: question[key] for key in (*ROSTER_KEYS, "source_id", "messages")},
                            "response": response, "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
                            "generated_tokens": len(token_ids), "generated_token_ids": token_ids, "eos_reached": eos,
                            "finish_reason": last.finish_reason, "budget_hit": last.finish_reason == "length",
                            "prompt_tokens": last.prompt_tokens, "seconds": time.monotonic() - tick})
            save(args.output / (role + ".partial.json"), {"status": "partial", "model_role": role, "rows": results})
            print(json.dumps({"arm": role, "id": question["id"], "tokens": len(token_ids), "seconds": time.monotonic() - tick}), flush=True)
            mx.clear_cache()
        integrity = frozen_signature(model)
        require(integrity["signature_sha256"] == before["signature_sha256"], "Generation modified frozen base bits")
        save(args.output / (role + "-frozen-integrity.json"), integrity)
        run = {"schema_version": 1, "status": "completed", "model_role": role, "suite": suite,
               "model_id": cfg["model_id"], "revision": cfg["revision"], "profile_name": cfg["inference_profile"],
               "decoding": cfg["decoding"], "rows": results, "protocol_sha256": protocol_hash,
               "runner_sha256": sha(Path(__file__)), "original_reservation_sha256": sha(args.registration),
               "reservation_sha256": sha(args.registration), "roster_sha256": object_sha(roster),
               "reservation_amendment_sha256": sha(args.reservation_amendment) if args.reservation_amendment else None,
               "adapter_sha256": cfg["initial_adapter_sha256"] if role == "historical_adapter" else candidate_sha,
               "selection_receipt_sha256": sha(args.selection) if args.selection else None,
               "model_files_sha256": files, "runtime": runtime, "runtime_sha256": runtime_hash,
               "native_policy": POLICY, "frozen_integrity_verified": True,
               "frozen_signature_sha256": before["signature_sha256"],
               "projection_receipt": {"policy": POLICY, "tied_embeddings": True, "separate_head": False,
                                      "embedding_dtype": "mlx.core.bfloat16", "embedding_raw_sha256": before["embedding_raw_sha256"]}}
        save(args.output / (role + ".json"), run)
    save(args.output / "generation-receipt.json", {"status": "generated_ungraded", "suite": suite,
         "seconds": time.monotonic() - started, "protocol_sha256": protocol_hash, "runner_sha256": sha(Path(__file__)),
         "base_sha256": sha(args.output / "base.json"), "adapter_sha256": sha(args.output / "adapter.json"),
         "runtime_sha256": runtime_hash, "scientific_gain_demonstrated": False, "independent_expert_validated": False})


def supervise(args, cfg):
    import psutil
    require(not args.output.exists(), "Use a fresh output directory")
    minimum = cfg["resources"]["minimum_system_available_bytes"]
    require(psutil.virtual_memory().available >= minimum, "System availability below native threshold")
    args.output.mkdir(parents=True)
    limits = cfg["resources"]
    deadline = cfg["training"]["deadline_seconds"] if args.command == "train" else cfg["evaluation"]["reserved_evaluation_seconds"]
    env = os.environ.copy()
    env.update({"OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "VECLIB_MAXIMUM_THREADS": "2",
                "TOKENIZERS_PARALLELISM": "false", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    started, swap_start, peak_rss, peak_cpu, stop, last = time.monotonic(), psutil.swap_memory().used, 0, 0, None, {}
    log = args.output / "worker.log"
    log_position, log_tail, gpu_error_during_run = 0, b"", False
    with log.open("w", encoding="utf-8") as stream:
        child = subprocess.Popen([str(args.mlx_python), str(Path(__file__)), *sys.argv[1:], "--worker"], env=env, stdout=stream, stderr=stream)
        proc = psutil.Process(child.pid)
        proc.cpu_percent()
        while child.poll() is None:
            time.sleep(.5)
            try:
                rss = proc.memory_info().rss
                peak_cpu = max(peak_cpu, proc.cpu_percent())
            except psutil.NoSuchProcess:
                continue
            peak_rss = max(peak_rss, rss)
            with log.open("rb") as reader:
                reader.seek(log_position)
                new_log = reader.read()
                log_position = reader.tell()
            scanned = log_tail + new_log
            gpu_error_during_run = gpu_error_during_run or gpu_error_detected(scanned.decode("utf-8", errors="replace"))
            log_tail = scanned[-1024:]
            available, swap_growth = psutil.virtual_memory().available, max(0, psutil.swap_memory().used - swap_start)
            elapsed = time.monotonic() - started
            last = {"worker_rss_bytes": rss, "system_available_bytes": available,
                    "system_swap_growth_bytes": swap_growth, "elapsed_seconds": elapsed}
            save(args.output / "resource-monitor.json", last)
            stop = ("gpu_error" if gpu_error_during_run else
                    "worker_rss" if rss > limits["worker_rss_limit_bytes"] else
                    "minimum_system_availability" if available < minimum else
                    "swap_growth" if swap_growth > limits["maximum_swap_growth_bytes"] else
                    "deadline" if elapsed > deadline else None)
            if stop:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
                break
        code = child.wait()
    gpu_error = gpu_error_during_run or gpu_error_detected(log.read_text(encoding="utf-8", errors="replace"))
    completed = code == 0 and not gpu_error and stop is None
    save(args.output / "supervisor-receipt.json", {"status": "completed" if completed else "quarantined_runtime_failure",
         "exit_code": code, "gpu_error_observed": gpu_error, "resource_stop": stop, "peak_worker_rss_bytes": peak_rss,
         "last_resource_sample": last, "peak_worker_cpu_percent": peak_cpu, "cpu_threads_target": 2,
         "cpu_threads_scope": "Environment target only; actual utilization may exceed it",
         "seconds": time.monotonic() - started, "log_sha256": sha(log), "runner_sha256": sha(Path(__file__)),
         "worker_pid": child.pid, "signal_scope": "Only the subprocess created by this supervisor",
         "termination_requested": stop is not None,
         "protocol_sha256": sha(args.protocol), "scientific_gain_demonstrated": False})
    if not completed:
        save(args.output / "status.json", {"status": "quarantined_runtime_failure", "exit_code": code,
                                            "gpu_error_observed": gpu_error, "resource_stop": stop})
    return 0 if completed else (code if code > 0 else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("train", "evaluate"))
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mlx-python", type=Path, required=True)
    parser.add_argument("--gate-receipt", type=Path)
    parser.add_argument("--gate-supervisor", type=Path)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--questions", type=Path)
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--reservation-amendment", type=Path)
    parser.add_argument("--historical-control", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.command == "train" and (args.gate_receipt is None or args.gate_supervisor is None):
        parser.error("Native training requires complete gate and supervisor receipts")
    if args.command == "evaluate" and any(value is None for value in (args.adapter, args.questions, args.registration)):
        parser.error("Native generation requires adapter, questions and original registration")
    cfg = load(args.protocol)
    protocol_hash = verify_registration(cfg, args.protocol)
    if not args.worker:
        return supervise(args, cfg)
    os.nice(10)
    try:
        if args.command == "train":
            train(args, cfg, protocol_hash)
        else:
            evaluate(args, cfg, protocol_hash)
        return 0
    except Exception as error:
        save(args.output / "failure-receipt.json", {"status": "failed_closed", "error": type(error).__name__ + ": " + str(error),
             "protocol_sha256": protocol_hash, "runner_sha256": sha(Path(__file__)), "scientific_gain_demonstrated": False})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
