"""Reuse development generations only when corrected routing preserves exact inputs."""
import argparse,json,shutil
from pathlib import Path
import run_corrective,verify_grounded,concise_qualified_profile_v7
HERE=Path(__file__).resolve().parent

def bind(source,output):
 if output.exists():raise ValueError('Use a fresh equivalence directory')
 receipt=run_corrective.load(source/'profile-receipt.json')
 if receipt['status']!='development_completed' or receipt['final_test_generated']:raise ValueError('Not a development-only comparison')
 for name,sha in receipt['files_sha256'].items():
  if verify_grounded.sha(source/name)!=sha:raise ValueError('Original development evidence changed')
 for key,name in [('profile_sha256','concise-qualified-profile.json'),('profile_helper_sha256','concise_qualified_profile.py'),('comparator_sha256','compare_concise_qualified_profile.py')]:
  if receipt[key]!=verify_grounded.sha(HERE/name):raise ValueError('Executed development inputs changed')
 expected=concise_qualified_profile_v7.questions_with_profile(verify_grounded.rows(HERE/'corrective-v4/development.jsonl'))
 if expected!=verify_grounded.rows(source/'questions.jsonl'):raise ValueError('Corrected helper changes development inputs; generate a new comparison')
 output.mkdir(parents=True)
 for name in receipt['files_sha256']:shutil.copyfile(source/name,output/name)
 shutil.copyfile(source/'profile-receipt.json',output/'executed-v6-profile-receipt.json')
 result={**receipt,'profile_helper_sha256':verify_grounded.sha(HERE/'concise_qualified_profile_v7.py'),'predictions_reused':True,'generation_helper_sha256':receipt['profile_helper_sha256'],'executed_receipt_sha256':verify_grounded.sha(source/'profile-receipt.json'),'equivalence_binder_sha256':verify_grounded.sha(HERE/'bind_profile_equivalence.py'),'exact_development_input_equivalence':True,'scope':'No new inference claimed. The corrected helper yields exactly the originally generated development inputs; source-excerpt words cannot route inference.','files_sha256':{p.name:verify_grounded.sha(p) for p in output.iterdir() if p.is_file()}}
 run_corrective.save(output/'profile-receipt.json',result)
 return {'status':'exact_input_equivalence','questions':len(expected),'predictions_reused':True}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('source','output'):parser.add_argument('--'+name,type=Path,required=True)
 args=parser.parse_args();print(json.dumps(bind(args.source.resolve(),args.output.resolve())))
