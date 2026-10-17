"""Plot the closed seven-edge law observation snapshot; no CAD import or native operation."""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from fractions import Fraction as Q
import resource
import signal
import sys
import time

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    d=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):d.update(block)
    return d.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    with Path(path).open('x')as f:json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n')
def fresh(path):
    path=Path(path)
    require(not path.exists()and not any(p.is_symlink()for p in [path,*path.parents]),'Fresh nonsymlink output required')
    return path

IDS=[431,293,292,291,290,289,161]
def select_data(review,terminal):
    stock=terminal['variants']['stock-rebuilt'];patched=terminal['variants']['patched']
    require(review['owner_terminal_sha256']=='7a0d05364c8b5786374f58366c1031498fc977a5b07f9e96ca379ef67a0206c0','Foreign owner terminal')
    require(review['actual_returncodes']==[1,0]and review['patched_whole_final7_native_laws_fresh_abscissae_and_exact_function_proof_recomputed_equal']is True and review['all_geometry_mass_interface_surface_STEP_FEA_gates_PENDING']is True,'Actual ROOT scope differs')
    require(terminal['status']=='closed_actual_stock_RC1_patched_RC0_complete_law_only_geometry_PENDING'and terminal['candidate_qualified']is False and terminal['all_geometry_gates_PENDING']is True,'Closed law-only terminal required')
    require(stock['actual_tool_returncode']==stock['actual_child_returncode']==1 and stock['actual_native_build_status']is None and stock['actual_failure']['type']=='Standard_Failure'and stock['actual_failure']['message']=='NCollection_Sequence::First','Original stock failure differs')
    require(not any(k in stock for k in ['whole_final_native_laws','whole_post_Build_physical_source_edges','raw_BREP_sha256']),'Stock Build must not acquire invented final laws or geometry')
    require(patched['actual_tool_returncode']==patched['actual_child_returncode']==0 and patched['actual_failure']is None,'Patched native observation did not close RC0')
    status=patched['actual_native_build_status'];require(status['IsDone']is True and status['HasResult']is False and status['NbFaultyContours']==status['NbFaultyVertices']==0,'Actual native status differs')
    require(patched['raw_BREP_sha256']==review['patched_raw_BREP_sha256']=='07b354e3716b4e856010e271f7a36aa7f6fe05a4ee4ce36eb0959af84e92409e','Preserved raw BREP authority differs')
    require(stock['pre_Build_physical_source_edges']==patched['pre_Build_physical_source_edges']and stock['whole_constructed_function_proof']==patched['whole_constructed_function_proof'],'Controls do not share the whole requested physical function')
    return dict(schema='closed-seven-edge-law-figure-data-1',stock=dict(actual_returncode=1,failure_type=stock['actual_failure']['type'],failure_message=stock['actual_failure']['message'],post_Build_laws=None,post_Build_physical_source_edges=None),patched=dict(actual_returncode=0,native_build_status=status,raw_BREP_sha256=patched['raw_BREP_sha256'],raw_BREP_bytes=patched['raw_BREP_bytes'],whole_final_native_laws=patched['whole_final_native_laws'],whole_post_Build_physical_source_edges=patched['whole_post_Build_physical_source_edges'],whole_final_exact_function_proof=patched['whole_final_exact_function_proof']),pre_Build_physical_source_edges=patched['pre_Build_physical_source_edges'],shared_requested_complete_native_function_proof=patched['whole_constructed_function_proof'],exact_proof_separate_from_sampled_visualization=True,candidate_qualified=False,all_geometry_gates='PENDING')

