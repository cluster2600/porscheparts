#!/usr/bin/env python3
"""Private preserved-field diagnostic; no mesh edits or solver invocation."""
import argparse,hashlib,json,math,os,re,resource,time
from pathlib import Path
import numpy as np
from diagnose_and_merge_fv_cells import body
from analyze_flow_balance import field_values,patch_block
from analyze_d2_result import native_table


def poly_mesh(case):
    root=case/'constant/polyMesh'
    count,text=body(root/'points');points=np.fromstring(text.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
    if len(points)!=count:raise ValueError('Points cardinality')
    count,text=body(root/'faces');faces=np.full((count,4),-1,dtype=np.int64)
    for i,line in enumerate(text.splitlines()):
        m=re.fullmatch(r'\s*([34])\(([^()]*)\)\s*',line)
        if not m:raise ValueError('Only native triangular/quad faces accepted')
        faces[i,:int(m[1])]=list(map(int,m[2].split()))
    count,text=body(root/'owner');owner=np.fromstring(text,sep=' ',dtype=np.int64)
    count,text=body(root/'neighbour');neighbour=np.fromstring(text,sep=' ',dtype=np.int64);ni=len(neighbour)
    nc=max(owner.max(),neighbour.max())+1;Sf=np.empty((len(faces),3));Cf=np.empty_like(Sf)
    for lo in range(0,len(faces),100000):
        ids=faces[lo:lo+100000];a,b,c=points[ids[:,0]],points[ids[:,1]],points[ids[:,2]]
        area=.5*np.cross(b-a,c-a);centers=(a+b+c)/3;mask=ids[:,3]>=0
        if mask.any():
            d=points[ids[mask,3]];area[mask]+=.5*np.cross(c[mask]-a[mask],d-a[mask]);centers[mask]=(a[mask]+b[mask]+c[mask]+d)/4
        Sf[lo:lo+len(ids)]=area;Cf[lo:lo+len(ids)]=centers
    signed=np.einsum('ij,ij->i',Sf,Cf)/3
    volume=np.bincount(owner,weights=signed,minlength=nc)-np.bincount(neighbour,weights=signed[:ni],minlength=nc)
    if not np.isfinite(volume).all() or (volume<=0).any():raise ValueError('Independent positive volumes required')
    centers=np.column_stack([(np.bincount(owner,weights=signed*Cf[:,i]*.75,minlength=nc)-np.bincount(neighbour,weights=signed[:ni]*Cf[:ni,i]*.75,minlength=nc))/volume for i in range(3)])
    return points,faces,owner,neighbour,Sf,Cf,volume,centers


def completed_log(path):
    rows=[]
    for block in re.split(r'(?m)^Time = ',path.read_text())[1:]:
        clock=re.search(r'ExecutionTime = ([0-9.eE+-]+) s\s+ClockTime = ([0-9.eE+-]+)',block)
        if not clock:continue
        n=int(float(re.match(r'([0-9.eE+-]+)',block)[1]));solves=[]
        for field,initial,final,count in re.findall(r'Solving for (\w+), Initial residual = ([0-9.eE+-]+), Final residual = ([0-9.eE+-]+), No Iterations (\d+)',block):
            solves.append({'field':field,'initial':float(initial),'final':float(final),'iterations':int(count),'final_over_initial':float(final)/float(initial) if float(initial)>0 else None})
        rows.append({'iteration':n,'solves':solves,'execution_seconds':float(clock[1]),'wall_seconds_rounded':float(clock[2])})
    return rows


def diagnose(previous,completion,selections,output,cache):
    started=time.monotonic();used={}
    def record(path,label):used[label]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    case=completion;points,faces,owner,neighbour,Sf,Cf,v,centers=poly_mesh(case);nc=len(v);ni=len(neighbour);core=453496;nf=4542
    selection=np.load(selections,allow_pickle=False);oldv=selection['cellVolumes'];maxvdiff=float(abs(v[:core]-oldv).max())
    if nc!=680596 or len(oldv)!=core or not np.allclose(v[:core],oldv,rtol=1e-7,atol=0):raise ValueError('Frozen D2 geometry cardinality or independent volume mismatch')
    for name in ['points','faces','owner','neighbour','boundary']:record(case/'constant/polyMesh'/name,'extended/constant/polyMesh/'+name)
    record(selections,'common-selections-private.npz')
    state={};fields={}
    for step,root in [(960,previous/'extended'),(1000,case),(1020,case)]:
        fields[step]={}
        for name,components in [('p',1),('U',3),('k',1),('omega',1),('nut',1)]:
            path=root/str(step)/name;values=field_values(path.read_text(),'internalField',nc,components)
            if not np.isfinite(values).all():raise ValueError('Finite complete fields required')
            fields[step][name]=values;record(path,'extended/'+str(step)+'/'+name)
        text=(root/str(step)/'phi').read_text();phi=field_values(text,'internalField',ni,1)
        record(root/str(step)/'phi','extended/'+str(step)+'/phi')
        if not np.isfinite(phi).all():raise ValueError('Finite native internal flux required')
        planes=[]
        for j in range(51):
            z=-.0495-j*.0055
            ids=np.flatnonzero((abs(Cf[:ni,2]-z)<1e-10)&(Sf[:ni,2]<0)) if j<50 else None
            if j==50:
                flux=field_values(patch_block(text,'outlet'),'value',nf,1)
            else:
                if len(ids)!=nf:raise ValueError('Native axial plane must contain4542 faces')
                flux=phi[ids]
            planes.append({'plane':j,'z_m':z,'net_m3_s':float(flux.sum()),'gross_reverse_m3_s':float(-flux[flux<0].sum()),'reversed_faces':int((flux<0).sum()),'reverse_over_net':float(-flux[flux<0].sum()/abs(flux.sum()))})
        if step==1020:
            absflux=np.zeros(len(owner));absflux[:ni]=abs(phi)
            for patch in re.finditer(r'(\w+)\s*\{([^{}]*)\}',(case/'constant/polyMesh/boundary').read_text()):
                n=re.search(r'\bnFaces\s+(\d+)',patch[2]);start=re.search(r'\bstartFace\s+(\d+)',patch[2])
                if not n or not start:continue
                count=int(n[1]);s=int(start[1]);absflux[s:s+count]=abs(field_values(patch_block(text,patch[1]),'value',count,1))
            rate=(np.bincount(owner,weights=absflux,minlength=nc)+np.bincount(neighbour,weights=abs(phi),minlength=nc))/(2*v)
            worst=int(np.argmax(rate));dt=.5/float(rate.max())
            courant={'formula':'Co_cell=dt*sum(abs(phi_faces))/(2*cellVolume); native MRF flux uses solver convention','max_rate_s_inverse':float(rate.max()),'p99_rate_s_inverse':float(np.quantile(rate,.99)),'max_Co0p5_dt_s':dt,'worst_cell':worst,'worst_center_m':centers[worst].tolist(),'worst_volume_m3':float(v[worst]),'at_least_steps_per_assumed_revolution_at_6000rpm':math.ceil(.01/dt),'not_selected_transient_timestep_or_physical_validation':True}
        U=fields[step]['U'];speed=np.linalg.norm(U,axis=1);mach=speed/343
        state[str(step)]={'axial_flux_planes':planes,'volume_fraction_above_assumed_Mach0p3':float(v[mach>.3].sum()/v.sum()),'maximum_absolute_speed_m_s':float(speed.max()),'minimum_k':float(fields[step]['k'].min()),'minimum_omega':float(fields[step]['omega'].min()),'minimum_nut':float(fields[step]['nut'].min())}
    bands=[];energy_core_buffer={}
    masks={'core':np.arange(core),'buffer':np.arange(core,nc)}
    for old,new in [(960,1000),(1000,1020)]:
        dp=1.2*(fields[new]['p']-fields[old]['p']);du=np.linalg.norm(fields[new]['U']-fields[old]['U'],axis=1)
        metrics=lambda ids:{'cells':len(ids),'volume_m3':float(v[ids].sum()),'pressure_volume_RMS_Pa':float(np.sqrt(np.dot(v[ids],dp[ids]**2)/v[ids].sum())),'velocity_volume_RMS_m_s':float(np.sqrt(np.dot(v[ids],du[ids]**2)/v[ids].sum())),'pressure_change_squared_energy':float(np.dot(v[ids],dp[ids]**2))}
        energy_core_buffer[str(old)+'_to_'+str(new)]={label:metrics(ids) for label,ids in masks.items()}
        for j in range(50):
            ids=np.arange(core+j*nf,core+(j+1)*nf);row=metrics(ids);row.update({'from':old,'to':new,'layer':j,'center_z_m':-.0495-(j+.5)*.0055,'mean_p_old_Pa':float(np.dot(v[ids],fields[old]['p'][ids])*1.2/v[ids].sum()),'mean_p_new_Pa':float(np.dot(v[ids],fields[new]['p'][ids])*1.2/v[ids].sum())});bands.append(row)
    logs=completed_log(previous/'extended/log.foamRun')+completed_log(case/'log.foamRun')
    if [r['iteration'] for r in logs]!=list(range(961,1021)):raise ValueError('Exactly60 complete original40+new20 iteration blocks')
    psolves=[x for row in logs for x in row['solves'] if x['field']=='p'];firstp=[next(x['initial'] for x in row['solves'] if x['field']=='p') for row in logs]
    algebraic={'pressure_solves':len(psolves),'pressure_iteration_count_total':sum(x['iterations'] for x in psolves),'maximum_pressure_final_over_initial':max(x['final_over_initial'] for x in psolves),'pressure_relative_target':.01,'first_p_initial_by_iteration':[{'iteration':r['iteration'],'residual':p} for r,p in zip(logs,firstp)],'pressure_initial_961_to1020_ratio':firstp[-1]/firstp[0],'pressure_initial_1001_to1020_ratio':firstp[-1]/firstp[40],'matrix_residual_is_not_physical_pressure_error':True}
    Q=state['1020']['axial_flux_planes'][0]['net_m3_s'];V=float(v[core:].sum());nominal=V/Q
    extrema=[]
    for stage,root in [('original',previous/'extended'),('continuation',case)]:
        record(root/'log.foamRun',stage+'/log.foamRun')
        file=next((root/'postProcessing/commonPressureBandMean').glob('*/*.dat'));table=native_table(file);table=table[table[:,0]>=961]
        values=table[:,1]*1.2
        for i in range(1,len(values)-1):
            if (values[i]-values[i-1])*(values[i+1]-values[i])<0:extrema.append({'iteration':int(table[i,0]),'pressure_Pa':float(values[i]),'stage':stage})
        record(file,stage+'/commonPressureBandMean')
    uniform_buffer={'initial_buffer_pressure_Pa_min':float(fields[960]['p'][core:].min()*1.2),'initial_buffer_pressure_Pa_max':float(fields[960]['p'][core:].max()*1.2),'initial_each_column_U_repeated_across50_layers':bool(np.array_equal(fields[960]['U'][core:].reshape(50,nf,3),np.broadcast_to(fields[960]['U'][core:core+nf],(50,nf,3)))),'initial_all51_flux_planes_identical_to_write_precision':max(abs(x['net_m3_s']-state['960']['axial_flux_planes'][0]['net_m3_s']) for x in state['960']['axial_flux_planes'])<1e-10,'not_momentum_equilibrium_initializer':True}
    cache.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(cache,cellVolumes=v,cellCenters=centers,courantRate=rate)
    result={'status':'preserved_D2_fields_and_logs_diagnosed_no_new_solver','analysis_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'dependencies_sha256':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ['diagnose_and_merge_fv_cells.py','analyze_flow_balance.py','analyze_d2_result.py']},'source_identity':used,'new_solver_launched':False,'geometry_or_criteria_changed':False,'native_geometry_volume_check':{'positive_cells':nc,'maximum_core_volume_difference_from_prior_independent_values_m3':maxvdiff},'initialization':uniform_buffer,'snapshots':state,'core_buffer_change':energy_core_buffer,'buffer_layer_changes':bands,'linear_solver_diagnostic':algebraic,'native_iteration_pressure_extrema':extrema,'physical_time_proxies':{'buffer_volume_m3':V,'net_common_flow1020_m3_s':Q,'nominal_throughflow_volume_over_Q_s':nominal,'assumed_rotor_revolution_s':.01,'throughflow_proxy_rotor_revolutions':nominal/.01,'recirculation_residence_time_not_bounded_by_volume_over_Q':True,'SIMPLE_iterations_are_not_physical_time':True},'courant_cost_screen':courant,'causal_limits':{'initialization_causal_contribution_not_isolated':True,'physical_unsteadiness_not_demonstrated':True,'SIMPLE_numeric_oscillation_and_physical_transient_cannot_be_identified_from_this_history':True,'finite_single_phase_MRF_incompressible_model_does_not_qualify_installed_airflow':True},'private_geometry_cache_identity':{'bytes':cache.stat().st_size,'sha256':hashlib.sha256(cache.read_bytes()).hexdigest()},'wall_seconds':time.monotonic()-started,'peak_RSS_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'physical_validation_established':False}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','initialization','linear_solver_diagnostic','physical_time_proxies','courant_cost_screen','wall_seconds']}));return result


if __name__=='__main__':
    os.nice(15);cli=argparse.ArgumentParser(description=__doc__)
    for name in ['previous','completion','selections','output','private_cache']:cli.add_argument(name,type=Path)
    a=cli.parse_args();diagnose(a.previous,a.completion,a.selections,a.output,a.private_cache)
