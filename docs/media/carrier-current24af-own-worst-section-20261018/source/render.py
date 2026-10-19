"""Actual R1 section and explicitly projected 3D chords; no CAD or FEA operations."""
import hashlib,importlib.util,json,math,os,resource,signal,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok,message):
 if not ok:raise ValueError(message)

def write(p,x):
 with Path(p).open('x')as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def read(path):return json.loads(Path(path).read_text())
def yz(point):return [point[1],point[2]]
def projected_chord(face):
 props=face['local_properties'];chord=props['local_chord'];require(chord and chord['status']=='unambiguous_first_native_in_out_normal_chord','Selected support must have a qualified original chord')
 hits=[q for q in props['normal_line_intersections']if q['face_index_zero_based']==chord['target_face_index_zero_based']and q['W_mm']==chord['thickness_mm']]
 require(len(hits)==1,'Exact retained chord endpoint must be unique')
 start,end=props['point_mm'],hits[0]['point_mm']
 require(all(len(q)==3 and all(math.isfinite(v)for v in q)for q in [start,end]),'Finite retained 3D endpoints required')
 return dict(source_face=face['face_index_zero_based'],target_face=chord['target_face_index_zero_based'],length_3D_mm=chord['thickness_mm'],start_xyz_mm=start,end_xyz_mm=end,projected_start_YZ_mm=yz(start),projected_end_YZ_mm=yz(end),projection_only=True,section_thickness_claimed=False)

def reciprocal_pairs(native):
 faces=native['probes'][0]['nearest_faces'];qualified=[];unresolved=[]
 for face in faces:
  chord=face['local_properties'].get('local_chord')
  if chord and chord['status']=='unambiguous_first_native_in_out_normal_chord':qualified.append((face,projected_chord(face)))
  else:unresolved.append(dict(face=face['face_index_zero_based'],status=face['local_properties'].get('status'),chord=chord))
 require(len({row['source_face']for face,row in qualified})==len(qualified),'Duplicate qualified source support')
 pairs=[];used=set()
 for face,row in qualified:
  if row['source_face']in used:continue
  reverse=[(other,chord)for other,chord in qualified if chord['source_face']==row['target_face']and chord['target_face']==row['source_face']]
  require(len(reverse)==1,'Every displayed qualified support must have one actual reciprocal support')
  other,back=reverse[0];require(back['source_face']!=row['source_face'],'Self-pair is not a reciprocal support pair')
  pairs.append([row,back]);used.update([row['source_face'],back['source_face']])
 require(len(used)==len(qualified),'A qualified nearest support was dropped')
 return pairs,unresolved

