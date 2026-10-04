"""Offline, bounded Qwen3 continuation and paired generation. No downloads or installs."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'training/qwen-metal-additive-20261002'
PACK = OLD / 'runs/qwen3-fidelity-001'
sys.path.insert(0, str(OLD))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024


class ResourceGuard:
    """Monitor this worker's RSS and Metal allocation, including during a long batch."""
    def __init__(self, output):
        self.output = output
        self.stopped = threading.Event()
        self.peak = 0

    def __enter__(self):
        import psutil
        if psutil.virtual_memory().available < 16 * 1024**3:
            raise ValueError('At least 16 GiB available memory is required before loading')
        self.thread = threading.Thread(target=self.monitor, daemon=True)
        self.thread.start()
        return self

    def monitor(self):
        import psutil
        import torch
        proc = psutil.Process()
        ceiling = load(HERE / 'protocol.json')['training']['max_rss_gib'] * 1024**3
        while not self.stopped.wait(0.5):
            rss = proc.memory_info().rss
            metal = torch.mps.driver_allocated_memory() if torch.backends.mps.is_available() else 0
            # Conservative bound: unified mappings may overlap these two counts.
            total = rss + metal
            self.peak = max(self.peak, total)
            if self.output.is_dir():
                save(self.output / 'resource-monitor.json', {'rss_bytes': rss,
                     'metal_driver_allocated_bytes': metal, 'conservative_combined_peak_bytes': self.peak})
            if total > ceiling:
                save(self.output / 'resource-limit-receipt.json', {'status': 'resource_limit_exceeded',
                     'conservative_combined_bytes': total, 'ceiling_bytes': ceiling})
                os._exit(137)

    def __exit__(self, *args):
        self.stopped.set()
        self.thread.join(timeout=2)


def verify_snapshot(snapshot):
    protocol = load(HERE / 'protocol.json')
    if sha(PACK / 'adapter/adapter_model.safetensors') != protocol['initial_adapter_sha256']:
        raise ValueError('Historical adapter changed')
    profile = load(OLD / 'compact-qwen3-v5/model-profile.json')
    expected = {**profile['tokenizer_files_sha256'],
                **load(PACK / 'development-receipt.json')['base_weights_sha256']}
    for name, digest in expected.items():
        if not (snapshot / name).is_file() or sha(snapshot / name) != digest:
            raise ValueError('Missing or changed pinned model file: ' + name)
    return expected


def inventory():
    names = ('torch', 'transformers', 'tokenizers', 'peft', 'accelerate',
             'datasets', 'huggingface-hub')
    result = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return {'python': sys.version, 'platform': sys.platform,
            'libraries': result, 'logical_cpus': os.cpu_count(),
            'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else None}


def runtime(snapshot):
    expected = verify_snapshot(snapshot)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    cfg = load(HERE / 'protocol.json')
    torch.set_num_threads(cfg['training']['threads'])
    torch.set_num_interop_threads(1)
    set_seed(cfg['training']['seed'])
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True)
    tokenizer.padding_side = 'right'
    template = hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()
    if template != load(OLD / 'compact-qwen3-v5/model-profile.json')['chat_template_sha256']:
        raise ValueError('Chat template changed')
    model = AutoModelForCausalLM.from_pretrained(
        str(snapshot), local_files_only=True, torch_dtype=torch.bfloat16,
        attn_implementation='sdpa')
    device = cfg['training']['device']
    if device not in ('cpu', 'mps'):
        raise ValueError('Unregistered execution device')
    if device == 'mps' and not torch.backends.mps.is_available():
        raise ValueError('Registered MPS backend unavailable; no silent CPU fallback')
    model.to(device)
    return model, tokenizer, expected


