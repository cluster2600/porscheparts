"""Check corrective package provenance and recompute lexical evaluation screens."""
import argparse,json
from pathlib import Path
import evaluate_corrective
import run_corrective
import verify_grounded
HERE=Path(__file__).resolve().parent

def verify(output):
 cfg,root,manifest=run_corrective.audit()
 package=run_corrective.load(output/'package-manifest.json')
 for name,sha in package['files_sha256'].items():
  if verify_grounded.sha(output/name)!=sha:raise ValueError('Packaged file changed: '+name)
 receipt=run_corrective.load(output/'development-receipt.json');final=run_corrective.load(output/'final-receipt.json');selection=run_corrective.load(output/'frozen-selection.json');assessment=run_corrective.load(output/'assistant-final-assessment.json')
 if any(r['test_used_in_training'] for r in (receipt,final)) or final['test_used_for_checkpoint_selection']:raise ValueError('Test isolation violated')
 if any(r.get('independent_expert_validated',False) or r.get('expert_validated',False) for r in (receipt,final,selection,assessment,package)):raise ValueError('Unsupported expert claim')
 if receipt['dataset_manifest_sha256']!=verify_grounded.sha(root/'manifest.json') or package['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256']:raise ValueError('Data release mismatch')
 if verify_grounded.sha(output/'development-receipt.json')!=selection['development_receipt_sha256']:raise ValueError('Selection receipt mismatch')
 if verify_grounded.sha(output/'frozen-selection.json')!=final['selection_sha256']:raise ValueError('Selection changed after final test')
 for name,sha in final['files_sha256'].items():
  if verify_grounded.sha(output/name)!=sha:raise ValueError('Raw final result changed')
 weight_hash=verify_grounded.sha(output/'adapter/adapter_model.safetensors')
 if weight_hash!=final['checkpoint_weights_sha256'] or weight_hash!=selection['checkpoint_weights_sha256']:raise ValueError('Selected tensors changed')
 audit=run_corrective.load(output/'adapter-audit.json')
 if not audit['all_finite'] or audit['sha256']!=weight_hash or audit['nonzero_lora_b_tensors']!=audit['lora_b_tensors']:raise ValueError('Tensor audit mismatch')
 config=run_corrective.load(output/'adapter/adapter_config.json')
 if (config['base_model_name_or_path'],config['revision'])!=(cfg['model_id'],cfg['revision']):raise ValueError('Base pin mismatch')
 original=run_corrective.load(output/'source-adapter-config.json');original.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision'])
 if config!=original:raise ValueError('Unexpected adapter config transformation')
 questions=verify_grounded.rows(root/'final-test.jsonl')
 for kind in ('base','adapter'):
  predictions=verify_grounded.rows(output/(kind+'-final-test.jsonl'))
  if len(predictions)!=12 or [r['id'] for r in predictions]!=[r['id'] for r in questions]:raise ValueError('Final predictions incomplete')
  if evaluate_corrective.screen(questions,predictions)!=run_corrective.load(output/(kind+'-final-screen.json')):raise ValueError('Final screen changed')
 auxiliary=verify_grounded.rows(HERE/'corrective-domain-benchmark.jsonl')
 if verify_grounded.sha(HERE/'corrective-domain-benchmark.jsonl')!=final['auxiliary_benchmark_sha256']:raise ValueError('Domain benchmark changed')
 if evaluate_corrective.screen(auxiliary,verify_grounded.rows(output/'adapter-domain-test.jsonl'))!=run_corrective.load(output/'adapter-domain-screen.json'):raise ValueError('Domain screen changed')
 if assessment['predictions_sha256']!=verify_grounded.sha(output/'adapter-final-test.jsonl'):raise ValueError('Assessment prediction mismatch')
 return {'status':'pass','assessment_status':assessment['status'],'scope':'Integrity and recomputed lexical screens; assistant assessment is not independent expert review.'}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(verify(args.output.resolve()),indent=2))