def closed_data(p):
 require(p['schema']=='actual-current24af-own-worst-section-projected-chords-figure-plan-1','Wrong image scope')
 require(all(sha(R/n)==v for n,v in p['files_sha256'].items()),'Pinned data/source/runtime differs')
 section=R/p['section_preparation'];review=read(section/'root-terminal-review-001.json');owner=read(section/'terminal-collection-001.json');plan=read(section/'plan.json');a=read(section/'output-001/assessment.json');data=read(section/'output-001/own_current24af_worst-section-data.json')
 require(sha(section/'root-terminal-review-001.json')==p['section_ROOT_sha256']=='f5797f5811c03e4d9bc75540c5fb71707957bb8774bfae3d21b3cc5c76ca2335'and review['schema']=='root-current24af-own-worst-section-terminal-review-1'and review['status']=='closed_actual_RC0_current24af_own_worst_raw_section_and_complete_samples_PASS','Wrong actual section ROOT')
 require(review['owner_terminal_sha256']==sha(section/'terminal-collection-001.json')=='a43f71420d279e00a071ab8efc907cb45d985024127fda453cede3145a04d279'and owner['assessment_sha256']==sha(section/'output-001/assessment.json'),'Whole section ROOT/owner/assessment join differs')
 require(owner['status']=='closed_actual_RC0_current24af_own_worst_raw_section_and_complete_samples_only'and owner['actual_child_returncode']==0 and owner['direct_child_reaped']and owner['owned_group_empty']and owner['fresh_PID_and_PGID_absent']and review['fresh_PID_PGID_absent'],'Section process is not closed')
 require(review['complete_section_data_sha256']==owner['complete_section_data_sha256']==sha(section/'output-001/own_current24af_worst-section-data.json')and review['raw_section_BREP_sha256']==owner['raw_section_BREP_sha256']==sha(section/'output-001/own_current24af_worst-section.brep'),'Actual native section data/curves differ')
 require(data['plan_sha256']==sha(section/'plan.json')and data['producer_sha256']==sha(section/'extract.py')and data['drawing_deflection_mm']==.001 and data['Approximation']is data['RunParallel']is False,'Original actual section producer/settings differ')
 records=load('_closed_actual_current24af_section_records',section/'records.py');planes=records.closed(plan,R);require(data['plane']==planes[0]and len(planes)==1,'Actual section plane differs')
 extract=load('_retained_actual_current24af_section_pure_checks',section/'extract.py');check=extract.check_section(data['section'],planes[0]);require(check==owner['whole_original_sample_checks']==review['whole_original_sample_checks']and check['edge_count']==28 and check['drawing_points']==708,'Complete original section checks differ')
 require(a['sources_before']==a['sources_after']==plan['files_sha256']and a['sources_unchanged']and data['candidate_BREP_sha256']==plan['BREP_sha256']==p['candidate_BREP_sha256']==records.QUERY,'Actual source maps or current24af geometry differ')
 observer=R/p['observer_preparation'];native=read(observer/'output-001/assessment.json');native_owner=read(observer/'terminal-collection-001.json');native_root=read(observer/'root-terminal-review-001.json');observer_plan=read(observer/'plan.json')
 require(sha(observer/'root-terminal-review-001.json')==plan['observation_ROOT_sha256']==p['observation_ROOT_sha256']=='edf7b2e91aa05e5616ae1dd5e3d94552930d1dd5a4e05717b00e5ddfd4a4f972','Foreign actual own-worst observation ROOT')
 require(native_root['owner_terminal_sha256']==sha(observer/'terminal-collection-001.json')==plan['actual_observation']['owner_sha256']and native_owner['assessment_sha256']==native_root['assessment_sha256']==sha(observer/'output-001/assessment.json'),'Whole actual observation joins differ')
 require(native['CAD_source']['sha256']==native['reference_FE_CAD_source']['sha256']==p['candidate_BREP_sha256']and native['case_peak']==native_owner['reference_case_peak']==native_root['actual_peak']==plan['selected_case_peak']and native['selected_case']==observer_plan['selected_case']==p['selected_case'],'Peak and actual section belong to different current geometry/case')
 require(native['case_peak']['reference_undeformed_IP_xyz_mm'][0]==data['plane']['origin_mm'][0]and native_root['complete_qualified_chord_rows']==native_owner['exact_recomputed_chord_rows']and native_root['complete_null_rows']==native_owner['retained_null_rows'],'Exact own-peak plane or complete chord/null rows differ')
 require(observer_plan['peak_files'][observer_plan['case_keys'].index(p['selected_case'])]==p['global_peak_file'],'Selected actual peak file is not the selected all20 case')
 peak=read(R/p['global_peak_file']);require(peak['all_global_maximum_ties']==[observer_plan['all_worst_case_and_peak_ties'][0]['whole_peak']]and peak['no_peak_excluded'],'Entire selected global tie object differs')
 pairs,unresolved=reciprocal_pairs(native);require(len(pairs)==p['projected_reciprocal_pair_count']==2 and sum(map(len,pairs))==4 and len(unresolved)==4,'Actual nearest support qualification roster differs')
 require(p['normal_chords_projected_to_YZ']is True and p['section_thickness_claimed']is False and p['new_CAD_or_FEA']is False,'Projected 3D chord scope must stay explicit')
 return data,native,native_owner

