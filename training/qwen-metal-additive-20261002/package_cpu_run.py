"""Package completed CPU results and a portable adapter without copying base weights."""
import argparse
import json
from pathlib import Path
import shutil
import verify_grounded

HERE=Path(__file__).resolve().parent

def package(source,output):
    if output.exists():
        raise ValueError('Use a fresh package directory')
    receipt=verify_grounded.load(source/'run-receipt.json')
    if receipt['status']!='completed' or receipt['test_used_in_training']:
        raise ValueError('Run incomplete or test data used for training')
    if receipt['runner_sha256']!=verify_grounded.sha(HERE/'run_cpu_pilot.py'):
        raise ValueError('Executed runner bytes do not match')
    if receipt['dataset_manifest_sha256']!=verify_grounded.sha(HERE/'grounded-v3/manifest.json'):
        raise ValueError('Run belongs to a different dataset')
    verify_grounded.verify(HERE,HERE/'grounded-v3')
    for name,expected in receipt['adapter_files_sha256'].items():
        if verify_grounded.sha(source/'adapter'/name)!=expected:
            raise ValueError('Adapter file changed: '+name)
    files=['run-receipt.json','training-metrics.json','trainer-history.json','adapter-audit.json','base-validation.json',
           'adapter-validation.json','base-predictions.jsonl','adapter-predictions.jsonl',
           'base-timings.json','adapter-timings.json','base-evaluation.json','adapter-evaluation.json',
           'base-review.jsonl','adapter-review.jsonl']
    for name in files:
        if not (source/name).is_file():
            raise ValueError('Missing result: '+name)
    output.mkdir(parents=True)
    for name in files:
        shutil.copyfile(source/name,output/name)
    shutil.copyfile(HERE/'MODEL-LICENSE.txt',output/'MODEL-LICENSE.txt')
    (output/'adapter').mkdir()
    shutil.copyfile(source/'adapter/adapter_model.safetensors',output/'adapter/adapter_model.safetensors')
    shutil.copyfile(source/'adapter/adapter_config.json',output/'source-adapter-config.json')
    config=verify_grounded.load(source/'adapter/adapter_config.json')
    config['base_model_name_or_path']=receipt['model_id']
    config['revision']=receipt['revision']
    (output/'adapter/adapter_config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    metadata={'status':'completed_cpu_lora_pilot','source_receipt_sha256':verify_grounded.sha(source/'run-receipt.json'),
              'packager_sha256':verify_grounded.sha(HERE/'package_cpu_run.py'),
              'base_weights_included':False,'expert_review':'pending',
              'model_license_source':'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/raw/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/LICENSE',
              'config_transformation':'Only base_model_name_or_path and revision set to the pinned public model for portable loading; original config retained separately. Adapter tensors unchanged.',
              'files_sha256':{str(p.relative_to(output)):verify_grounded.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output/'package-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return metadata

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=package(args.source.resolve(),args.output.resolve())
    print(json.dumps({'status':result['status'],'files':len(result['files_sha256']),'base_weights_included':False}))
