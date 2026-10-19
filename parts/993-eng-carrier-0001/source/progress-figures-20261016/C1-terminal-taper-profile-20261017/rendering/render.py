"""English closed-profile comparison only. No CAD import, section or ray calculation."""
import hashlib,importlib.util,json,os,resource,signal,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
EXTRACT=R/'work/carrier-C1-taper-section-preparation-001/extract.py'
EXTRACT_SHA='4a987fc275fb60039e8237241b27e1e2012c62df11f03eb17e723e1f6756ac4e'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def write(p,x):
 with Path(p).open('x')as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def closed_data(p):
 require(p['launch_ready']is True and p['root_GO_sha256']is not None and p['profile_ROOT_review_sha256']is not None,'NOT ARMED: closed ROOT profile and render GO required')
 require(sha(p['root_GO'])==p['root_GO_sha256']and sha(p['profile_ROOT_review'])==p['profile_ROOT_review_sha256'],'ROOT evidence differs')
 require(sha(EXTRACT)==EXTRACT_SHA and all(sha(R/n)==v for n,v in p['inputs_sha256'].items()),'Pinned profiles/source/evidence differ')
 s=importlib.util.spec_from_file_location('_closed_new_taper_profile',EXTRACT);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 base=Path(p['profile_preparation']);plan=json.loads((base/'plan.json').read_text());launch=json.loads((base/'launch-plan.json').read_text());sup=json.loads((base/'execution-001/execution-receipt.json').read_text());a=json.loads((base/'output-001/assessment.json').read_text());terminal=json.loads((base/'terminal-collection.json').read_text());data=json.loads(Path(p['data']).read_text())
 require(sup['actual_returncode']==0 and sup['direct_child_reaped']and sup['final_group_members']==[]and sup['cleanup_error']is None and not sup['timeout']and not sup['interrupted'],'Actual new-profile group not closed')
 require(sup['command']==launch['command']and sup['plan_sha256']==sha(base/'launch-plan.json')and sup['sources_before']==sup['sources_after']=={**launch['inputs_sha256'],**launch['source_sha256']},'Foreign new-profile supervision')
 require(Path(sup['command'][3])==EXTRACT and Path(sup['command'][-2])==base/'plan.json'and sup['command'][-1]==sha(base/'plan.json')and Path(sup['output_directory'])==Path(p['data']).parent,'Foreign producer/plan/output')
 require(sha(p['data'])==p['data_sha256']==a['raw_profile_data_sha256']==terminal['section_data_sha256']and terminal['actual_tool_returncode']==0 and terminal['supervision_sha256']==sha(base/'execution-001/execution-receipt.json')and terminal['assessment_sha256']==sha(base/'output-001/assessment.json'),'Foreign profile receipt/data')
 require(data['producer_sha256']==EXTRACT_SHA and data['plan_sha256']==sha(base/'plan.json')and data['source_sha256']==plan['files_sha256']==a['sources_before']==a['sources_after']and a['sources_unchanged'],'New profile context differs')
 old=m.closed_old(plan);m.closed_volume(plan);m.check_new(data,old)
 return data,m.OLD