def validate_data(data,contract):
    require(data['schema']=='closed-seven-edge-law-figure-data-1'and data['candidate_qualified']is False and data['all_geometry_gates']=='PENDING','Law-only data scope differs')
    require(data['stock']['post_Build_laws']is None and data['stock']['post_Build_physical_source_edges']is None,'No stock post-Build curve may be invented')
    require(data['stock']['actual_returncode']==1 and data['patched']['actual_returncode']==0,'Control returncodes differ')
    physical=data['patched']['whole_post_Build_physical_source_edges'];rows=data['patched']['whole_final_native_laws']
    require([r['edge_index_zero_based']for r in rows]==IDS,'Complete ordered native law records required')
    proof=contract.validate_native(rows,physical);require(proof==data['patched']['whole_final_exact_function_proof'],'Full exact retained native proof differs')
    requested=contract.requested_spec(data['pre_Build_physical_source_edges'])
    shared=data['shared_requested_complete_native_function_proof'];constructed=[r['native_full_record']for r in shared['edges']]
    require(contract.validate_native(constructed,data['pre_Build_physical_source_edges'])==shared,'Shared whole requested native function proof differs')
    first=constructed[0]
    require(requested==dict(degree=first['native_degree'],poles=first['native_poles'],knots=first['native_knots'],multiplicities=first['native_multiplicities'],periodic=first['native_periodic'],rational=first['native_rational']),'Actual constructed requested coefficients differ')
    require(data['exact_proof_separate_from_sampled_visualization']is True and proof['whole_physical_contour_covered']is True and proof['geometry_qualified']is False,'Exact proof/visualization scopes differ')
    return requested,proof

def visual_samples(proof,samples_per_span):
    """Display-only samples of the retained exact restrictions; never an acceptance test."""
    require(type(samples_per_span)is int and samples_per_span==81,'Reviewed display-only sample count differs')
    target=list(map(Q,proof['edges'][0]['physical_interval_Q']));x=[];native=[];requested=[]
    for edge in proof['edges']:
        for piece in edge['all_actual_knot_spans']:
            lo,hi=map(Q,piece['interval_Q']);coeff=list(map(Q,piece['normalized_power_coefficients_Q']))
            for j in range(samples_per_span):
                t=Q(j,samples_per_span-1);s=lo+(hi-lo)*t;v=Q(0)
                for c in reversed(coeff):v=v*t+c
                u=(s-target[0])/(target[1]-target[0]);w=3*u*u-2*u*u*u if s<=target[1]else Q(1)
                x.append(float(s));native.append(float(v));requested.append(float(w))
    return x,native,requested

def literal_helpers(root,plan):
    source=Path(__file__).read_text();old=(root/plan['pure_helpers_source']).read_text();current=ast.parse(source);prior=ast.parse(old)
    for name in plan['literal_helper_names']:
        a=next(n for n in current.body if isinstance(n,ast.FunctionDef)and n.name==name);b=next(n for n in prior.body if isinstance(n,ast.FunctionDef)and n.name==name)
        require(ast.get_source_segment(source,a)==ast.get_source_segment(old,b),'Existing pure helper changed: '+name)

def verify(plan_path,expected,rendering=False):
    require(sha(plan_path)==expected,'Plan hash differs');p=read(plan_path);root=Path(p['source_root'])
    require(p['schema']=='closed-seven-edge-law-figure-plan-1'and p['workers']==0 and p['samples_per_native_knot_span']==81 and p['native_CAD_mesh_or_FEA_calls']==0 and p['bounds']==dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0),'Figure scope/bounds differ')
    if rendering:require(p['launch_ready']is True and p['root_GO']is not None and sha(root/p['root_GO'])==p['root_GO_sha256'],'NON-ARMED: ROOT render GO required')
    require(all(sha(root/n)==h for n,h in p['files_sha256'].items()),'Input/source/runtime hash differs')
    require(p['files_sha256'][str(Path(__file__).relative_to(root))]==sha(__file__)and all(p['files_sha256'].get(n)==h for n,h in p['runtime_sha256'].items()),'Source/runtime bindings differ')
    literal_helpers(root,p);context=p['closed_context'];review=read(root/context['root_review']);terminal=read(root/context['owner_terminal'])
    require(p['files_sha256'][context['root_review']]=='68c5afa2cb79f88839a4e026bb7523f8e7732ce7ac781395a12a92892bd15cd6'and p['files_sha256'][context['owner_terminal']]==review['owner_terminal_sha256'],'Actual ROOT/owner terminal hash join differs')
    data=read(root/p['data']);require(data==select_data(review,terminal),'Whole selected closed data differs')
    spec=importlib.util.spec_from_file_location('_closed_exact_full_contour_contract',root/p['contract_source']);contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    requested,proof=validate_data(data,contract)
    require(not any(n=='OCP'or n.startswith('OCP.')or n=='build123d'or n.startswith('build123d.')for n in sys.modules),'Native CAD was imported')
    require(sha(plan_path)==expected,'Plan changed during preflight');return p,data,requested,proof

