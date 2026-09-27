#!/usr/bin/env python3
"""Download public, revision-pinned assets; no account token is read."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('output', type=Path)
p.add_argument('--weights', choices=['none', 'recode', 'all'], default='none')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
lock = json.loads((Path(__file__).resolve().parents[2] / 'deploy/vast/cad-recode/models.lock.json').read_text())
base = f"https://raw.githubusercontent.com/{lock['upstream']['repository']}/{lock['upstream']['revision']}"
for name in ['demo.ipynb', 'LICENSE.md']:
    subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--output', str(a.output / name), f'{base}/{name}'], check=True)
nb = json.loads((a.output / 'demo.ipynb').read_text())
classes = []
for cell in nb['cells']:
    if cell['cell_type'] == 'code' and 'class CADRecode(' in ''.join(cell['source']):
        tree = ast.parse(''.join(cell['source']))
        classes = [ast.unparse(n) for n in tree.body if isinstance(n, ast.ClassDef)]
if len(classes) != 2:
    raise ValueError('upstream architecture changed')
# Architecture copied unmodified from pinned upstream; keep its licence alongside it.
header = '''# CAD-Recode by Rukhovich et al., ICCV 2025. CC-BY-NC-4.0; see LICENSE.md.
import torch
from torch import nn
from transformers import Qwen2ForCausalLM, Qwen2Model, PreTrainedModel
from transformers.modeling_outputs import CausalLMOutputWithPast
'''
(a.output / 'recode_model.py').write_text(header + '\n\n'.join(classes) + '\n')
if a.weights != 'none':
    from huggingface_hub import snapshot_download
    for key in (['recode', 'tokenizer'] if a.weights == 'recode' else ['recode', 'tokenizer', 'nemotron', 'vlm']):
        patterns = ['*.json', '*.txt', '*.model']
        if key != 'tokenizer': patterns += ['*.safetensors', '*.py', '*.jinja']
        snapshot_download(lock[key]['repository'], revision=lock[key]['revision'],
                          local_dir=a.output / key, allow_patterns=patterns, token=False)
manifest = {str(f.relative_to(a.output)): hashlib.file_digest(f.open('rb'), 'sha256').hexdigest()
            for f in a.output.rglob('*') if f.is_file() and '.cache' not in f.parts}
(a.output / 'assets.json').write_text(json.dumps({'pins': lock, 'sha256': manifest}, indent=2) + '\n')