def render(p):
 require(p['bounds']==dict(outer=120,inner=100,CPU=[90,100],threads=1,workers=0),'Render resources differ')
 require(os.getpriority(os.PRIO_PROCESS,0)==10 and all(os.environ.get(k)=='1'for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')),'nice10/BLAS1 child required')
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('100s draw-only bound')));signal.alarm(100);resource.setrlimit(resource.RLIMIT_CPU,(90,100))
 began=time.monotonic();data,old=closed_data(p);out=R/p['output_directory'];old.fresh(out);before={n:sha(R/n)for n in p['runtime_sha256']};require(before==p['runtime_sha256'],'Render runtime differs before import')
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib.font_manager import findfont,FontProperties
 matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':'#183347','axes.labelcolor':'#536D7D','svg.fonttype':'none','svg.hashsalt':'carrier-preserved-taper-profile-20261017','pdf.fonttype':42,'path.simplify':False})
 fig,axes=plt.subplots(1,2,figsize=(14.5,8),facecolor='#F8FAFC');fig.subplots_adjust(left=.065,right=.96,top=.75,bottom=.31,wspace=.2)
 fig.text(.06,.94,'993 TURBO · PRESERVED TAPER / ORIGINAL C1 · ACTUAL NATIVE SECTIONS',fontsize=11,weight='bold',color='#536D7D')
 fig.text(.06,.886,'What changed at the C1 fillet end?',fontsize=24,weight='bold')
 fig.text(.06,.834,'Same closed oblique plane through coarse peak 84037/IP1 · shared U/Z coordinates · baseline reference reused',fontsize=10.2)
 def lines(section):return [[old.project(q)for q in e['points_xyz_mm']]for e in section['edges']]
 baseline=data['cached_sections'][0];sections=[data['cached_sections'][1],data['taper_section']];checks=[]
 for ax,section,label,color in zip(axes,sections,['ORIGINAL C1 · closed profile','TERMINAL TAPER · preserved raw BREP'],['#087E8B','#30576E']):
  ax.set_facecolor('white');ax.grid(color='#DCE4E9',linewidth=.6);ax.set_axisbelow(True)
  ax.add_collection(LineCollection(lines(baseline),colors='#899AA5',linewidths=1.2,linestyles='dashed',alpha=.8,label='Original baseline reference'))
  ax.add_collection(LineCollection(lines(section),colors=color,linewidths=2.4,label='Actual native section'))
  ax.set(xlim=old.ZOOM[0],ylim=old.ZOOM[1],xlabel='Oblique horizontal U from the original foot (mm)',ylabel='Z − original foot Z (mm)');ax.set_aspect('equal',adjustable='box');ax.set_title(label,loc='left',weight='bold',pad=12);ax.legend(loc='lower left',fontsize=8)
  for spine in ax.spines.values():spine.set_color('#B8C8D2')
  checks.append(dict(role=section['role'],full_native_edges_submitted=section['edge_count'],sampled_positions_sha256=section['sampled_positions_sha256'],xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),aspect=ax.get_aspect(),display_crop_only=True))
 hits=data['closed_reference_context']['raw_hits'];ray=[old.project(q['point_mm'])for q in hits[:3]]
 axes[0].plot([q[0]for q in ray],[q[1]for q in ray],color='#D47732',lw=1.4,ls=':',marker='o',ms=4)
 fig.text(.06,.226,'Orange reference ray belongs ONLY to original C1.',fontsize=12,weight='bold',color='#A55A25')
 fig.text(.06,.184,'No taper normal ray or chord was computed. These profiles do not establish a wall thickness or strength result.',fontsize=10)
 fig.text(.06,.138,'Raw taper Build succeeded; the original post-Build law gate refused. Candidate remains unqualified; downstream gates stay separate.',fontsize=9.5)
 fig.text(.06,.083,'All native section curves retained; 0.001 mm drawing deflection, common display crop. No old CAD replay, CAD rebuild, remesh or FEA.',fontsize=9,color='#536D7D')
 font=findfont(FontProperties(family='DejaVu Sans'),fallback_to_default=False);paths={str(Path(sys.executable).resolve()),font};out.mkdir()
 for ext in ['png','svg','pdf']:
  metadata={'Date':None,'Creator':'Preserved taper native profiles'}if ext=='svg'else{'CreationDate':None,'ModDate':None,'Creator':'Preserved taper native profiles'}if ext=='pdf'else{'Software':'Preserved taper native profiles'}
  fig.savefig(out/('carrier-preserved-taper-profiles.'+ext),dpi=180,metadata=metadata)
 plt.close(fig)
 paths.update(str(Path(v.__file__).resolve())for n,v in list(sys.modules.items())if n.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(v,'__file__',None)and Path(v.__file__).is_file())
 require(paths<=set(p['runtime_sha256'])and all(sha(R/n)==v for n,v in p['runtime_sha256'].items()),'Post-render imports outside pinned runtime or drifted')
 require(all(sha(R/n)==v for n,v in p['inputs_sha256'].items()),'Source/data/closure drifted')
 write(out/'render-receipt.json',dict(status='actual_closed_profile_comparison_rendered_no_admission',source_sha256=sha(__file__),data_sha256=p['data_sha256'],profile_ROOT_review_sha256=p['profile_ROOT_review_sha256'],checks=checks,ray_plotted_on_original_C1_only=True,new_taper_ray_computed=False,global_thickness_claimed=False,candidate_qualified=False,original_law_RC1_preserved=True,FEA_executed=False,runtime_files_sha256={n:sha(n)for n in sorted(paths)},elapsed_seconds=time.monotonic()-began,outputs_sha256={q.name:sha(q)for q in out.iterdir()if q.is_file()}))
if __name__=='__main__':
 plan_path,expected=sys.argv[1:];require(sha(plan_path)==expected,'Render plan differs');render(json.loads(Path(plan_path).read_text()))
