"""Archive an early failed final evaluation without claiming complete scores."""
import argparse,json,shutil
from pathlib import Path
import run_compact,run_corrective as u,verify_grounded as v
HERE=Path(__file__).resolve().parent

def package(source,final,comparison,output):
 cfg,root,_,_=run_compact.audit()
 if output.exists():raise ValueError('Use a fresh archive')
 base=v.rows(final/'base-final-test.jsonl');adapter=v.rows(final/'adapter-final-test.partial.jsonl')
 if len(base)!=12 or len(adapter)!=2 or [r['id'] for r in adapter]!=['precision-01','precision-02']:raise ValueError('Unexpected early-stop evidence')
 # Deliberately explicit assistant decisions; these are not automated truth scores.
 decisions=[{'id':'precision-01','pass':False,'reason':'COMET and thermomechanical deposition are identified, but finite elements are omitted and the answer invents a restriction to microstructure rather than other properties/processes.'},{'id':'precision-02','pass':False,'reason':'Diffusion, nucleation and growth are identified, but a non-source contrast with fatigue/stress-rupture transformations is added, confusing mechanical properties with phase transformations.'}]
 output.mkdir(parents=True)
 shutil.copytree(final,output/'raw-partial-evaluation')
 shutil.copytree(comparison,output/'profile-development')
 shutil.copyfile(source/'development-receipt.json',output/'training-receipt.json')
 for name in ('source-precision-profile.json','source_precision_profile.py'):shutil.copyfile(HERE/name,output/name)
 assessment={'status':'rejected_early_primary_scientific_screen','primary_rows':decisions,'primary_predictions_assessed':2,'primary_predictions_planned':12,'primary_maximum_possible_passes':10,'required_primary_passes':11,'base_predictions_generated':12,'adapter_primary_predictions_generated':2,'adapter_domain_predictions_generated':0,'predictions_sha256':v.sha(final/'adapter-final-test.partial.jsonl'),'independent_expert_validated':False,'scope':'Assistant source-grounded decisions, peer checked. Stop after two failures make the registered >=11/12 criterion impossible. Unfinished work is retained; no complete final or supplemental accuracy claimed. All twenty registered paragraphs are retired for future evaluation.'}
 u.save(output/'assistant-assessment.json',assessment)
 (output/'RESULTS.md').write_text('# Source profile: rejected early\n\nThe unchanged conservative Qwen3 adapter was evaluated with source-v10 after\npassing twelve retired development questions. Twelve paired base predictions\nand two adapter primary predictions were generated. Both adapter answers add\nunsupported restrictions or property comparisons. With two primary failures,\nthe registered requirement of at least 11/12 is already impossible. The run was\nstopped; no supplemental prediction was generated. No full-test score is claimed.\n\nRaw partial files and the frozen selection are retained. The entire registered\nprecision benchmark is excluded from subsequent final evaluation. These two\nfailed questions and a third failed base question enter later development only.\nIndependent scientific/translation review remains pending.\n')
 manifest={'status':assessment['status'],'model_id':cfg['model_id'],'revision':cfg['revision'],'checkpoint_weights_sha256':v.sha(source/'adapter/adapter_model.safetensors'),'weights_reference':'../qwen3-compact-001/adapter/adapter_model.safetensors','training_profile_sha256':u.load(source/'development-receipt.json')['profile_sha256'],'inference_profile':'source-v10','profile_sha256':v.sha(HERE/'source-precision-profile.json'),'profile_helper_sha256':v.sha(HERE/'source_precision_profile.py'),'evaluator_sha256':v.sha(HERE/'evaluate_selected.py'),'packager_sha256':v.sha(HERE/'package_rejected_source_profile.py'),'registered_test_manifest_sha256':v.sha(HERE/'precision-test-manifest.json'),'registered_domain_manifest_sha256':v.sha(HERE/'precision-domain-manifest.json'),'independent_expert_validated':False,'termination':'SIGTERM after two independently inspected primary failures; last status and partial raw files retained.','files_sha256':{str(p.relative_to(output)):v.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
 u.save(output/'package-manifest.json',manifest);return {'status':manifest['status'],'files':len(manifest['files_sha256'])}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','final','comparison','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(package(**{k:v.resolve() for k,v in vars(a).items()})))
