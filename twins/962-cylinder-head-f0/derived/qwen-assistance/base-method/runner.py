"""Run a bounded, offline Qwen code proposal; do not execute its response."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(model, output):
    model, output = map(Path, (model, output))
    if output.exists():
        raise ValueError("Output must be new")
    weights = sha(model / "model.safetensors")
    if weights != "daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58":
        raise ValueError("Pinned base model changed")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                      HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    import mlx.core as mx
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    network, tokenizer = load(str(model), tokenizer_config={"trust_remote_code": False})
    tokenizer.add_eos_token("<|im_end|>")
    prompt_path = Path(__file__).with_name("qwen-prompt.txt")
    prompt = tokenizer.apply_chat_template([{"role": "user", "content": prompt_path.read_text()}],
                                           tokenize=False, add_generation_prompt=True)
    if len(tokenizer.encode(prompt)) > 2048:
        raise ValueError("Prompt exceeds the bounded context")
    mx.random.seed(962)
    started = time.monotonic()
    response, tokens = "", 0
    for item in stream_generate(network, tokenizer, prompt=prompt, max_tokens=768, sampler=make_sampler(temp=0)):
        response += item.text
        tokens += 1
    output.mkdir(parents=True)
    (output / "response.txt").write_text(response)
    report = dict(model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
                  model_revision="b3252a2f97102b1fb1571fec2c9b27219a8536be", weights_sha256=weights,
                  adapter=None,
                  model_input_hashes={p.name: sha(p) for p in model.glob("*.json")},
                  runtime={p: importlib.metadata.version(p) for p in ("mlx", "mlx-lm", "transformers")},
                  prompt_sha256=sha(prompt_path), runner_sha256=sha(Path(__file__)),
                  response_sha256=sha(output / "response.txt"), generated_tokens=tokens,
                  seconds=round(time.monotonic() - started, 3), temperature=0, seed=962,
                  generated_code_executed=False, engineering_approval=False)
    (output / "qwen-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(response)


if __name__ == "__main__":
    main(*sys.argv[1:])
