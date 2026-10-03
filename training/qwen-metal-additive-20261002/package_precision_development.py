"""Archive rejected precision SFT without claiming it reached the new final test."""
import argparse,json,shutil
from pathlib import Path
import run_precision,run_corrective as u,verify_grounded as v
HERE=Path(__file__).resolve().parent

def package(source,output,inventory):
 cfg,root,_,_=run_precision.audit();receipt=u.load(source/'development-receipt.json');audit=u.load(source/'adapter-audit.json')
 if output.exists() or receipt['status']!='development_completed' or receipt['final_test_generated']:raise ValueError('Invalid development archive')
 for key,name in [('config_sha256','precision-config-v7.json'),('profile_sha256','precision-terminology-profile.json'),('profile_helper_sha256','precision_terminology_profile.py'),('runner_sha256','run_precision.py')]:
  if receipt[key]!=v.sha(HERE/name):raise ValueError('Executed input changed')
 if receipt['dataset_manifest_sha256']!=v.sha(root/'manifest.json'):raise ValueError('Data changed')
 weights=source/'adapter/adapter_model.safetensors'
 if v.sha(weights)!=receipt['adapter_files_sha256']['adapter_model.safetensors'] or audit['sha256']!=v.sha(weights) or not audit['all_finite']:raise ValueError('Invalid adapter audit')
 output.mkdir(parents=True)
 for name in ('development-receipt.json','development-questions.jsonl','base-development.jsonl','base-development-screen.json','adapter-development.jsonl','adapter-development-screen.json','training-metrics.json','trainer-history.json','adapter-audit.json'):shutil.copyfile(source/name,output/name)
 for path,name in [(inventory,'runtime-freeze.txt'),(root/'MODEL-LICENSE.txt','MODEL-LICENSE.txt'),(source/'adapter/adapter_config.json','source-adapter-config.json')]:shutil.copyfile(path,output/name)
 (output/'adapter').mkdir();shutil.copyfile(weights,output/'adapter/adapter_model.safetensors')
 config=u.load(source/'adapter/adapter_config.json');config.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision']);u.save(output/'adapter/adapter_config.json',config)
 u.save(output/'assistant-development-assessment.json',{'status':'rejected_on_development','reviewers':['root assistant','pipeline_review assistant peer'],'decisive_failures':[{'id':'eval-001','reason':'Does not justify why one global measurement fails; replaces identification reasoning with non-equilibrium conditions.'},{'id':'fresh-03','reason':'Incorrectly names deposited height instead of substrate thickness explicitly stated as main influence.'}],'explanatory_regression':'Several yes/no questions collapse to bare Non plus reference; correct polarity does not establish useful scientific answers.','predictions_sha256':v.sha(output/'adapter-development.jsonl'),'new_final_test_generated':False,'independent_expert_validated':False})
 (output/'RESULTS.md').write_text('''# Precision SFT: rejected on development\n\nActual Qwen3 4B CPU BF16 LoRA trained 59 factual examples across seven languages,\n30 optimizer steps and one epoch in 1642.87 seconds. Mean training loss:2.15966.\nThe 144 tensors (2,949,120 parameters) are finite and all72 LoRA B tensors are\nnonzero. Adapter SHA-256:39dc305a84989261236e62edb1e818c4fc57dd86324ed1bf8c6c736184d7422e.\n\nDespite lower training loss, development answers are less useful: several\nbecome bare refusals and the model selects deposited height instead of substrate\nthickness. These raw outputs are retained. This candidate is rejected; no\nresponse on the newly registered precision final or domain tests was generated.\nThe earlier retired tests used here are development only, and three retired\ntraining-family paragraphs enter the correction curriculum. No source-held-out\narticle or new test paragraph enters SFT.\n\nA change in learning rate and curriculum accompanies this result; this does\nnot isolate either as the cause. Independent scientific/translation review is\npending. This trial is not recommended and does not qualify a physical part.\n''')
 manifest={'status':'rejected_on_development','inference_profile':'precision-v9','model_id':cfg['model_id'],'revision':cfg['revision'],'dataset_manifest_sha256':receipt['dataset_manifest_sha256'],'packager_sha256':v.sha(HERE/'package_precision_development.py'),'new_final_test_generated':False,'base_weights_included':False,'independent_expert_validated':False,'files_sha256':{str(p.relative_to(output)):v.sha(p) for p in output.rglob('*') if p.is_file()}}
 u.save(output/'package-manifest.json',manifest);return {'status':manifest['status'],'files':len(manifest['files_sha256'])}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','output','inventory'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(package(a.source.resolve(),a.output.resolve(),a.inventory.resolve())))
