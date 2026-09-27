#!/usr/bin/env python3
"""Generate candidates only. Do not execute generated Python."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
import torch
from transformers import AutoTokenizer
from pipeline import digest, new_output, verify_intake, write_json

p = argparse.ArgumentParser()
p.add_argument('intake', type=Path)
p.add_argument('models', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
p.add_argument('--attempts', type=int, choices=[1, 2, 3], default=1)
a = p.parse_args()
verify_intake(a.intake)
manifest = json.loads((a.models / 'assets.json').read_text())
for name, expected in manifest['sha256'].items():
    path = (a.models / name).resolve()
    if not path.is_relative_to(a.models.resolve()) or digest(path) != expected:
        raise ValueError('model asset hash mismatch')
if a.device == 'cuda' and not torch.cuda.is_available():
    raise RuntimeError('CUDA unavailable; no silent CPU fallback')
points = np.load(a.intake / 'points.npy', allow_pickle=False)
if points.shape != (256, 3) or not np.isfinite(points).all() or np.abs(points).max() > 1.00001:
    raise ValueError('invalid normalized point cloud')
spec = importlib.util.spec_from_file_location('recode_model', a.models / 'recode_model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tokenizer = AutoTokenizer.from_pretrained(a.models / 'tokenizer', local_files_only=True,
                                         pad_token='<|im_end|>', padding_side='left')
# Eager attention avoids the old upstream FlashAttention build on Blackwell.
model = module.CADRecode.from_pretrained(a.models / 'recode', local_files_only=True,
                                        torch_dtype=torch.bfloat16, attn_implementation='eager').eval().to(a.device)
output = new_output(a.output)
ids = [tokenizer.pad_token_id] * 256 + [tokenizer('<|im_start|>')['input_ids'][0]]
mask = [-1] * 256 + [1]
for attempt in range(1, a.attempts + 1):
    torch.manual_seed(935 + attempt)
    start = time.monotonic()
    if a.device == 'cuda': torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        tokens = model.generate(input_ids=torch.tensor([ids], device=a.device),
            attention_mask=torch.tensor([mask], device=a.device),
            point_cloud=torch.tensor(points, dtype=torch.float32, device=a.device).unsqueeze(0),
            max_new_tokens=768, pad_token_id=tokenizer.pad_token_id,
            do_sample=attempt > 1, **({'temperature': 0.7} if attempt > 1 else {}))
    raw = tokenizer.decode(tokens[0, len(ids):], skip_special_tokens=True)
    (output / f'candidate-{attempt}.py').write_text(raw)
    try:
        ast.parse(raw); syntax = True
    except SyntaxError:
        syntax = False
    write_json(output / f'candidate-{attempt}.json', {
        'status': 'generated_unverified' if syntax else 'invalid_syntax',
        'elapsed_seconds': time.monotonic() - start, 'device': a.device,
        'peak_vram_bytes': torch.cuda.max_memory_allocated() if a.device == 'cuda' else None,
        'truncated': int(tokens.shape[1]) - len(ids) >= 768,
        'source_sha256': digest(a.intake / 'intake.json'),
        'code_sha256': digest(output / f'candidate-{attempt}.py'),
        'model_revision': manifest['pins']['recode']['revision'],
        'geometry_accepted': False})
