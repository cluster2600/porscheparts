# Executed CPU LoRA pilot

This is a separate unquantized BF16 CPU experiment using the frozen v3 model,
tokenizer and data. The prepared GPU NF4 QLoRA experiment has not been run.
The runtime available for this session has no GPU, 16 GiB memory, four CPU
quota cores, and AVX512 BF16 instructions. The runner uses four threads.

The experiment fixes one epoch, seed 42, rank 8 on `q_proj`/`v_proj`, alpha 16,
dropout 0.05, learning rate 5e-5, batch 1 and accumulation 8. It uses the 53 SFT
training examples and 16 validation examples; test examples never enter training.
Eight held-out prompts are generated before and after training, with the same
BF16 CPU execution and deterministic 256-token output budget. No parameters are
adjusted in response to test predictions.

Results and the portable adapter are in [cpu-lora-001](runs/cpu-lora-001/RESULTS.md).
The exact installed dependency inventory is included as `runtime-freeze.txt`.

## Reproduce

Use a fresh output directory on a Linux BF16-capable CPU with sufficient memory:

```sh
python3 -m venv work/metal-cpu-env
work/metal-cpu-env/bin/python -m pip install \
  -r training/qwen-metal-additive-20261002/cpu-pilot-requirements.txt
PYTHONUNBUFFERED=1 HF_HUB_DISABLE_XET=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false \
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
work/metal-cpu-env/bin/python \
  training/qwen-metal-additive-20261002/run_cpu_pilot.py \
  --run --output work/metal-cpu-new-run --cache work/metal-model-cache
```

Without `--run`, the command only verifies the frozen export and model profile.
The runtime downloads the exact upstream revision, checks tokenizer hashes,
measures baseline validation loss, generates baseline predictions, trains the
adapter, then measures adapter loss and predictions. It writes stage status,
timing, dependency versions, weight hashes and a complete run receipt.

The output includes an adapter, not a replacement of the base checkpoint.
Packaging retains the trained tensors unchanged and normalizes only the saved
adapter's base-model identifier/revision for portable loading. The original
adapter configuration is retained as provenance. Base weights and redundant
tokenizer assets are not copied into the result package; fetch them from the
pinned upstream model. Model license: `MODEL-LICENSE.txt`; data attribution and
CC BY 4.0 notices: `grounded-v3/sources.json` and its linked license evidence.

```sh
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/audit_cpu_adapter.py \
  --adapter work/metal-cpu-new-run/adapter/adapter_model.safetensors \
  --output work/metal-cpu-new-run/adapter-audit.json
python3 training/qwen-metal-additive-20261002/package_cpu_run.py \
  --source work/metal-cpu-new-run --output work/metal-cpu-new-package
```

## Interpretation and review

Validation loss is mean per-example cross-entropy on assistant targets. Citation
presence is a syntactic measurement on eight generated answers. Neither metric
establishes scientific correctness or statistically significant improvement.
Token-budget hits are recorded and should be considered when reviewing truncated
responses. Validation/test coverage remains small and uneven across alloys.

The base and adapter review worksheets include prompts, reference answers,
criteria, generated answers and prediction hashes. Their expert score fields
remain blank pending independent review. An assistant's qualitative observations
are separate from that review; they do not constitute engineering approval.
Do not infer part qualification or safe manufacturing parameters from this pilot.

For portable inference, load the pinned base and its tokenizer, then attach the
packaged adapter using PEFT; CPU prediction conditions match this experiment:

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
model_id = "Qwen/Qwen2.5-1.5B-Instruct"
revision = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
base = AutoModelForCausalLM.from_pretrained(
    model_id, revision=revision, torch_dtype=torch.bfloat16,
    attn_implementation="sdpa")
model = PeftModel.from_pretrained(base, "/path/to/packaged/adapter").eval()
```
