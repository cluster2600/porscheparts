"""Check completed CPU result hashes and measurement consistency without ML imports."""
import argparse
import json
from pathlib import Path
import evaluate_grounded
import verify_grounded

HERE=Path(__file__).resolve().parent

def verify(output):
    manifest=verify_grounded.load(output/'package-manifest.json')
    for name,expected in manifest['files_sha256'].items():
        if verify_grounded.sha(output/name)!=expected:
            raise ValueError('Changed packaged file: '+name)
    receipt=verify_grounded.load(output/'run-receipt.json')
    if receipt['status']!='completed' or receipt['test_used_in_training'] or receipt['expert_validated']:
        raise ValueError('Run status or qualification claim invalid')
    if receipt['dataset_manifest_sha256']!=verify_grounded.sha(HERE/'grounded-v3/manifest.json'):
        raise ValueError('Dataset release mismatch')
    verify_grounded.verify(HERE,HERE/'grounded-v3')
    config=verify_grounded.load(output/'adapter/adapter_config.json')
    if (config['base_model_name_or_path'],config['revision'])!=(receipt['model_id'],receipt['revision']):
        raise ValueError('Portable adapter points to a different model')
    if verify_grounded.sha(output/'adapter/adapter_model.safetensors')!=receipt['adapter_files_sha256']['adapter_model.safetensors']:
        raise ValueError('Adapter tensors changed during packaging')
    if verify_grounded.sha(output/'source-adapter-config.json')!=receipt['adapter_files_sha256']['adapter_config.json']:
        raise ValueError('Original adapter config changed')
    audit=verify_grounded.load(output/'adapter-audit.json')
    if not audit['all_finite'] or not 0<audit['nonzero_lora_b_tensors']==audit['lora_b_tensors']:
        raise ValueError('Adapter failed finite/nonzero tensor audit')
    if audit['sha256']!=receipt['adapter_files_sha256']['adapter_model.safetensors']:
        raise ValueError('Tensor audit belongs to a different adapter')
    for kind in ('base','adapter'):
        predictions=verify_grounded.rows(output/(kind+'-predictions.jsonl'))
        report,_=evaluate_grounded.evaluate(HERE/'grounded-v3',predictions)
        if report!=verify_grounded.load(output/(kind+'-evaluation.json')) or report!=receipt[kind+'_evaluation']:
            raise ValueError('Prediction metrics mismatch')
        losses=verify_grounded.load(output/(kind+'-validation.json'))
        if losses!=receipt[kind+'_validation'] or len(losses['example_losses'])!=16:
            raise ValueError('Validation measurements mismatch')
        if abs(sum(losses['example_losses'])/16-losses['mean_example_loss'])>1e-10:
            raise ValueError('Validation mean is incorrect')
    return {'status':'pass','scope':'Artifact integrity and measured loss/citation correspondence; scientific review pending.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.output.resolve()),indent=2))
