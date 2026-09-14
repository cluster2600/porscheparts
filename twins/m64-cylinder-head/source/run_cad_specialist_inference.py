#!/usr/bin/env python3
"""Bounded non-commercial CAD reconstruction experiment; generated code is DATA.

Official architecture sources are hash-pinned and imported, not model-generated
code. No geometry execution, master replacement or manufacturing authorization.
Input: the SAME 256x3 float32 NPY, bbox-centered in [-1, 1], for both models.
Generated CadQuery coordinates conventionally need /100 before denormalization.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


MODELS = {
    "cadrille": {
        "repo": "maksimko123/cadrille",
        "revision": "2f422d1169e4362e2288b0e0f54bb3a2b504e0f9",
        "source_repo": "col14m/cadrille",
        "source_revision": "d72acc687273d31d62afe62eb9ded8b66b835321",
        "source_file": "cadrille.py",
        "source_sha256": "0338162cfb9f78981e63b48638935419e3d92c639bf2f97a9a191de96fca50b8",
        "processor": "Qwen/Qwen2-VL-2B-Instruct",
        "processor_revision": "895c3a49bc3fa70a340399125c650a463535e71c",
    },
    "cad-recode": {
        "repo": "filapro/cad-recode-v1.5",
        "revision": "765e8cc315a1a77bd8c69ccd0b403bad20ce35e8",
        "source_repo": "filaPro/cad-recode",
        "source_revision": "03e3262119b38939feaa44b8368ad8db99243d47",
        "source_file": "demo.ipynb",
        "source_sha256": "0e7f29d23885aca46d6aa73fa0bee98b9bbb37745a01a8cfed706e83acd27e8f",
        "processor": "Qwen/Qwen2-1.5B",
        "processor_revision": "8a16abf2848eda07cc5253dec660bf1ce007ad7a",
    },
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_recode_architecture(raw):
    """Keep only official model classes and their dependency imports, never demo exec."""
    notebook = json.loads(raw)
    source = next("".join(cell["source"]) for cell in notebook["cells"]
                  if cell["cell_type"] == "code")
    tree = ast.parse(source)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    require([node.name for node in classes] == ["FourierPointEncoder", "CADRecode"],
            "official_class_set_changed")
    imports = ast.parse("import torch\nfrom torch import nn\n"
                        "from transformers import Qwen2ForCausalLM, Qwen2Model, PreTrainedModel\n"
                        "from transformers.modeling_outputs import CausalLMOutputWithPast\n").body
    return (ast.unparse(ast.Module(body=imports + classes, type_ignores=[])) + "\n").encode()


def adapt_point_cast(raw, device):
    if device == "cuda":
        return raw
    require(raw.count(b".bfloat16()") == 1, "official_point_cast_changed")
    return raw.replace(b".bfloat16()", b".to(dtype=self.model.embed_tokens.weight.dtype)")


def prepare_architecture(name, directory, device="cuda"):
    spec = MODELS[name]
    url = ("https://raw.githubusercontent.com/" + spec["source_repo"] + "/"
           + spec["source_revision"] + "/" + spec["source_file"])
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(2_000_001)
    require(len(raw) <= 2_000_000 and sha(raw) == spec["source_sha256"], "source_digest_mismatch")
    module_raw = extract_recode_architecture(raw) if name == "cad-recode" else raw
    module_raw = adapt_point_cast(module_raw, device)
    path = directory / "official_architecture.py"
    path.write_bytes(module_raw)
    return path, sha(module_raw)


def load_points(path):
    import numpy as np
    require(path.stat().st_size <= 16384, "point_file_size")
    points = np.load(path, allow_pickle=False)
    require(points.shape == (256, 3) and points.dtype == np.float32, "points_shape_dtype")
    require(np.isfinite(points).all() and float(np.abs(points).max()) <= 1.00001,
            "points_nonfinite_or_not_normalized")
    require(float(np.ptp(points, axis=0).max()) > 0.1, "degenerate_points")
    return points


def infer(args):
    import numpy as np
    import torch
    import transformers
    from transformers import AutoProcessor, AutoTokenizer, set_seed
    require(transformers.__version__ == "4.50.3", "transformers_version_required_4_50_3")
    require(args.device != "cuda" or torch.cuda.is_available(), "cuda_required")
    require(args.device != "mps" or (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()),
            "mps_required_no_silent_cpu_fallback")
    if args.device != "cuda":
        torch.set_num_threads(args.cpu_threads)
    points = load_points(args.points)
    spec = MODELS[args.model]
    source_path, module_sha = prepare_architecture(args.model, args.output, args.device)
    module_spec = importlib.util.spec_from_file_location("official_cad_architecture", source_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    set_seed(args.seed)
    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    start = time.monotonic()
    common = {"revision": spec["revision"], "token": False, "use_safetensors": True,
              "torch_dtype": torch.bfloat16 if args.device == "cuda" else torch.float32,
              "attn_implementation": "sdpa",
              "trust_remote_code": False, "output_loading_info": True}
    klass = module.Cadrille if args.model == "cadrille" else module.CADRecode
    model, loading = klass.from_pretrained(spec["repo"], **common)
    require(not any(loading.get(k) for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")),
            "model_weights_loading_mismatch")
    # Official CUDA architecture deliberately keeps its point encoder float32.
    model = model.eval().to(args.device)
    if args.device != "cuda":
        model = model.to(dtype=torch.float32)
    processor_kwargs = {"revision": spec["processor_revision"], "token": False,
                        "trust_remote_code": False, "padding_side": "left"}
    if args.model == "cadrille":
        processor = AutoProcessor.from_pretrained(spec["processor"], **processor_kwargs,
                                                  min_pixels=256*28*28, max_pixels=1280*28*28)
        batch = module.collate([{"point_cloud": points, "description": "Generate cadquery code",
                                "file_name": "common-input"}], processor=processor, n_points=256, eval=True)
        batch = {key: value.to(args.device) for key, value in batch.items() if hasattr(value, "to")}
        tokenizer = processor.tokenizer
    else:
        tokenizer = AutoTokenizer.from_pretrained(spec["processor"], **processor_kwargs,
                                                 pad_token="<|im_end|>")
        ids = [tokenizer.pad_token_id] * 256 + [tokenizer("<|im_start|>")["input_ids"][0]]
        batch = {"input_ids": torch.tensor([ids], device=args.device),
                 "attention_mask": torch.tensor([[-1]*256+[1]], device=args.device),
                 "point_cloud": torch.tensor(points.astype(np.float32), device=args.device).unsqueeze(0)}
    if args.device == "cuda":
        torch.cuda.synchronize()
    elif args.device == "mps":
        torch.mps.synchronize()
    load_seconds = time.monotonic() - start
    input_count = batch["input_ids"].shape[1]
    generation_start = time.monotonic()
    with torch.inference_mode():
        generated = model.generate(**batch, max_new_tokens=args.max_tokens, do_sample=False,
                                   max_time=args.generation_seconds, pad_token_id=tokenizer.pad_token_id,
                                   return_dict_in_generate=True)
    if args.device == "cuda":
        torch.cuda.synchronize()
    elif args.device == "mps":
        torch.mps.synchronize()
    generation_seconds = time.monotonic() - generation_start
    ids = generated.sequences[0, input_count:].tolist()
    code = tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    require(len(code.encode()) <= 131072, "generated_code_byte_limit")
    code_path = args.output / "generated.py.txt"
    code_path.write_text(code, encoding="utf-8")
    eos = model.generation_config.eos_token_id
    eos = eos if isinstance(eos, list) else [eos]
    ended = bool(ids and ids[-1] in eos)
    return {"status": "unreviewed" if ended else "incomplete", "model": spec,
            "license": "cc-by-nc-4.0", "noncommercial_research_only": True,
            "geometry_executed": False, "physical_validation": False, "master_modified": False,
            "input_sha256": sha(args.points.read_bytes()), "point_count": 256,
            "normalization": "provided_bbox_centered_minus1_plus1",
            "output_coordinate_scale_to_input": 0.01,
            "official_module_sha256": module_sha, "generated_code_sha256": sha(code.encode()),
            "architecture_adaptation": ("none" if args.device == "cuda" else
                                        "point_embedding_cast_uses_model_weight_dtype_instead_of_bfloat16"),
            "seed": args.seed, "do_sample": False, "attention": "sdpa",
            "input_tokens": input_count, "output_tokens": len(ids), "max_new_tokens": args.max_tokens,
            "ended_with_eos": ended, "load_seconds": load_seconds,
            "generation_seconds": generation_seconds, "generation_time_budget": args.generation_seconds,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "device": args.device, "model_parameter_dtype": str(next(model.parameters()).dtype),
            "cpu_threads": torch.get_num_threads(), "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if args.device == "cuda" else ("Apple MPS" if args.device == "mps" else None),
            "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated() if args.device == "cuda" else None,
            "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved() if args.device == "cuda" else None,
            "mps_current_allocated_bytes": (torch.mps.current_allocated_memory() if args.device == "mps"
                                            and hasattr(torch.mps, "current_allocated_memory") else None),
            "mps_driver_allocated_bytes": (torch.mps.driver_allocated_memory() if args.device == "mps"
                                           and hasattr(torch.mps, "driver_allocated_memory") else None)}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--device", choices=("cuda", "cpu", "mps"), default="cuda")
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--generation-seconds", type=int, default=120)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--noncommercial-research", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    require(args.noncommercial_research, "noncommercial_research_acknowledgment_required")
    require(0 <= args.seed < 2**31 and 1 <= args.max_tokens <= 1536, "seed_or_token_budget")
    require(1 <= args.cpu_threads <= 8, "cpu_thread_budget")
    require(1 <= args.generation_seconds <= 300 and 1 <= args.timeout_seconds <= 1200,
            "time_budget")
    args.points = args.points.resolve(strict=True)
    args.output = args.output.resolve()
    return args


def configure_mps_environment(env):
    """Validate both watermarks before Torch imports or any weight download."""
    env.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.5")
    env.setdefault("PYTORCH_MPS_LOW_WATERMARK_RATIO", "0.4")
    high = float(env["PYTORCH_MPS_HIGH_WATERMARK_RATIO"])
    low = float(env["PYTORCH_MPS_LOW_WATERMARK_RATIO"])
    require(math.isfinite(low) and math.isfinite(high) and 0 < low < high <= 1,
            "mps_watermarks_require_0_less_low_less_high_at_most_1")
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"


def snapshot_driver(source, output):
    raw = source.read_bytes()
    destination = output / "inference_driver.py"
    destination.write_bytes(raw)
    return destination, sha(raw)


def main(argv=None):
    args = parse_args(argv)
    if args.device == "mps":
        configure_mps_environment(os.environ)
    if args.worker:
        driver_sha = sha(Path(__file__).read_bytes())
        try:
            result = infer(args)
        except Exception as error:
            # Do not serialize exception messages that could contain third-party sensitive data.
            result = {"status": "failed", "error_type": type(error).__name__,
                      "geometry_executed": False, "physical_validation": False,
                      "model": MODELS[args.model], "driver_sha256": driver_sha}
            dump(args.output / "generation.json", result)
            raise
        result["driver_sha256"] = driver_sha
        dump(args.output / "generation.json", result)
        return 0
    args.output.mkdir(mode=0o700)
    driver_path, driver_sha = snapshot_driver(Path(__file__).resolve(), args.output)
    command = [sys.executable, str(driver_path), "--worker", "--noncommercial-research",
               "--model", args.model, "--device", args.device, "--cpu-threads", str(args.cpu_threads),
               "--points", str(args.points), "--output", str(args.output),
               "--seed", str(args.seed), "--max-tokens", str(args.max_tokens),
               "--generation-seconds", str(args.generation_seconds),
               "--timeout-seconds", str(args.timeout_seconds)]
    start = time.monotonic()
    env = os.environ.copy()
    env.update(HF_HUB_DISABLE_IMPLICIT_TOKEN="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    if args.device == "mps":
        configure_mps_environment(env)
    # This process must itself be launched without any workload credentials.
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "VAST_API_KEY", "OPENAI_API_KEY", "BAO_TOKEN", "VAULT_TOKEN"):
        env.pop(key, None)
    timed_out = False
    with (args.output / "inference.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            process.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
    receipt = {"model": args.model, "device": args.device, "returncode": process.returncode, "timed_out": timed_out,
               "elapsed_seconds": time.monotonic()-start, "timeout_seconds": args.timeout_seconds,
               "geometry_executed": False, "input_sha256": sha(args.points.read_bytes()),
               "driver_sha256": driver_sha}
    dump(args.output / "supervision.json", receipt)
    print(json.dumps(receipt))
    return 1 if timed_out or process.returncode else 0


if __name__ == "__main__":
    raise SystemExit(main())
