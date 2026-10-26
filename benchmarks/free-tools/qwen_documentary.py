"""Opt-in MLX documentary inference. Does not call or modify the geometry planner."""

import argparse
import json
from pathlib import Path

from ft_common import sha256, write


def identities(folder):
    folder = Path(folder).resolve(strict=True)
    if not folder.is_dir():
        raise ValueError("existing local model directory required")
    files = sorted(
        p
        for p in folder.rglob("*")
        if p.is_file()
        and p.suffix in {".json", ".safetensors", ".model", ".txt", ".jinja"}
    )
    if not files:
        raise ValueError("local model files missing")
    return {str(path.relative_to(folder)): sha256(path) for path in files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("model", "adapter", "prompt", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    before = {"model": identities(args.model), "adapter": identities(args.adapter)}
    if args.output.exists():
        raise ValueError("fresh output required")
    from mlx_lm import generate, load as load_model
    from mlx_lm.sample_utils import make_sampler
    import importlib.metadata

    model, tokenizer = load_model(
        str(args.model.resolve()), adapter_path=str(args.adapter.resolve())
    )
    messages = [{"role": "user", "content": args.prompt.read_text()}]
    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    answer = generate(
        model,
        tokenizer,
        prompt=rendered,
        max_tokens=256,
        sampler=make_sampler(temp=0),
        verbose=False,
    )
    after = {"model": identities(args.model), "adapter": identities(args.adapter)}
    if before != after:
        raise ValueError("model files changed during inference")
    from knowledge import validate_answer

    brief = json.loads(args.prompt.read_text().split("\nREFERENCE_DATA\n", 1)[1])
    write(
        args.output,
        {
            "text": answer,
            "validation": validate_answer(answer, brief),
            "model_files": before,
            "mlx_lm": importlib.metadata.version("mlx-lm"),
            "prompt_sha256": sha256(args.prompt),
            "engineering_authorized": False,
            "status": "unqualified_documentary_draft_requires_review",
        },
    )


if __name__ == "__main__":
    main()