def verify(path,expected,rendering=False):
 require(sha(path)==expected,'Render plan differs');p=read(path)
 if rendering:require(p['launch_ready']is True and p['root_GO_sha256']is not None and sha(R/p['root_GO'])==p['root_GO_sha256'],'NON-ARMED: no authoring before ROOT GO')
 require(p['bounds']==dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0),'Original render bounds differ')
 out=R/p['output_directory'];require(not out.exists()and not any(q.is_symlink()for q in [out,*out.parents]),'Fresh nonsymlink render output required')
 data,native,owner=closed_data(p);return p,data,native,owner

def render(path,expected):
 p,data,native,owner=verify(path,expected,True);require(os.getpriority(os.PRIO_PROCESS,0)==10 and all(os.environ.get(k)=='1'for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']),'Inherited nice10/BLAS1 required')
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s draw-only budget')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141));began=time.monotonic()
 before={n:sha(R/n)for n in p['runtime_sha256']};require(before==p['runtime_sha256'],'Plot runtime differs before import')
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib.font_manager import findfont,FontProperties
 matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':'#183347','axes.labelcolor':'#536D7D','svg.fonttype':'none','svg.hashsalt':'carrier-current24af-own-worst-native-section-20261018','pdf.fonttype':42,'path.simplify':False})
 lines=[[yz(q)for q in e['points_xyz_mm']]for e in data['section']['edges']];allpoints=[q for line in lines for q in line];peak=native['case_peak']['reference_undeformed_IP_xyz_mm'];pairs,unresolved=reciprocal_pairs(native)
 chords=[chord for pair in pairs for chord in pair];colors=['#A4457B','#087E8B','#995D00','#5963AE']
 mesh_peak=read(R/p['global_peak_file'])['all_global_maximum_ties'][0];require(mesh_peak['reference_undeformed_IP_xyz_mm']==peak,'Actual peak plotting point moved');lo,hi=mesh_peak['corner_measure']['bounds_mm']
 fig,axes=plt.subplots(1,2,figsize=(14.5,8.7),facecolor='#F8FAFC');fig.subplots_adjust(left=.065,right=.96,top=.75,bottom=.34,wspace=.2)
 fig.text(.06,.94,'993 TURBO · CURRENT 24af · ACTUAL NATIVE SECTION',fontsize=11,weight='bold',color='#536D7D')
 fig.text(.06,.886,'Geometry at the current all20 worst stress peak',fontsize=22,weight='bold')
 fig.text(.06,.834,f'X = {data["plane"]["origin_mm"][0]:.14f} mm · element 81426 / IP3 · reverse-torque combined / spring support',fontsize=10.2)
 checks=[]
 for i,ax in enumerate(axes):
  ax.set_facecolor('white');ax.grid(color='#DCE4E9',linewidth=.6);ax.set_axisbelow(True);ax.add_collection(LineCollection(lines,colors='#30576E',linewidths=1.8,label='Actual native section'))
  ax.plot(peak[1],peak[2],'o',color='#D47732',ms=5,label='Actual all20 worst FE IP')
  limits=([min(q[0]for q in allpoints),max(q[0]for q in allpoints)],[min(q[1]for q in allpoints),max(q[1]for q in allpoints)])if i==0 else([lo[1],hi[1]],[lo[2],hi[2]])
  ax.set(xlim=limits[0],ylim=limits[1],xlabel='Y (mm)',ylabel='Z (mm)');ax.set_aspect('equal',adjustable='box');ax.set_title('Whole native section'if i==0 else'Actual peak-element bounds\nY–Z projection',loc='left',weight='bold',pad=12)
  for spine in ax.spines.values():spine.set_color('#B8C8D2')
  checks.append(dict(full_native_edges_submitted=len(lines),sampled_positions_sha256=data['section']['sampled_positions_sha256'],xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),aspect=ax.get_aspect(),display_crop_only=i==1))
 axes[0].legend(loc='lower left',fontsize=8)
 for chord,color in zip(chords,colors):
  start,end=chord['projected_start_YZ_mm'],chord['projected_end_YZ_mm'];axes[1].plot([start[0],end[0]],[start[1],end[1]],color=color,lw=1.5,ls='--',marker='o',ms=3)
 fig.text(.06,.256,'Dashed segments show both qualified reciprocal pairs at the actual IP.',fontsize=12,weight='bold',color='#A55A25')
 fig.text(.06,.220,'These are Y–Z projections of measured 3D normal chords, not thicknesses of the displayed section; endpoint X values differ.',fontsize=9.8)
 for y,chord,color in zip([.180,.145,.110,.075],chords,colors):fig.text(.06,y,f'Face {chord["source_face"]} → {chord["target_face"]}: 3D normal chord {chord["length_3D_mm"]:.9f} mm; endpoint X = {chord["start_xyz_mm"][0]:.9f} → {chord["end_xyz_mm"][0]:.9f} mm',fontsize=10,color=color)
 fig.text(.06,.030,'All 28 native curves / 708 samples retained · 4 local NULL rows at this IP and all five-probe unresolved rows kept in receipt · no new CAD or FEA',fontsize=8.7,color='#536D7D')
 font=findfont(FontProperties(family='DejaVu Sans'),fallback_to_default=False);paths={str(Path(sys.executable).resolve()),font};out=R/p['output_directory'];out.mkdir()
 for ext in ['png','svg','pdf']:
  metadata={'Date':None,'Creator':'Actual current24af own-worst native section'}if ext=='svg'else{'CreationDate':None,'ModDate':None,'Creator':'Actual current24af own-worst native section'}if ext=='pdf'else{'Software':'Actual current24af own-worst native section'}
  fig.savefig(out/('carrier-current24af-own-worst-section.'+ext),dpi=180,metadata=metadata)
 plt.close(fig)
 paths.update(str(Path(v.__file__).resolve())for n,v in list(sys.modules.items())if n.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(v,'__file__',None)and Path(v.__file__).is_file())
 require(paths<=set(p['runtime_sha256'])and all(sha(R/n)==v for n,v in p['runtime_sha256'].items()),'Post-render imports outside pinned runtime or drifted');require(all(sha(R/n)==v for n,v in p['files_sha256'].items()),'Source/data/closure drifted')
 write(out/'render-receipt.json',dict(status='actual_current24af_own_worst_section_and_explicit_projected_chords_rendered_no_admission',source_sha256=sha(__file__),section_ROOT_sha256=p['section_ROOT_sha256'],observation_ROOT_sha256=p['observation_ROOT_sha256'],checks=checks,actual_peak_xyz_mm=peak,normal_chords=chords,reciprocal_pairs=pairs,actual_IP_unresolved_rows=unresolved,selected_case=p['selected_case'],all_qualified_chords_retained=owner['exact_recomputed_chord_rows'],all_unresolved_rows_retained=owner['retained_null_rows'],normal_chords_projected_to_YZ=True,section_thickness_claimed=False,new_CAD_or_FEA=False,candidate_qualified=False,runtime_files_sha256={n:sha(n)for n in sorted(paths)},elapsed_seconds=time.monotonic()-began,outputs_sha256={q.name:sha(q)for q in out.iterdir()if q.is_file()}));signal.alarm(0)
if __name__=='__main__':
 mode,path,expected=sys.argv[1:]
 if mode=='preflight':p,*_=verify(Path(path),expected);print(json.dumps(dict(status='closed_records_and_hashes_only_no_authoring',armed=p['launch_ready'])))
 elif mode=='render':render(Path(path),expected)
 else:raise ValueError('Use preflight or render PLAN SHA')
