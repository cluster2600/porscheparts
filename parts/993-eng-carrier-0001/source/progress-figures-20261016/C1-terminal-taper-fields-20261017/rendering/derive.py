"""Private renderer derivation: actual closure schema and English labels only."""
import ast,difflib,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent.parent;O=R/'work/carrier-process-20261017/bounded-webs-C1-fields-figure-preparation-001/figure_v2.py';old=O.read_text();new=old;changes=[]
def replace(a,b):
 global new
 assert new.count(a)==1,(a[:100],new.count(a));new=new.replace(a,b);changes.append([a,b])
def function(name,text):
 tree=ast.parse(new);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name);replace(ast.get_source_segment(new,node),text.strip())
replace('"""Actual closed C1 FE fields, common scales and original field projection; no solver."""','"""Actual closed raw-taper FE fields; English diagnostic, no new solver."""')
function('validate_case', '''
def validate_case(row,docs,hashes,root_case):
    whole,a,native,record,peaks,energy,loads=[docs[k]for k in ['terminal','assessment','native_receipt','record','peaks','energy','loads']]
    role=row['role'];term=whole['cases'][role];expected={'rigid':'combined-rigid-static','spring':'combined-spring-1000-static'}
    require(role in expected and row['case']==expected[role]and a['case_name']==row['case']==record['name']==peaks['case']==energy['case'],'Wrong closed case identity')
    require(whole['status']=='two_actual_linear_static_cases_closed_no_qualification'and term['actual_tool_returncode']==term['actual_container_returncode']==term['attach_cli_returncode']==0 and term['owned_container_removed']is True and term['all_current_pins_equal']is True,'Case not actually closed')
    require(a['status']=='actual_linear_static_and_independent_energy_completed'and a['sources_unchanged']is True and a['plan_unchanged']is True and a['all_global_maxima_included']is True and a['candidate_qualified']is False and a['law_original_RC1_preserved']is True,'Assessment not complete or diagnostic scope changed')
    require(term['assessment_sha256']==hashes[row['assessment']]and term['native_receipt_sha256']==hashes[row['native_receipt']],'Terminal report cross-binding differs')
    require(root_case['assessment_sha256']==hashes[row['assessment']]and root_case['native_receipt_sha256']==hashes[row['native_receipt']]and root_case['actual_tool_RC']==0 and root_case['all31_whole_outputs_verified']is True and root_case['fresh_exact_Docker_ID_absent']is True,'Root closure differs')
    require(native['actual_container_exit_code']==native['attach_cli_returncode']==0 and native['container_removed']is True and native['input_hashes_unchanged']is True,'Native container not closed')
    require(a['native_result']==record and a['prepared_actual_load_supports']==loads and a['energy_audit_sha256']==hashes[row['energy']]and a['global_peaks_sha256']==hashes[row['peaks']],'Whole case result/load/audits differ')
    for key in ['record','field','deck','mesh_inp','mesh_npz','mesh_meta','loads','energy','peaks']:
        path=row[key];require(term['whole_outputs_sha256'][path]==hashes[path],'Actual output differs: '+key)
    require(record['mesh_sha256']==hashes[row['mesh_inp']]and record['input_sha256']==hashes[row['deck']],'Mesh/deck not same case')
    require(energy['energy_closure_pass']is True and energy['tolerance']==1e-4 and energy['relative_energy_closure_error']<=energy['tolerance'],'Original energy gate not passed')
    require(peaks['no_peak_excluded']is True and peaks['maximum_ties']==len(peaks['all_global_maximum_ties'])and peaks['maximum_VM_MPa']==record['integration_point_VM_max_MPa']and root_case['all_global_maximum_ties']==peaks['all_global_maximum_ties'],'Global IP ties lost')
    require(loads['target_force_N']==[0,0,-4000]and loads['target_moment_Nmm']==[0,850000,0]and loads['unchanged_original_distribute_unrounded_resultant_assertions_reached']is True,'Actual loads not declared study')
    require(loads['actual_eye_node_counts']==[2274,2278]and loads['serialized_CLOAD_entries']==6336,'Actual load/support roster differs')
    if role=='rigid':require(loads['rigid_constrained_DOFs']==13656 and loads['SPRING1_elements']==0 and loads['springs']==[],'Rigid support changed')
    else:
        require(loads['rigid_constrained_DOFs']==0 and loads['SPRING1_elements']==13656 and len(loads['springs'])==6,'Spring support changed')
        require({(s['eye'],s['DOF'])for s in loads['springs']}=={(i,j)for i in range(2)for j in range(1,4)}and all(s['summed_card_stiffness_N_mm']==s['declared_total_per_eye_axis_N_mm']==1000 for s in loads['springs']),'K1000 must be total per eye and axis')
    return dict(row,record_data=record,peak_data=peaks,energy_data=energy,load_data=loads)
''')
replace("plan['schema']=='actual-C1-two-case-fields-plan-1'","plan['schema']=='actual-new-taper-two-case-fields-plan-1'")
replace("if rendering:require(plan['launch_ready']is True,'NON-ARMED: no array extraction/render before root review')","if rendering:require(plan['launch_ready']is True and plan['root_GO_sha256']is not None and sha(plan['root_GO'])==plan['root_GO_sha256'],'NON-ARMED: no array extraction/render before root review')")
replace("review=read(root/plan['root_review']);require(review['status']=='root_closed_two_actual_C1_BREP_linear_cases_energy_PASS_all_peaks_preserved'and review['full_energy_and_peak_reports_wholly_preserved']is True,'Two root terminal reviews required')","review=read(root/plan['root_review']);require(review['schema']=='root-two-new-taper-linear-static-terminal-1'and review['status']=='closed_actual_RC0_two_new_taper_static_and_energy_cases'and review['actual_tool_RC']==0 and review['terminal_sha256']==hashes[plan['combined_terminal']]and review['all_global_peaks_retained']is True and review['candidate_qualified']is False and review['law_original_RC1_preserved']is True,'Two actual new-taper ROOT closures required')")
replace("review['BREP_sha256']","review['actual_new_BREP_sha256']")
replace("'carrier-C1-fields-001'","'carrier-terminal-taper-fields-001'")
labels={
'993 TURBO · PROTOTYPE C1 · DEUX CAS LINÉAIRES CLOS':'993 TURBO · PRESERVED TAPER · TWO CLOSED LINEAR CASES',
'Contraintes et déplacements sur le vrai maillage':'Stress and displacement on the actual T10 mesh',
'Fz = −4 000 N · My = +850 000 N·mm · mêmes caméra, axes en mm et échelles pour les deux cas':'Fz = −4 000 N · My = +850 000 N·mm · common camera, mm axes and field scales',
'89 788 C3D10 · 166 794 nœuds · déformée ×1 · BREP maître ':'89 536 C3D10 · 166 403 nodes · true deformation ×1 · raw BREP ',
'Rigide : 4 552 nœuds bloqués en XYZ. K1000 : 1 000 N/mm au total par œil et par axe, répartis sur 2 274 / 2 278 nœuds.':'Rigid: 4 552 nodes fixed in XYZ. K1000: 1 000 N/mm TOTAL per eye and axis, distributed over 2 274 / 2 278 nodes.',
"'Rigide'if":"'Rigid'if",
'K1000 · total par œil / axe':'K1000 · total per eye / axis',
'déplacements réels ×1':'actual displacement ×1',
'U projeté (mm)':'Projected U (mm)',
'V projeté (mm)':'Projected V (mm)',
"'Pic IP global'":"'Global IP peak'",
'Zoom XY commun · même échelle MPa':'Peak-region XY · shared MPa scale',
'|u| réel (mm)':'Actual |u| (mm)',
"colLabels=['Cas','Pic IP global (MPa)','Max frontière (MPa)','|u| tous nœuds (mm)','Élément / IP','XYZ IP au repos (mm)']":"colLabels=['Case','Global IP peak (MPa)','Boundary max (MPa)','All-node |u| (mm)','Element / IP','Reference IP XYZ (mm)']",
'Couleurs de contraintes : maximum des 4 IP par élément adjacent à une facette de frontière, sans extrapolation nodale. Cercles orange : tous les pics IP globaux.':'Stress colours: maximum of 4 IPs in each boundary-adjacent element, without nodal extrapolation. Orange circles: every global IP peak.',
'Facettes linéaires des coins des C3D10 ; déplacement de leurs sommets ×1. Gris : état au repos. Croix : tous les maxima de |u| parmi les nœuds.':'Linear C3D10 corner facets; actual corner displacement ×1. Grey: reference shape. Crosses: every all-node maximum of |u|.',
'Le champ de déplacement est coloré par le maximum des 3 nœuds de coin de chaque facette ; le maximum global inclut aussi les nœuds milieux.':'Displacement colours use the largest of each facet\u2019s 3 corner values; the global maximum also includes midside nodes.',
'Géométrie et maillage différents des campagnes STEP antérieures : comparaison descriptive seulement. Aucun critère de résistance ni convergence des contraintes établi.':'New raw-BREP geometry and mesh. Assumed linear loads/material; no strength allowable or stress convergence established.',
'Prototype CAO BREP · échange STEP refusé · résultats linéaires du cas de charge déclaré · vue orthographique 8° / 22°.':'Unqualified raw taper: post-Build law refusal retained; STEP exchange not qualified. Orthographic view 8° / 22°.',
'Actual C1 finite-element fields':'Actual preserved-taper finite-element fields',
'carrier-C1-contraintes-deplacements.':'carrier-terminal-taper-stress-displacement.',
'actual_closed_C1_fields_rendered_no_new_FEA':'actual_closed_new_taper_fields_rendered_no_new_FEA',
}
# Some short labels occur more than once in the inherited renderer, all presentation-only.
for a,b in labels.items():
 count=new.count(a);assert count>0,a;new=new.replace(a,b);changes.append([a,b,count])
