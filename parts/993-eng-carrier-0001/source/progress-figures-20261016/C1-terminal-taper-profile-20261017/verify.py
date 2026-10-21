"""Full stored-evidence integrity only; no CAD/runtime imports or rendering."""
import contextlib,hashlib,importlib.util,io,json,math
from pathlib import Path
H=Path(__file__).resolve().parent;DEPENDENCY=H.parent/'C1-junction-section-20261017'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def require(ok,message):
 if not ok:raise ValueError(message)
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def evidence():
 require(sha(DEPENDENCY/'archive.json')=='ae765f3b3723edd8132ae51721c74a8300a388821babd169e55aed367ccb466e','Closed figure25 dependency differs')
 with contextlib.redirect_stdout(io.StringIO()):load('_figure25_stdlib_integrity',DEPENDENCY/'verify.py').main()
 oldroot=DEPENDENCY/'sources/mirror/work/carrier-C1-junction-section-figure-003';old=read(oldroot/'data-001/section-data.json');helper=load('_closed_original_profile_drawing_checks',oldroot/'figure.py');helper.check(old)
 d=read(H/'extraction/output-001/section-data.json');p=read(H/'extraction/plan.json');l=read(H/'extraction/launch-plan.json');s=read(H/'extraction/execution-001/execution-receipt.json');a=read(H/'extraction/output-001/assessment.json');t=read(H/'extraction/terminal-collection.json');root=read(H/'extraction/root-terminal-review-001.json');v=read(H/'extraction/output-001/native-volume-methods.json')
 require(root['actual_tool_RC']==0 and root['terminal_sha256']==sha(H/'extraction/terminal-collection.json')and root['supervision_sha256']==sha(H/'extraction/execution-001/execution-receipt.json')and root['data_sha256']==sha(H/'extraction/output-001/section-data.json')and root['volume_methods_sha256']==sha(H/'extraction/output-001/native-volume-methods.json'),'New extraction ROOT joins differ')
 require(s['actual_returncode']==0 and s['direct_child_reaped']and s['final_group_members']==[]and s['cleanup_error']is None and not s['timeout']and not s['interrupted']and s['command']==l['command']and s['sources_before']==s['sources_after']=={**l['inputs_sha256'],**l['source_sha256']},'Actual extraction supervision differs')
 require(d['cached_sections']==old['sections']and d['closed_reference_context']==old['diagnostic_context']and d['section_plane']==old['section_plane']==helper.plane(),'Whole closed baseline/C1 profiles/context/plane differ')
 require(d['producer_sha256']==sha(H/'extraction/extract.py')and d['plan_sha256']==sha(H/'extraction/plan.json')and d['source_sha256']==p['files_sha256']==a['sources_before']==a['sources_after']and a['sources_unchanged'],'Actual new-profile source context differs')
 section=d['taper_section'];points=[q for e in section['edges']for q in e['points_xyz_mm']]
 require(section['role']=='taper'and section['native_solids']==1 and section['edge_count']==len(section['edges'])==29 and len(points)==2335 and all(len(e['points_xyz_mm'])>=2 for e in section['edges']),'Whole taper section differs')
 require(all(len(q)==3 and all(type(x)is float and math.isfinite(x)for x in q)for q in points)and helper.coordinate_sha(section['edges'])==section['sampled_positions_sha256']==root['new_coordinate_sha256']and max(helper.plane_residual(q)for q in points)<=section['maximum_native_edge_tolerance_mm'],'Native drawing coordinate bytes/plane differ')
 require(d['native_volume_methods']==v==t['native_volume_methods']and v['same_native_Solid_identity_before_after']and v['same_Solid_passed_to_all_three_unchanged_calls']and v['adaptive_exact_binary64_equal_to_closed_reference']and v['Gmsh_getMass_mm3']is None,'Same-Solid actual volume record differs')
 require([r['arguments']for r in v['methods']]==[[False,False,False],[True,False,False],[1e-10,True,False]]and [r['signed_mass_mm3']for r in v['methods']]==[285603.15679600753,285603.15679600753,285602.88227244973]and all(r['signed_mass_mm3'].hex()==r['mass_binary64_hex']for r in v['methods']),'Actual overload values/hex differ')
 r=read(H/'rendering/render-001/render-receipt.json');rp=read(H/'rendering/plan.json');rl=read(H/'rendering/launch-plan.json');rs=read(H/'rendering/execution-001/execution-receipt.json');rt=read(H/'rendering/terminal-collection.json');rr=read(H/'rendering/root-terminal-review-001.json')
 require(rr['actual_tool_RC']==0 and rr['terminal_sha256']==sha(H/'rendering/terminal-collection.json')and rr['supervision_sha256']==sha(H/'rendering/execution-001/execution-receipt.json')and rr['render_receipt_sha256']==sha(H/'rendering/render-001/render-receipt.json'),'Actual draw ROOT joins differ')
 require(rs['actual_returncode']==0 and rs['direct_child_reaped']and rs['final_group_members']==[]and rs['cleanup_error']is None and not rs['timeout']and not rs['interrupted']and rs['command']==rl['command']and rs['sources_before']==rs['sources_after']=={**rl['inputs_sha256'],**rl['source_sha256']},'Actual draw supervision differs')
 require(r['source_sha256']==sha(H/'rendering/render.py')and r['data_sha256']==sha(H/'extraction/output-001/section-data.json')and r['profile_ROOT_review_sha256']==sha(H/'extraction/root-terminal-review-001.json'),'New draw producer/profile differs')
 require([x['role']for x in r['checks']]==['after','taper']and [x['full_native_edges_submitted']for x in r['checks']]==[30,29]and r['ray_plotted_on_original_C1_only']and not r['new_taper_ray_computed']and not r['global_thickness_claimed']and not r['candidate_qualified']and r['original_law_RC1_preserved']and not r['FEA_executed'],'Drawing scope differs')
 require(r['runtime_files_sha256']==rp['runtime_sha256']and len(r['runtime_files_sha256'])==219,'Historical plotting-runtime record differs')
 for name,h in r['outputs_sha256'].items():require(sha(H/name)==h==rt['exports'][name]['sha256'],'Whole actual export differs')
 require(rr['root_PNG_visually_inspected']and not rr['PDF_raster_view'],'Actual visual QA scope differs')
 return d,helper

def main():
 archive=read(H/'archive.json');actual={str(p.relative_to(H))for p in H.rglob('*')if p.is_file()and p.name!='archive.json'};require(actual==set(archive['files']),'Complete capsule file set differs')
 for name,row in archive['files'].items():
  p=H/name;require(not Path(name).is_absolute()and '..'not in Path(name).parts and not any(q.is_symlink()for q in [p,*p.parents]),'Unsafe archive path');require(p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'Capsule bytes/hash differ')
 evidence();print(json.dumps(dict(status='figure26_actual_evidence_capsule_verified_stdlib_only',payloads=len(actual),figure25_dependency=True,new_taper_edges=29,new_taper_points=2335,actual_three_formats=True,new_portable_render_replay_executed=False,CAD_or_runtime_copied=False,no_native_or_render=True)))
if __name__=='__main__':main()
