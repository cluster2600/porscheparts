"""Closed source-design and actual R1 observation joins; standard library only."""
import importlib.util,json
from pathlib import Path
D64='d64a7faf8455735e05198661be823ead7037c23b58d36522e1cca60056aea624'
R1='240109caadf961b2c5b70e580dcd50e6fef61dfd3aaa861cdb932c80a9df31a2'
ROOTS={'d64_ROOT':'e37d778f94894ae3cc9a34a8094d73ffd5688845b74be474a20843fffca10e20','analytical_ROOT':'d6b8cde5d559808e80048839b0e6b7f3192b9449577f2b1d7a2a887d87a0083a','old_H2_ROOT':'95259799b7ce902e304af8b6bf3b7a6d70d50cd531ac9d33b292dd176daa584d','section_ROOT':'43dfe089ff92e52a9976e4d25ad7266fd48f221ffe2d6adf7fb45abfc160fd12'}
def require(ok,message):
 if not ok:raise ValueError(message)
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def verify(p,R):
 def bound(k):
  path=p[k];require(path in p['files_sha256'],'Unpinned metadata role');return json.loads((R/path).read_text())
 for role,digest in ROOTS.items():require(p['files_sha256'][p[role]]==digest,'Foreign closed source/design ROOT: '+role)
 root,owner,assessment=[bound(k)for k in ['d64_ROOT','d64_owner','d64_assessment']]
 require(root['schema']=='root-stock-outward-C2-rib-trial002-terminal-review-1'and root['status']=='closed_actual_RC0_one_valid_rebuilt_rib_candidate_strict_retention_and_original_local_gates_PASS','Actual d64 direct-source scope differs')
 require(root['owner_terminal_sha256']==p['files_sha256'][p['d64_owner']]and owner['evidence']['assessment_sha256']==p['files_sha256'][p['d64_assessment']],'d64 ROOT/owner/assessment crossed')
 require(root['candidate_BREP_sha256']==owner['evidence']['raw_candidate_sha256']==p['files_sha256'][p['current_BREP']]==D64 and owner['actual_child_returncode']==0 and owner['direct_child_reaped']and owner['owned_group_empty'],'d64 source candidate is not closed')
 require(root['measurements']==owner['evidence']['complete_measurements_before_gates']and root['native_Cut_summaries']==owner['evidence']['complete_native_Cut_summaries']==assessment['native_Cut_summaries'],'Whole d64 measurements/Cuts crossed')
 reference=bound('reference_R1_plan')
 for name,digest in reference['files_sha256'].items():require(p['files_sha256'].get(name)==digest,'R1 evidence closure input differs')
 context=load('_retained_whole_R1_peak_context',R/p['R1_context_source'])
 context.verify_target(reference,R);context.select_common(reference,[json.loads((R/n).read_text())for n in reference['peak_files']],json.loads((R/reference['root_cases']).read_text()),json.loads((R/reference['combined_cases_terminal']).read_text()))
 own_root,own,observed=[bound(k)for k in ['R1_observer_ROOT','R1_observer_owner','R1_observer_assessment']]
 require(own_root['schema']=='root-R1-own-peak-terminal-review-1'and own_root['status']=='closed_actual_RC0_whole_owner_and_stored_byte_match'and own_root['owner_sha256']==p['files_sha256'][p['R1_observer_owner']]and own['assessment_sha256']==p['files_sha256'][p['R1_observer_assessment']],'Actual R1 own-peak observation crossed')
 require(own_root['candidate_BREP_sha256']==p['files_sha256'][p['R1_BREP']]==R1 and observed['status']=='actual_R1_at_own_common_IP_native_diagnostic_complete'and observed['sources_unchanged'],'Actual R1 observation identity differs')
 analysis=bound('analytical_trial');require(analysis['candidate_version']=='first-window-root-corner-slide-v1'and analysis['scaled_X_slide_mm']=='3/2'and analysis['scaled_Y_slide_mm']=='15/136'and analysis['R1_fillets_automatically_reapplied']is False,'Fixed one-corner analytical design differs')
 old_h2=bound('old_H2_ROOT');require(old_h2['schema']=='root-R1-discrete-H2-refusal-terminal-review-1'and old_h2['status']=='actual_RC1_four_passes_volume_refusal_whole_owner_and_stored_byte_match'and old_h2['candidate_BREP_sha256']==R1 and old_h2['final_full_H2_measurement_NOT_reached']is True,'Original generated-reference volume refusal must remain')
 section=bound('section_ROOT');require(section['schema']=='root-R1-actual-peak-section-terminal-review-1'and section['status']=='actual_RC0_whole_owner_and_stored_bytes_match'and section['complete_sampled_data_sha256']==p['files_sha256'][p['section_data']],'Actual closed own-peak section differs')
 contract=bound('interface_contract');require(contract['study_central_centres_xy_mm']==[[-50,-20],[-50,20],[50,-20],[50,20]]and contract['study_tool_radius_mm']==12.5 and contract['study_carrier_pad_z_mm']==[-4,4],'Original all-four tool and pad recipe differs')
 require(p['candidate_version']=='first-window-root-corner-slide-v1'and p['R1_material_retention_required']is False and p['R1_fillet_inherited']is False and p['full_protected_interfaces_required_downstream']is True,'Distinct direct-source revision scope differs')
 return dict(d64=root,R1_observer=own_root,analysis=analysis)
