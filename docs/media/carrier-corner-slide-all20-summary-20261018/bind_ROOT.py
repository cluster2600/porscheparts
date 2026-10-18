"""Bind only the actual formal all20 closure; preserve the complete pre-ROOT data snapshot."""
import copy,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];F=R/'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-twenty-static-preparation-002'
ROOT_SHA='dc26accac6af16ba323b0e196555c681de95aeffff1d3fdb29c9fd12e145936c'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def validate(d,root):
 assert root['schema']=='root-current24af-twenty-static-terminal-review-1'and root['status']=='closed_actual_RC0_all20_current24af_whole_fields_energy_peaks_resources_and_process_absence_PASS'
 assert root['owner_terminal_sha256']=='ccf9d868b5faa83d5128e16210bdd0fe2b8162258d0c05a09f9fb9e2e2bcfaa8'and root['process_absence_supplement_sha256']=='ec7dd4b46f8ff469232ef25060527dd0fce1aa74b272a56a2f58645351ad6ad1'
 assert root['all20_owner_objects_and_encoded_bytes_equal']and root['supplement_object_and_encoded_bytes_equal']and root['all20_original_native_resource_and_plan_guards_replayed']and root['fresh_exact_DockerIDs_and_host_PID_PGID_absent']and root['all_global_peak_ties_retained']and root['output_FD_count']==620
 assert set(root['actual_results'])==set(d['cases'])and len(d['cases'])==20
 for key,row in d['cases'].items():
  r=root['actual_results'][key];record=row['actual_native_result'];energy=row['independent_energy_audit'];peaks=row['all_global_peak_ties']
  assert r['force_N']==row['force_N']and r['moment_Nmm']==row['moment_Nmm']and r['support_N_mm']==row['support_N_mm']
  assert r['VM_MPa']==record['integration_point_VM_max_MPa']and r['U_mm']==record['displacement_max_mm']and r['energy_relative_error']==energy['relative_energy_closure_error']and r['full_global_peak_ties']==peaks['all_global_maximum_ties']
 return True
if __name__=='__main__':
 p=F/'root-solver-terminal-review-001.json';assert sha(p)==ROOT_SHA;root=read(p);original=read(H/'data.json');validate(original,root);d=copy.deepcopy(original)
 d.update(formal_ROOT_path=str(p.relative_to(R)),formal_ROOT_sha256=ROOT_SHA,ROOT_acceptance='CLOSED_actual20_numeric_cases_only');d['source_files_sha256'][str(p.relative_to(R))]=ROOT_SHA
 back=copy.deepcopy(d);back.update(formal_ROOT_path=None,formal_ROOT_sha256=None,ROOT_acceptance='PENDING');del back['source_files_sha256'][str(p.relative_to(R))]
 assert back==original and(json.dumps(back,indent=2,allow_nan=False)+'\n').encode()==(H/'data.json').read_bytes()
 with(H/'data-closed.json').open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
 text=(H/'SUMMARY.md').read_text().replace('Formal all20 ROOT closure is pending; no convergence or strength qualification is assigned.','All20 cases are formally closed by ROOT `'+ROOT_SHA+'`; no convergence or strength qualification is assigned.')
 with(H/'SUMMARY-closed.md').open('x')as f:f.write(text)
 with(H/'ROOT-binding-inverse.json').open('x')as f:json.dump(dict(original_data_sha256=sha(H/'data.json'),bound_data_sha256=sha(H/'data-closed.json'),whole_original_NULL_snapshot_object_and_bytes_inverse=True,changed_metadata_fields=['formal_ROOT_path','formal_ROOT_sha256','ROOT_acceptance','source_files_sha256 ROOT addition only'],all20_whole_scientific_case_objects_unchanged=True),f,indent=2);f.write('\n')
 print(sha(H/'data-closed.json'))
