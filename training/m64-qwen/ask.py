#!/usr/bin/env python3
"""Use the measured local candidate with fixed context; no tools or code execution."""
import argparse
import json
import os
from pathlib import Path
import sys

from dataset import CONTEXT, SYSTEM, digest
from run import HERE, WORK, comparison, configure_tokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--prompt', required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to(WORK.resolve()):
        parser.error('run must be below work/m64-qwen')
    status = json.loads((run / 'status.json').read_text())
    if status.get('status') != 'completed':
        parser.error('run is not completed')
    config = json.loads((HERE / 'model.json').read_text())
    if json.loads((run / 'configuration.json').read_text()) != config:
        parser.error('run does not match the pinned configuration')
    os.environ.update({'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                       'HF_HUB_DISABLE_IMPLICIT_TOKEN': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
                       'DO_NOT_TRACK': '1', 'TOKENIZERS_PARALLELISM': 'false'})
    from huggingface_hub import snapshot_download
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    model = Path(snapshot_download(config['repository'], revision=config['revision'], token=False,
                                  local_files_only=True, cache_dir=str(WORK / 'model-cache'),
                                  allow_patterns=['*.json', '*.safetensors', '*.txt', 'README.md']))
    if digest(model / 'model.safetensors') != config['weights_sha256']:
        parser.error('model weight hash mismatch')
    receipt = json.loads((run / 'comparison.json').read_text())
    decision = comparison(json.loads((run / 'base-evaluation.json').read_text()),
                          json.loads((run / 'adapter-evaluation.json').read_text()),
                          receipt['base_test_loss'], receipt['adapter_test_loss'])
    adapter = None
    if decision['decision'] == 'candidate_adapter':
        adapter = run / 'adapter'
        if digest(adapter / 'adapters.safetensors') != receipt['adapter_sha256']:
            parser.error('adapter hash mismatch')
    network, tokenizer = load(str(model), adapter_path=str(adapter) if adapter else None,
                              tokenizer_config={'trust_remote_code': False})
    configure_tokenizer(tokenizer)
    messages = [{'role': 'system', 'content': SYSTEM + ' ' + CONTEXT},
                {'role': 'user', 'content': args.prompt}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if len(tokenizer.encode(prompt)) > 4096:
        parser.error('prompt exceeds the 4096-token pilot limit')
    print('Using ' + ('experimental adapter' if adapter else 'base model'), file=sys.stderr)
    print(generate(network, tokenizer, prompt=prompt, max_tokens=512, sampler=make_sampler(temp=0)))


if __name__ == '__main__':
    main()
