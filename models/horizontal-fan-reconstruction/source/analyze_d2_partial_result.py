#!/usr/bin/env python3
"""Audit stopped D2 branch, actual completed windows and private MPI checkpoint."""
import argparse,json,re
from pathlib import Path
import numpy as np
from append_outlet_prisms import body
from analyze_flow_balance import field_values,patch_block
from analyze_d2_result import sha,stats,symmetric,difference,native_table
from measurement_window import require_measurement_window


def analyze(root,partial,protocol_file,output):
    protocol=json.loads(protocol_file.read_text());selected=np.load(root/'cases/common-selections-private.npz',allow_pickle=False);v=selected['cellVolumes'];nc=len(v);records={};used={};fields={};tables={}
    def checked_file(path):
        used[str(path.relative_to(root))]=sha(path);return path.read_text()
    for label in ['current','extended']:
        case=root/'cases'/label;log=checked_file(case/'log.foamRun');blocks=re.split(r'(?m)^Time = ',log)[1:];completed=[];residuals={}
        for block in blocks:
            iteration=int(float(re.match(r'([\d.eE+-]+)',block)[1]));row={}
            for field,value in re.findall(r'Solving for (\w+), Initial residual = ([\d.eE+-]+)',block):row[field]=max(row.get(field,0),float(value))
            if set(row)>={'p','Ux','Uy','Uz','k','omega'} and 'ExecutionTime =' in block:completed.append(iteration);residuals[iteration]=row
        if completed!=list(range(961,961+len(completed))):raise ValueError('Contiguous actually complete solver iterations required')
        report={'started_iterations':len(blocks),'complete_solver_iterations':len(completed),'last_complete_iteration':completed[-1],'End_present':'\nEnd\n' in log,'required_final_iteration':1020,'target_reached':completed[-1]==1020,'windows':[]}
        data={}
        for name in ['commonOutletFlux','commonPressureBandMean','rotorForces']:
            files=list((case/'postProcessing'/name).glob('*/*.dat'))
            if len(files)!=1:raise ValueError('Exactly one native measurement table required')
            checked_file(files[0]);data[name]=native_table(files[0])
            if list(data[name][1:,0])!=list(map(float,completed)) or data[name][0,0]!=960:raise ValueError('Actual complete log/table correspondence required')
        tables[label]=data;report['native_table_samples_including960']={k:len(a) for k,a in data.items()}
        for lo,hi in protocol['execution']['windows']:
            if hi>completed[-1]:report['windows'].append({'range':[lo,hi],'status':'missing_required_window','samples':sum(lo<=t<=hi for t in completed)});continue
            q=data['commonOutletFlux'];pr=data['commonPressureBandMean'];t=data['rotorForces'];q=q[(q[:,0]>=lo)&(q[:,0]<=hi)];pr=pr[(pr[:,0]>=lo)&(pr[:,0]<=hi)];t=t[(t[:,0]>=lo)&(t[:,0]<=hi)];require_measurement_window(list(range(lo,hi+1)),q,pr,t,20);torque=t[:,9]+t[:,12]
            maxima={name:max(residuals[it][name] for it in range(lo,hi+1)) for name in ['p','Ux','Uy','Uz','k','omega']}
            report['windows'].append({'range':[lo,hi],'status':'complete_descriptive_window','samples':20,'Q_m3_s':stats(q[:,1]),'pressure_Pa':stats(pr[:,1]*1.2),'torque_Nm':stats(torque),'maximum_initial_residuals':maxima,'window_is_not_the_missing_target_window':hi!=1020})
        records[label]=report
    # Gather existing MPI scalar/vector cell fields exactly by original global IDs.
    pp_manifest=json.loads((partial/'partial-checkpoint-manifest.json').read_text());expected=680596;coverage=np.zeros(expected,dtype=np.int64);p=np.empty(expected);u=np.empty((expected,3));common_faces=np.load(root/'cases/extended/private-maps.npz',allow_pickle=False)['old_to_new_faces'][selected['commonOutletFaceIds']];lookup={int(face):index for index,face in enumerate(common_faces)};common_phi=np.empty(len(common_faces));face_coverage=np.zeros(len(common_faces),dtype=np.int64);far_phi=[]
    partial_used={};finite_counts={name:0 for name in ['p','U','k','omega','nut']}
    def native(path):
        key=str(path.relative_to(partial));record=pp_manifest['members'][key]
        if path.stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:raise ValueError('Partial checkpoint identity '+key)
        partial_used[key]=record;return path.read_text()
    for rank in range(4):
        case=partial/('processor'+str(rank));addrpath=case/'constant/polyMesh/cellProcAddressing';native(addrpath);ids=np.fromstring(body(addrpath)[1],sep=' ',dtype=np.int64);coverage[ids]+=1
        p[ids]=field_values(native(case/'1000/p'),'internalField',len(ids),1);u[ids]=field_values(native(case/'1000/U'),'internalField',len(ids),3)
        finite_counts['p']+=len(ids);finite_counts['U']+=len(ids)
        for scalar in ['k','omega','nut']:
            values=field_values(native(case/'1000'/scalar),'internalField',len(ids),1)
            if not np.isfinite(values).all() or (values<0).any():raise ValueError('Finite positive native turbulence checkpoint required')
            finite_counts[scalar]+=len(values)
        facepath=case/'constant/polyMesh/faceProcAddressing';native(facepath);addr=np.fromstring(body(facepath)[1],sep=' ',dtype=np.int64);phi_text=native(case/'1000/phi');ni=int(re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)',phi_text)[1]);phi=field_values(phi_text,'internalField',ni,1)
        for local,a in enumerate(addr[:ni]):
            global_id=abs(int(a))-1
            if global_id in lookup:
                i=lookup[global_id];common_phi[i]=phi[local]*np.sign(a);face_coverage[i]+=1
        bt=native(case/'constant/polyMesh/boundary');ot=patch_block(bt,'outlet');count=int(re.search(r'\bnFaces\s+(\d+)',ot)[1]);far_phi.extend(field_values(patch_block(phi_text,'outlet'),'value',count,1).tolist())
    if not (coverage==1).all() or not (face_coverage==1).all() or len(far_phi)!=4542 or not np.isfinite(p).all() or not np.isfinite(u).all():raise ValueError('Complete unique MPI1000 coverage required')
    if abs(common_phi.sum()-tables['extended']['commonOutletFlux'][-1,1])>1e-8:raise ValueError('Native phi/common functionObject sum mismatch')
    fields['extended']={'p':p[:nc],'U':u[:nc]}
    def serial(iteration):
        case=root/'cases/current';return {name:field_values(checked_file(case/str(iteration)/name),'internalField',nc,components) for name,components in [('p',1),('U',3)]}
    fields['current']=serial(1000);final_current=serial(1020);stationary=difference(v,fields['current'],final_current)
    A=records['current']['windows'][1];B=records['extended']['windows'][1]
    matched={'range':[981,1000],'descriptive_only_not_stationary_domain_comparison':True,'current_mean_common_Q_m3_s':A['Q_m3_s']['mean'],'extended_mean_common_Q_m3_s':B['Q_m3_s']['mean'],'symmetric_relative_Q_difference':symmetric(A['Q_m3_s']['mean'],B['Q_m3_s']['mean']),'current_mean_torque_Nm':A['torque_Nm']['mean'],'extended_mean_torque_Nm':B['torque_Nm']['mean'],'symmetric_relative_torque_difference':symmetric(A['torque_Nm']['mean'],B['torque_Nm']['mean']),'current_mean_common_pressure_Pa':A['pressure_Pa']['mean'],'extended_mean_common_pressure_Pa':B['pressure_Pa']['mean'],'signed_pressure_difference_Pa':B['pressure_Pa']['mean']-A['pressure_Pa']['mean']}
    fv=lambda flux:{'net_m3_s':float(flux.sum()),'gross_reverse_m3_s':float(-flux[flux<0].sum()),'gross_forward_m3_s':float(flux[flux>0].sum()),'reverse_over_net':float(-flux[flux<0].sum()/abs(flux.sum())),'reversed_faces':int((flux<0).sum())}
    current_phi=field_values(patch_block(checked_file(root/'cases/current/1000/phi'),'outlet'),'value',4542,1);flux={'iteration':1000,'current_common_plane':fv(current_phi),'extended_common_plane':fv(common_phi),'extended_far_outlet':fv(np.array(far_phi))}
    s=protocol['additional_stationarity_screen'];first,last=records['current']['windows'][1:];deltaQ=symmetric(first['Q_m3_s']['mean'],last['Q_m3_s']['mean']);deltaT=symmetric(first['torque_Nm']['mean'],last['torque_Nm']['mean']);deltaP=abs(first['pressure_Pa']['mean']-last['pressure_Pa']['mean']);stationarity_checks={'common_flow_CV':last['Q_m3_s']['CV']<=s['last_window_common_flow_CV_max'],'common_pressure_std':last['pressure_Pa']['std']<=s['last_window_common_pressure_std_Pa_max'],'between_windows_common_flow':deltaQ<=s['between_last_two_window_mean_common_flow_relative_max'],'between_windows_torque':deltaT<=s['between_last_two_window_mean_torque_relative_max'],'between_windows_pressure':deltaP<=s['between_last_two_window_mean_pressure_difference_Pa_max'],'core_pressure_checkpoint_RMS':stationary['pressure_volume_RMS_Pa']<=s['checkpoint1000_to1020_core_pressure_volume_RMS_Pa_max'],'core_velocity_checkpoint_RMS':stationary['velocity_volume_RMS_m_s']<=s['checkpoint1000_to1020_core_velocity_volume_RMS_m_s_max']}
    result={'status':'incomplete_pair_inconclusive_domain_comparison','current_completed60':True,'extended_completed60':False,'both_cases_stationary_admitted':False,'domain_comparison_gate_evaluated':False,'reports':records,'matched_complete981_1000_windows':matched,'current_original_numerical_checks':json.loads((root/'cases/current/flow-summary.json').read_text())['criteria_checks'],'current_additional_stationarity_checks':stationarity_checks,'current_between_last_windows':{'relative_Q':deltaQ,'relative_torque':deltaT,'abs_pressure_Pa':deltaP},'current_checkpoint1000_to1020':stationary,'paired_common_core1000':difference(v,fields['current'],fields['extended']),'paired_fixed_zones1000':{name:difference(v[selected[name]],{k:a[selected[name]] for k,a in fields['current'].items()},{k:a[selected[name]] for k,a in fields['extended'].items()}) for name in ['commonPressureBand','commonOutletOwners','commonTipWake']},'actual_saved_checkpoint1000_reflux':flux,'MPI1000_coverage':{'global_cells':expected,'each_cell_exactly_once':True,'finite_completed1000_field_counts':finite_counts,'common_faces':len(common_faces),'each_common_face_exactly_once':True,'common_phi_matches_native_functionObject':True},'source_sha256':used,'partial_native_members_used':partial_used,'partial_checkpoint_manifest_sha256':sha(partial/'partial-checkpoint-manifest.json'),'analysis_script_sha256':sha(Path(__file__)),'dependency_sha256':{name:sha(Path(__file__).parent/name) for name in ['analyze_d2_result.py','append_outlet_prisms.py','analyze_flow_balance.py','measurement_window.py']},'protocol_sha256':sha(protocol_file),'domain_independence_established':False,'physical_validation_established':False,'airflow_improvement_proven':False,'local_fields_qualified':False,'no_new_solver_or_OpenFOAM_reconstruction_run':True,'checkpoint1000_is_not_missing1020_or_a_continuation':True}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'matched':matched,'reflux':flux,'current_stationarity':stationarity_checks}));return result


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for name in ['root','partial','protocol','output']:a.add_argument(name,type=Path)
    x=a.parse_args();analyze(x.root,x.partial,x.protocol,x.output)