def render(plan_path,expected,output):
    started=time.monotonic();p,data,requested,proof=verify(plan_path,expected,True);root=Path(p['source_root']);require(Path(output)==root/p['output_directory'],'Declared plot destination differs');output=fresh(output)
    os.environ['MPLBACKEND']='Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_pdf,matplotlib.backends.backend_svg
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,'text.color':'#183347','axes.labelcolor':'#536D7D','svg.fonttype':'none','svg.hashsalt':'carrier-seven-edge-radius-law-001','pdf.fonttype':42,'path.simplify':False})
    x,native,wanted=visual_samples(proof,p['samples_per_native_knot_span']);b=requested['knots'][1];last=requested['knots'][-1]
    fig=plt.figure(figsize=(14.5,10.5),facecolor='white')
    fig.text(.06,.956,'993 TURBO · COMPLETE SEVEN-EDGE RADIUS LAW',fontsize=11,color='#536D7D',weight='bold')
    fig.text(.06,.917,'The requested law survives the patched native Build',fontsize=22,weight='bold')
    fig.text(.06,.885,'Same original contour and requested whole function · one SetRadius(function), one Build per isolated control',fontsize=10)
    fig.text(.06,.850,'REBUILT STOCK  /  RC1',fontsize=12,weight='bold',color='#A35038')
    fig.text(.06,.823,'Standard_Failure: NCollection_Sequence::First',fontsize=10)
    fig.text(.06,.798,'Build did not return. No post-Build curve or raw Solid is fabricated.',fontsize=9.5,color='#536D7D')
    fig.text(.55,.850,'PATCHED TOOLKIT  /  RC0  /  EXACT LAW PASS',fontsize=12,weight='bold',color='#087E8B')
    fig.text(.55,.823,'IsDone = true · HasResult = false (retained) · 0 faulty contours / vertices',fontsize=9.5)
    fig.text(.55,.798,'At the law observation, geometry gates were pending; one valid raw Solid was saved.',fontsize=9.5,color='#536D7D')
    ax=fig.add_axes([.07,.473,.60,.267]);detail=fig.add_axes([.75,.473,.20,.267])
    ax.plot(x,wanted,color='#B8C7CF',linewidth=5,label='Requested whole function')
    ax.plot(x,native,color='#087E8B',linewidth=1.8,linestyle='--',label='Retained native coefficients')
    for i,e in enumerate(proof['edges']):
        lo,hi=map(lambda q:float(Q(q)),e['physical_interval_Q']);ax.axvspan(lo,hi,color='#087E8B'if i%2==0 else'#536D7D',alpha=.045)
        ax.axvline(lo,color='#CBD5DB',linewidth=.7);ax.text((lo+hi)/2,1.075,str(e['edge_index_zero_based']),ha='center',fontsize=8)
    ax.axvline(last,color='#CBD5DB',linewidth=.7);ax.set(xlim=(0,last),ylim=(-.055,1.14),xlabel='Native contour abscissa s (mm)',ylabel='Radius R (mm)',title='All seven physical source edges');ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.legend(loc='lower right',fontsize=8,frameon=False)
    detail.plot(x,wanted,color='#B8C7CF',linewidth=5);detail.plot(x,native,color='#087E8B',linewidth=1.8,linestyle='--');detail.set(xlim=(0,b),ylim=(-.055,1.055),xlabel='s on edge 431 (mm)',title='Terminal smoothstep');detail.spines[['top','right']].set_visible(False);detail.grid(alpha=.15)
    fig.text(.075,.423,'R(s) = 3(s/b)² − 2(s/b)³ for 0 ≤ s ≤ b; R(s) = 1 for b ≤ s ≤ L.',fontsize=11,weight='bold')
    fig.text(.075,.399,f'b = {b:.15g} mm; L = {last:.15g} mm. Curves are sampled visuals; acceptance uses full exact Fraction restrictions.',fontsize=9.3,color='#536D7D')
    table_ax=fig.add_axes([.07,.197,.88,.177]);table_ax.axis('off');rows=[]
    for e in proof['edges']:
        lo,hi=map(lambda q:float(Q(q)),e['physical_interval_Q']);rows.append([str(e['edge_index_zero_based']),f'{lo:.6f} → {hi:.6f}','[0, 0, 3, −2]'if e['restriction']=='cubic_smoothstep'else'[1, 0, 0, 0]','Exact smoothstep'if e['restriction']=='cubic_smoothstep'else'Exact constant R1'])
    table=table_ax.table(cellText=rows,colLabels=['Source edge','Complete physical interval (mm)','Local normalized power coefficients','Full interval restriction'],cellLoc='center',loc='center',colWidths=[.12,.30,.32,.26]);table.auto_set_font_size(False);table.set_fontsize(8.6);table.scale(1,1.35)
    for(pos,cell)in table.get_celld().items():
        cell.set_edgecolor('#DCE4E9')
        if pos[0]==0:cell.set_facecolor('#E8EFF3');cell.set_text_props(weight='bold')
    fig.text(.075,.154,'Retained native cubic: poles [0, 0, 1, 1, 1, 1]; knots [0, b, L]; multiplicities [4, 2, 4].',fontsize=9.5)
    fig.text(.075,.129,'All seven complete native records and exact rational physical intervals are retained in law-data.json; table intervals are rounded for display.',fontsize=9,color='#536D7D')
    fig.text(.075,.091,'Exact proof: law_contract.py a6c1443c… + original Fraction restriction e47b4d4c… · closed ROOT 68c5afa2… / owner 7a0d0536…',fontsize=8.8,color='#536D7D')
    fig.text(.075,.067,'Historical law observation only. Later geometry checks are separate; none is transferred into the law proof.',fontsize=9,color='#A35038')
    fig.text(.075,.043,'Raw BREP 07b354e3716b… remains unqualified. This scalar figure contains no CAD rendering or new native computation.',fontsize=9,color='#536D7D')
    verify(plan_path,expected,True);fresh(output).mkdir()
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Closed seven-edge native radius law'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Closed seven-edge native radius law'}if ext=='pdf'else{'Software':'Closed seven-edge native radius law'})
        fig.savefig(output/('carrier-seven-edge-radius-law.'+ext),dpi=180,metadata=metadata)
    plt.close(fig);verify(plan_path,expected,True)
    loaded={str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.split('.')[0]in ['numpy','matplotlib','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file()}
    require(loaded<=set(p['runtime_sha256']),'Imported plot runtime outside the attested runtime')
    write(output/'render-receipt.json',dict(schema='closed-seven-edge-law-render-1',status='actual_closed_law_data_scalar_plot_no_native_or_qualification',plan_sha256=expected,source_sha256=sha(__file__),files_sha256=p['files_sha256'],runtime_sha256=p['runtime_sha256'],runtime_imported_files=sorted(loaded),whole_exact_proof_recomputed_equal=True,full_fraction_proof=proof,requested_native_coefficients=requested,whole_physical_edges=IDS,visual_samples_per_native_knot_span=81,sampled_curve_is_not_the_proof=True,stock_post_Build_curve=None,native_CAD_mesh_or_FEA_calls=0,candidate_qualified=False,downstream_geometry_gates='PENDING',downstream_geometry_gate_status_scope='historical_at_the_law_observation',wall_seconds=time.monotonic()-started,CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,cwd=os.getcwd(),outputs_sha256={q.name:sha(q)for q in sorted(output.iterdir())}))

if __name__=='__main__':
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    mode,plan,expected=sys.argv[1:4]
    if mode=='preflight':
        p,data,_,_=verify(plan,expected);print(json.dumps(dict(status='stdlib_only_closed_law_bindings_no_plot',launch_ready=p['launch_ready'],physical_edges=IDS,pins=len(p['files_sha256']))))
    elif mode=='render':
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s scalar-law figure budget')));signal.setitimer(signal.ITIMER_REAL,150);resource.setrlimit(resource.RLIMIT_CPU,(140,141));os.chdir('/');render(plan,expected,sys.argv[4])
    else:raise SystemExit('usage: figure.py preflight PLAN SHA | render ARMED_PLAN SHA FRESH_OUTPUT')