replace("# Same XY display window as figure20; it is a crop only, never a measurement or mesh filter.\n    zoom=plan['display_zoom_XY_mm'];zoom_bounds=np.asarray(zoom)","# Actual peaks have opposite X signs: mirror the retained50mm display crop only.\n    zoom=plan['display_zoom_XY_mm']")
replace("row=c['row'];xyz=c['xyz'];ids=c['ids'];rest,_=project(xyz,basis)","row=c['row'];xyz=c['xyz'];ids=c['ids'];rest,_=project(xyz,basis);zoom_bounds=np.asarray(zoom[row['role']])")
replace("plt.close(fig);verify(plan_path,expected,True)","plt.close(fig);verify(plan_path,expected,True)\n    loaded_after={str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.split('.')[0]in ['numpy','matplotlib','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file()}\n    require(loaded_after<=set(runtime),'A post-export runtime file is outside the219 pinned files')")
replace("runtime_imported_files=sorted(loaded)","runtime_imported_files=sorted(loaded_after)")
restored=new
for item in reversed(changes):
 a,b,*count=item;assert restored.count(b)==(count[0] if count else 1);restored=restored.replace(b,a)
assert restored==old
(H/'figure.py').write_text(new)
(H/'source-changes.json').write_text(json.dumps(dict(source=str(O.relative_to(R)),source_sha256=hashlib.sha256(O.read_bytes()).hexdigest(),substitutions=changes,whole_inverse_equal=True),indent=2)+'\n')
(H/'figure-from-C1.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(O.relative_to(R)),tofile=str((H/'figure.py').relative_to(R)))))
