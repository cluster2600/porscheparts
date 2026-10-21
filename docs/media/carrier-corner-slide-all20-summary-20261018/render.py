"""Two scalar heatmaps of all20 actual coarse cases; SOURCE only until reviewed GO."""
import hashlib,importlib.util,json,os,resource,signal,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def verify(p,native=False):
 assert p['schema']=='current24af-all20-scalar-heatmap-plan-1'and p['actual_workers']==0
 if native:assert p['launch_ready']is True and p['root_GO_sha256']is not None and sha(R/p['root_GO'])==p['root_GO_sha256'],'UNARMED: scalar graphic creation requires ROOT GO'
 assert all(sha(R/n)==v for n,v in p['files_sha256'].items())
 d=read(H/'data-closed.json');assert d['formal_ROOT_sha256']=='dc26accac6af16ba323b0e196555c681de95aeffff1d3fdb29c9fd12e145936c'
 spec=importlib.util.spec_from_file_location('_all20_closed_scalar_binding',H/'bind_ROOT.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate(d,read(R/d['formal_ROOT_path']))
 return d

def render(plan,expected,out):
 assert sha(plan)==expected;p=read(plan);d=verify(p,True);out=Path(out);assert not out.exists()and not any(q.is_symlink()for q in [out,*out.parents])
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in()).throw(TimeoutError('150s scalar drawing bound')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
 os.environ['MPLBACKEND']='Agg'
 import numpy as np
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 labels=['Gravity','Shock','Longitudinal','Lateral','Stock torque reference','Combined','Reverse torque combined','Roll','Pitch','Yaw']
 keys=d['loads'];assert len(keys)==len(labels)==10
 vm=np.array([[d['cases'][load+'-'+support]['actual_native_result']['integration_point_VM_max_MPa']for support in d['supports']]for load in keys])
 movement=np.array([[d['cases'][load+'-'+support]['actual_native_result']['displacement_max_mm']for support in d['supports']]for load in keys])
 fig,axes=plt.subplots(1,2,figsize=(12,8.4),facecolor='#F8FAFC');fig.subplots_adjust(left=.22,right=.95,top=.82,bottom=.18,wspace=.45)
 for ax,values,title,unit in zip(axes,[vm,movement],['Global integration-point von Mises','All-node displacement magnitude'],['MPa','mm']):
  image=ax.imshow(values,cmap='cividis',vmin=0,vmax=float(values.max()),aspect='auto',interpolation='nearest')
  ax.set_xticks([0,1],['Rigid','K1000 total / eye / axis']);ax.set_yticks(range(10),labels);ax.tick_params(axis='y', labelleft=(ax is axes[0]));ax.set_title(title,fontsize=11)
  for i in range(10):
   for j in range(2):ax.text(j,i,f'{values[i,j]:.3f}',ha='center',va='center',fontsize=10,color='white'if values[i,j]<.55*values.max()else'#142433')
  fig.colorbar(image,ax=ax,fraction=.05,pad=.04,label=unit)
 fig.suptitle('Current24af · all ten declared loads × two supports',fontsize=17,x=.55,y=.94)
 fig.text(.22,.875,'85 958 C3D10 · 160 005 nodes · original linear-elastic load/support definitions',fontsize=10)
 fig.text(.05,.105,'Largest stress: reverse torque combined / spring, 1 904.280 MPa. Largest movement: roll / spring, 83.228 mm.',fontsize=10)
 fig.text(.05,.067,'Separate VM and U scales; every case shown. Original whole results, energy audits and all global ties retained.',fontsize=9)
 fig.text(.05,.032,'Coarse linear results: stress convergence and strength qualification are not assigned.',fontsize=9)
 verify(p,True);out.mkdir()
 for ext in ['png','svg']:fig.savefig(out/('current24af-all20-summary.'+ext),dpi=180,metadata={'Date':None}if ext=='svg'else{})
 plt.close(fig);verify(p,True);signal.alarm(0)
 with(out/'receipt.json').open('x')as f:json.dump(dict(status='actual20_scalar_values_drawn_no_new_solver',data_sha256=sha(H/'data-closed.json'),all20_cases_shown=True,unrounded_values=d['cases'],global_stress=d['selected_worst_stress'],global_displacement=d['maximum_displacement'],qualification=False,outputs_sha256={q.name:sha(q)for q in out.iterdir()if q.is_file()}),f,indent=2);f.write('\n')
if __name__=='__main__':
 mode,plan,expected=sys.argv[1:4]
 if mode=='preflight':assert sha(plan)==expected;verify(read(plan));print('SOURCE_ONLY_all20_scalar_metadata_no_graphics')
 elif mode=='render':render(plan,expected,sys.argv[4])
