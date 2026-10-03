"""Package the second precision cycle with truthful raw evidence and portable LoRA."""
import argparse,json,shutil
from pathlib import Path
import run_precision,run_corrective as u,verify_grounded as v
HERE=Path(__file__).resolve().parent

def package(source,final,assessment,summary,inventory,output):
 cfg,root,_,_=run_precision.audit()
 if output.exists():raise ValueError('Use a fresh result package')
 receipt=u.load(source/'development-receipt.json');end=u.load(final/'final-receipt.json');selection=u.load(final/'frozen-selection.json');reviewed=u.load(assessment)
 if end['status']!='final_test_completed' or end['test_used_for_checkpoint_selection'] or any(x.get('independent_expert_validated',False) for x in (receipt,end,selection,reviewed)):raise ValueError('Invalid final provenance or expert claim')
 if reviewed['status'] not in ('accepted_on_registered_benchmark','failed_registered_benchmark'):raise ValueError('Missing final assessment')
 for name,sha in end['files_sha256'].items():
  if v.sha(final/name)!=sha:raise ValueError('Final result changed')
 for key,name in [('config_sha256','precision-config-v7.json'),('profile_sha256','precision-terminology-profile.json'),('profile_helper_sha256','precision_terminology_profile.py')]:
  if receipt[key]!=v.sha(HERE/name) or end[key]!=receipt[key]:raise ValueError('Executed inputs changed')
 if receipt['runner_sha256']!=v.sha(HERE/'run_precision.py') or end['evaluator_sha256']!=v.sha(HERE/'evaluate_precision.py'):raise ValueError('Executed code changed')
 if end['dataset_manifest_sha256']!=v.sha(root/'manifest.json') or receipt['dataset_manifest_sha256']!=end['dataset_manifest_sha256']:raise ValueError('Executed data changed')
 if reviewed['predictions_sha256']!=v.sha(final/'adapter-final-test.jsonl') or reviewed['domain_predictions_sha256']!=v.sha(final/'adapter-domain-test.jsonl'):raise ValueError('Assessment belongs to different predictions')
 checkpoint=source/'adapter';audit=u.load(source/'adapter-audit.json');weight_hash=v.sha(checkpoint/'adapter_model.safetensors')
 if weight_hash!=end['checkpoint_weights_sha256'] or weight_hash!=selection['checkpoint_weights_sha256'] or weight_hash!=audit['sha256'] or not audit['all_finite'] or audit['nonzero_lora_b_tensors']!=audit['lora_b_tensors']:raise ValueError('Weights or tensor audit changed')
 output.mkdir(parents=True)
 for name in ('development-receipt.json','development-questions.jsonl','base-development.jsonl','base-development-screen.json','adapter-development.jsonl','adapter-development-screen.json','training-metrics.json','trainer-history.json','adapter-audit.json'):shutil.copyfile(source/name,output/name)
 for name in end['files_sha256']:shutil.copyfile(final/name,output/name)
 shutil.copyfile(final/'final-receipt.json',output/'final-receipt.json')
 for path,name in [(assessment,'assistant-final-assessment.json'),(summary,'RESULTS.md'),(inventory,'runtime-freeze.txt'),(root/'MODEL-LICENSE.txt','MODEL-LICENSE.txt'),(checkpoint/'adapter_config.json','source-adapter-config.json'),(HERE/'precision-terminology-profile.json','precision-terminology-profile.json'),(HERE/'precision_terminology_profile.py','precision_terminology_profile.py')]:shutil.copyfile(path,output/name)
 (output/'adapter').mkdir();shutil.copyfile(checkpoint/'adapter_model.safetensors',output/'adapter/adapter_model.safetensors')
 config=u.load(checkpoint/'adapter_config.json');config.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision']);u.save(output/'adapter/adapter_config.json',config)
 manifest={'status':reviewed['status'],'inference_profile':'precision-v9','model_id':cfg['model_id'],'revision':cfg['revision'],'dataset_manifest_sha256':receipt['dataset_manifest_sha256'],'base_weights_included':False,'independent_expert_validated':False,'packager_sha256':v.sha(HERE/'package_precision.py'),'previous_failed_trial_manifest_sha256':v.sha(HERE/'runs/qwen3-compact-001/package-manifest.json'),'config_normalization':'Only public base ID and pinned revision; tensors unchanged.','files_sha256':{str(p.relative_to(output)):v.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
 u.save(output/'package-manifest.json',manifest);return {'status':manifest['status'],'files':len(manifest['files_sha256'])}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','final','assessment','summary','inventory','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(package(**{k:v.resolve() for k,v in vars(a).items()})))
