"""Package a reviewed corrective experiment without copying base weights."""
import argparse,json,shutil
from pathlib import Path
import run_corrective
import verify_grounded
HERE=Path(__file__).resolve().parent

def package(source,final,assessment,summary,inventory,output):
 cfg,root,_=run_corrective.audit()
 if output.exists():raise ValueError('Use a fresh result package')
 receipt=run_corrective.load(source/'development-receipt.json');end=run_corrective.load(final/'final-receipt.json');selection=run_corrective.load(final/'frozen-selection.json')
 reviewed=run_corrective.load(assessment)
 if end['status']!='final_test_completed' or end['test_used_for_checkpoint_selection'] or end['independent_expert_validated']:raise ValueError('Invalid final run status')
 if reviewed['independent_expert_validated'] or reviewed['status'] not in ('accepted_on_registered_benchmark','failed_registered_benchmark'):raise ValueError('Missing truthful assessment')
 for name,sha in end['files_sha256'].items():
  if verify_grounded.sha(final/name)!=sha:raise ValueError('Final result changed')
 if reviewed['predictions_sha256']!=verify_grounded.sha(final/'adapter-final-test.jsonl'):raise ValueError('Assessment belongs to different predictions')
 if receipt['runner_sha256']!=verify_grounded.sha(HERE/'run_corrective.py') or end['evaluator_sha256']!=verify_grounded.sha(HERE/'evaluate_corrective.py'):raise ValueError('Executed code changed')
 if receipt['dataset_manifest_sha256']!=verify_grounded.sha(root/'manifest.json') or end['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256']:raise ValueError('Data provenance changed')
 checkpoint=source/'checkpoints'/selection['checkpoint']
 if verify_grounded.sha(checkpoint/'adapter_model.safetensors')!=end['checkpoint_weights_sha256']:raise ValueError('Selected weights changed')
 audit=run_corrective.load(source/(selection['checkpoint']+'-audit.json'))
 if not audit['all_finite'] or audit['nonzero_lora_b_tensors']!=audit['lora_b_tensors'] or audit['sha256']!=end['checkpoint_weights_sha256']:raise ValueError('Tensor audit failed')
 output.mkdir(parents=True)
 names=['development-receipt.json','base-development.jsonl','base-development-screen.json','training-metrics.json','trainer-history.json']
 names+=[p.name for p in sorted(source.glob('checkpoint-*-development*.json*'))]
 for name in names:shutil.copyfile(source/name,output/name)
 for name in end['files_sha256']:shutil.copyfile(final/name,output/name)
 shutil.copyfile(final/'final-receipt.json',output/'final-receipt.json')
 for path,name in [(assessment,'assistant-final-assessment.json'),(summary,'RESULTS.md'),(inventory,'runtime-freeze.txt'),(HERE/'MODEL-LICENSE.txt','MODEL-LICENSE.txt')]:shutil.copyfile(path,output/name)
 shutil.copyfile(source/(selection['checkpoint']+'-audit.json'),output/'adapter-audit.json')
 shutil.copyfile(checkpoint/'adapter_config.json',output/'source-adapter-config.json')
 shutil.copyfile(checkpoint/'trainer_state.json',output/'selected-trainer-state.json')
 (output/'adapter').mkdir();shutil.copyfile(checkpoint/'adapter_model.safetensors',output/'adapter/adapter_model.safetensors')
 config=run_corrective.load(checkpoint/'adapter_config.json');config.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision']);run_corrective.save(output/'adapter/adapter_config.json',config)
 manifest={'status':reviewed['status'],'model_id':cfg['model_id'],'revision':cfg['revision'],'dataset_manifest_sha256':receipt['dataset_manifest_sha256'],'base_weights_included':False,'independent_expert_validated':False,'packager_sha256':verify_grounded.sha(HERE/'package_corrective.py'),'config_normalization':'Only public base model ID and pinned revision; tensors unchanged.','files_sha256':{str(p.relative_to(output)):verify_grounded.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
 run_corrective.save(output/'package-manifest.json',manifest)
 return {'status':manifest['status'],'files':len(manifest['files_sha256'])}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('source','final','assessment','summary','inventory','output'):parser.add_argument('--'+name,type=Path,required=True)
 args=parser.parse_args();print(json.dumps(package(**{k:v.resolve() for k,v in vars(args).items()})))