def supervised_tokens(record, tokenizer):
    options = dict(tokenize=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(record['messages'], **options)
    prefix = tokenizer.apply_chat_template(record['messages'][:-1],
                                          add_generation_prompt=True, **options)
    if full[:len(prefix)] != prefix or len(full) <= len(prefix):
        raise ValueError('Assistant mask boundary mismatch')
    end = full.index(tokenizer.eos_token_id, len(prefix))
    labels = [-100] * len(full)
    labels[len(prefix):end + 1] = full[len(prefix):end + 1]
    return {'input_ids': full, 'attention_mask': [1] * len(full), 'labels': labels}


def train(snapshot, output):
    # Refuse authoring/manifest changes before loading a multi-GiB model.
    import audit
    audited = audit.audit_data(HERE)
    cfg = load(HERE / 'protocol.json')
    if output.exists():
        raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    save(output / 'status.json', {'status': 'loading', 'protocol_sha256': sha(HERE / 'protocol.json')})
    started = time.monotonic()
    model, tokenizer, model_files = runtime(snapshot)
    from datasets import Dataset
    from peft import PeftModel
    from transformers import Trainer, TrainingArguments, TrainerCallback, DataCollatorForSeq2Seq
    records = rows(HERE / 'data/train-records.jsonl')
    tokens = [supervised_tokens(record, tokenizer) for record in records]
    steps = math.ceil(len(records) / cfg['training']['gradient_accumulation_steps'])
    if steps > cfg['training']['max_optimizer_steps']:
        raise ValueError('Training exceeds registered optimizer-step ceiling')
    model = PeftModel.from_pretrained(model, str(PACK / 'adapter'), is_trainable=True)
    model.config.use_cache = False
    model.enable_input_require_grads()

    class Bounds(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if any(isinstance(v, (float, int)) and not math.isfinite(v)
                   for v in (logs or {}).values()):
                raise ValueError('Non-finite training metric')
            self.check(state)

        def on_step_end(self, args, state, control, **kwargs):
            self.check(state)

        def check(self, state):
            if rss_bytes() > cfg['training']['max_rss_gib'] * 1024**3:
                raise ValueError('Registered process memory ceiling exceeded')
            if time.monotonic() - started > cfg['training']['deadline_seconds']:
                raise ValueError('Registered training deadline exceeded')
            save(output / 'status.json', {'status': 'training', 'step': state.global_step,
                                         'elapsed_seconds': time.monotonic() - started})

    arguments = TrainingArguments(
        output_dir=str(output / 'checkpoints'), num_train_epochs=1,
        learning_rate=cfg['training']['learning_rate'], lr_scheduler_type='linear',
        warmup_ratio=0.1, per_device_train_batch_size=1,
        gradient_accumulation_steps=cfg['training']['gradient_accumulation_steps'],
        gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        bf16=True, use_cpu=cfg['training']['device'] == 'cpu', dataloader_pin_memory=False, logging_steps=1,
        save_strategy='steps', save_steps=cfg['training']['save_steps'],
        save_total_limit=3, eval_strategy='no', seed=cfg['training']['seed'],
        report_to=[], disable_tqdm=True)
    trainer = Trainer(model=model, args=arguments, train_dataset=Dataset.from_list(tokens),
                      data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True,
                                                          label_pad_token_id=-100),
                      callbacks=[Bounds()])
    result = trainer.train()
    trainer.save_model(str(output / 'adapter'))
    receipt = {'status': 'trained_not_selected_or_evaluated', 'model_id': cfg['model_id'],
               'revision': cfg['revision'], 'protocol_sha256': sha(HERE / 'protocol.json'),
               'data_manifest_sha256': sha(HERE / 'data/manifest.json'),
               'runner_sha256': sha(Path(__file__)), 'initial_adapter_sha256': cfg['initial_adapter_sha256'],
               'adapter_sha256': sha(output / 'adapter/adapter_model.safetensors'),
               'model_files_sha256': model_files, 'rows': len(records),
               'supervised_tokens': sum(sum(v != -100 for v in t['labels']) for t in tokens),
               'optimizer_steps': trainer.state.global_step, 'seconds': time.monotonic() - started,
               'peak_rss_bytes': rss_bytes(), 'runtime': inventory(),
               'scientific_gain_demonstrated': False, 'reserved_test_opened': False,
               'audit': audited, 'training_metrics': result.metrics}
    save(output / 'training-receipt.json', receipt)
    save(output / 'trainer-history.json', trainer.state.log_history)
    save(output / 'status.json', {'status': receipt['status']})


def evaluate(snapshot, adapter, questions_path, registration, output, selection, historical_control=False):
    cfg = load(HERE / 'protocol.json')
    reserve = load(registration)
    if sha(questions_path) != reserve['questions_sha256']:
        raise ValueError('Questions differ from pre-output registration')
    questions = rows(questions_path)
    roster = [{key: q[key] for key in ('id', 'suite', 'source_family', 'critical', 'input_sha256')}
              for q in questions]
    if roster != reserve['roster']:
        raise ValueError('Evaluation roster changed')
    suite = reserve['suite']
    if suite not in ('development', 'reserved'):
        raise ValueError('Unknown evaluation suite')
    if suite == 'reserved':
        frozen = load(selection) if selection else {}
        if (frozen.get('protocol_sha256') != sha(HERE / 'protocol.json') or
                frozen.get('adapter_sha256') != sha(adapter / 'adapter_model.safetensors') or
                frozen.get('reservation_sha256') != sha(registration) or
                frozen.get('decision') != 'selected_for_reserved_evaluation'):
            raise ValueError('Reserved run requires frozen selection tied to reservation and weights')
    for q in questions:
        if object_sha(q['messages']) != q['input_sha256']:
            raise ValueError('Expanded input hash mismatch')
        import task_routed_profile
        raw = {**q, 'messages': q['raw_messages']}
        if task_routed_profile.questions_with_profile([raw])[0]['messages'] != q['messages']:
            raise ValueError('Evaluation messages differ from frozen profile expansion')
    if output.exists():
        raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    model, tokenizer, files = runtime(snapshot)
    from peft import PeftModel
    import torch
    model = PeftModel.from_pretrained(model, str(adapter)).eval()
    if historical_control:
        if suite != 'development':
            raise ValueError('Historical three-arm control is development only')
        model.load_adapter(str(PACK / 'adapter'), adapter_name='historical', is_trainable=False)
        model.eval()
    runtime_identity = inventory()
    runtime_identity['device'] = cfg['training']['device']
    started = time.monotonic()
    roles = ('base', 'historical_adapter', 'adapter') if historical_control else ('base', 'adapter')
    for role in roles:
        results = []
        model.set_adapter('historical' if role == 'historical_adapter' else 'default')
        context = model.disable_adapter() if role == 'base' else contextlib.nullcontext()
        with context, torch.inference_mode():
            for q in questions:
                tick = time.monotonic()
                encoded = tokenizer.apply_chat_template(q['messages'], tokenize=True,
                    return_tensors='pt', return_dict=True, add_generation_prompt=True,
                    enable_thinking=False)
                encoded = encoded.to(cfg['training']['device'])
                generated = model.generate(**encoded, **cfg['decoding'],
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
                new = generated[0, encoded['input_ids'].shape[-1]:]
                response = tokenizer.decode(new, skip_special_tokens=True).strip()
                results.append({**{key: q[key] for key in ('id', 'suite', 'source_id', 'source_family', 'critical', 'input_sha256', 'messages')},
                    'response': response, 'response_sha256': hashlib.sha256(response.encode()).hexdigest(),
                    'generated_tokens': len(new), 'budget_hit': len(new) >= cfg['decoding']['max_new_tokens'],
                    'seconds': time.monotonic() - tick})
                save(output / (role + '.partial.json'), {'model_role': role, 'rows': results})
                print(json.dumps({'stage': 'generation', 'arm': role, 'id': q['id'],
                                  'tokens': len(new), 'seconds': time.monotonic() - tick}), flush=True)
                if rss_bytes() > cfg['training']['max_rss_gib'] * 1024**3:
                    raise ValueError('Evaluation memory ceiling exceeded')
        run = {'schema_version': 1, 'status': 'completed', 'model_role': role, 'suite': suite,
               'model_id': cfg['model_id'], 'revision': cfg['revision'],
               'profile_name': cfg['inference_profile'], 'decoding': cfg['decoding'], 'rows': results,
               'reservation_sha256': sha(registration), 'roster_sha256': object_sha(roster),
               'protocol_sha256': sha(HERE / 'protocol.json'), 'model_files_sha256': files,
               'adapter_sha256': (cfg['initial_adapter_sha256'] if role == 'historical_adapter'
                                   else sha(adapter / 'adapter_model.safetensors')),
               'selection_receipt_sha256': sha(selection) if selection else None,
               'runtime': runtime_identity, 'runtime_sha256': object_sha(runtime_identity)}
        save(output / (role + '.json'), run)
    save(output / 'generation-receipt.json', {'status': 'generated_ungraded', 'suite': suite,
         'seconds': time.monotonic() - started, 'peak_rss_bytes': rss_bytes(),
         'runner_sha256': sha(Path(__file__)), 'base_sha256': sha(output / 'base.json'),
         'adapter_sha256': sha(output / 'adapter.json'), 'scientific_gain_demonstrated': False})


def supervised_child(args, deadline):
    # Timeout only this newly created subprocess; never signal another job.
    child_args = [sys.executable, str(Path(__file__)), *args, '--worker']
    child = subprocess.Popen(child_args)
    try:
        return child.wait(timeout=deadline)
    except subprocess.TimeoutExpired:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        return 124


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'train', 'evaluate'))
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--questions', type=Path)
    parser.add_argument('--registration', type=Path)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--historical-control', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.command == 'preflight':
        report = inventory()
        if args.snapshot:
            report['model_files_sha256'] = verify_snapshot(args.snapshot.resolve())
        report['status'] = 'preflight_only_not_trained'
        print(json.dumps(report, indent=2))
        return 0
    if args.snapshot is None or args.output is None:
        parser.error('Training/generation requires --snapshot and fresh --output')
    if args.command == 'evaluate' and any(x is None for x in (args.adapter, args.questions, args.registration)):
        parser.error('Evaluation requires --adapter, --questions and --registration')
    cfg = load(HERE / 'protocol.json')
    if not args.worker:
        seconds = (cfg['training']['deadline_seconds'] if args.command == 'train'
                   else cfg['evaluation']['reserved_evaluation_seconds'])
        code = supervised_child(sys.argv[1:], seconds)
        if code:
            save(args.output / 'interruption-receipt.json', {'status': 'failed_or_interrupted',
                 'exit_code': code, 'scientific_gain_demonstrated': False})
        return code
    if args.command == 'train':
        with ResourceGuard(args.output):
            train(args.snapshot.resolve(), args.output.resolve())
    else:
        with ResourceGuard(args.output):
            evaluate(args.snapshot.resolve(), args.adapter.resolve(), args.questions.resolve(),
                     args.registration.resolve(), args.output.resolve(), args.selection,
                     args.historical_control)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
