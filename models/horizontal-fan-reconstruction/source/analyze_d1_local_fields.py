#!/usr/bin/env python3
"""Read preserved fields/logs only; local changes are not algebraic residuals."""
import argparse, hashlib, json, re
from pathlib import Path
import numpy as np
from diagnose_and_merge_fv_cells import read
from analyze_flow_balance import field_values, patch_block
NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def analyze(old_inputs, new_inputs, logs, output):
    old_index = json.loads((old_inputs/'input-manifest.json').read_text())['members']
    new_index = json.loads((new_inputs/'input-manifest.json').read_text())
    case = old_inputs/'cfd-V2-fine-pressure015-900'
    used = {}
    for path in [*(case/'constant/polyMesh').iterdir(), case/'900/p', case/'900/U']:
        if not path.is_file():
            continue
        key = str(path.relative_to(old_inputs)); record = old_index[key]
        if path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
            raise ValueError('Preserved mesh/900 identity differs')
        used['historical/'+key] = record
    for name in ['p', 'U', 'phi']:
        p = new_inputs/'960'/name
        key = 'D1-runtime-symlink-repair/cases/control/960/'+name
        record = new_index['members'][key]
        if p.stat().st_size != record['bytes'] or sha(p) != record['sha256']:
            raise ValueError('Preserved960 identity differs')
        used['D1/'+key] = record
    log_index = json.loads((logs/'input-manifest.json').read_text())['files']
    points, faces, owner, neighbour, patches = read(case)
    ni = len(neighbour); nc = int(max(owner.max(), neighbour.max()))+1
    tri = points[faces]; fc = tri.mean(axis=1)
    sf = .5*np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    area = np.linalg.norm(sf, axis=1)
    centers = np.zeros((nc, 3)); count = np.zeros(nc); volumes = np.zeros(nc)
    np.add.at(centers, owner, fc); np.add.at(centers, neighbour, fc[:ni])
    np.add.at(count, owner, 1); np.add.at(count, neighbour, 1)
    centers /= count[:, None]
    vf = np.einsum('ij,ij->i', fc, sf)/3
    np.add.at(volumes, owner, vf); np.add.at(volumes, neighbour, -vf[:ni])
    if nc != 453496 or not np.all(count == 4) or volumes.min() <= 0:
        raise ValueError('Positive native tetrahedra required')
    # Official internal face orthogonality; boundary faces enter skewness only.
    d = centers[neighbour]-centers[owner[:ni]]
    angle = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', d, sf[:ni]) /
                                       (np.linalg.norm(d, axis=1)*area[:ni]), -1, 1)))
    nonorth = np.zeros(nc)
    np.maximum.at(nonorth, owner[:ni], angle); np.maximum.at(nonorth, neighbour, angle)
    cpf = fc-centers[owner]
    full_d = np.empty_like(cpf); full_d[:ni] = d
    normal = sf[ni:]/area[ni:, None]
    full_d[ni:] = normal*np.einsum('ij,ij->i', normal, cpf[ni:])[:, None]
    sv = cpf-full_d*(np.einsum('ij,ij->i', sf, cpf) /
                     np.einsum('ij,ij->i', sf, full_d))[:, None]
    mag = np.linalg.norm(sv, axis=1); svhat = sv/np.maximum(mag[:, None], 1e-150)
    fd = np.linalg.norm(full_d, axis=1)*np.r_[np.full(ni, .2), np.full(len(faces)-ni, .4)]
    for vertex in range(3):
        fd = np.maximum(fd, np.abs(np.einsum('ij,ij->i', svhat, tri[:, vertex]-fc)))
    skew_face = mag/fd; skew = np.zeros(nc)
    np.maximum.at(skew, owner, skew_face); np.maximum.at(skew, neighbour, skew_face[:ni])
    # Cell determinant from internal-face dyadic tensor, exact published method.
    tensor = np.zeros((nc, 3, 3)); summed_area = np.zeros(nc); internal_count = np.zeros(nc)
    dyad = sf[:ni, :, None]*sf[:ni, None, :]
    for cells in [owner[:ni], neighbour]:
        np.add.at(tensor, cells, dyad); np.add.at(summed_area, cells, area[:ni]); np.add.at(internal_count, cells, 1)
    det = np.abs(np.linalg.det(tensor/((summed_area/internal_count)**2)[:, None, None]))
    reproduced = {'nonorthogonality_max_deg':float(angle.max()), 'skewness_max':float(skew_face.max()), 'cell_determinant_min':float(det.min())}
    expected = [71.08568896, 1.099266956, .005150897637]
    if not np.allclose(list(reproduced.values()), expected, rtol=2e-7, atol=2e-7):
        raise ValueError('Local metrics do not reproduce independent checkMesh: '+str(reproduced))
    texts = {time:{name:(root/str(time)/name).read_text() for name in ['p','U']} for time,root in [(900,case),(960,new_inputs)]}
    p = {t:1.2*field_values(texts[t]['p'], 'internalField', nc, 1) for t in texts}
    u = {t:field_values(texts[t]['U'], 'internalField', nc, 3) for t in texts}
    if not all(np.isfinite(x).all() for x in [*p.values(),*u.values()]):
        raise ValueError('Complete finite preserved fields required')
    dp = p[960]-p[900]; du = np.linalg.norm(u[960]-u[900], axis=1)
    def quant(x):
        return {str(q):float(np.quantile(x,q)) for q in [0,.5,.9,.99,1]}
    def subset(mask):
        return {'cells':int(mask.sum()), 'volume_fraction':float(volumes[mask].sum()/volumes.sum()), 'nonorthogonality_deg':quant(nonorth[mask]), 'skewness':quant(skew[mask]), 'determinant':quant(det[mask]), 'pressure_change_abs_Pa':quant(np.abs(dp[mask])), 'velocity_change_m_s':quant(du[mask])}
    hot = np.abs(dp)>1.; top = np.argsort(np.abs(dp))[-10:][::-1]
    if not hot.any():
        raise ValueError('No >1Pa cells; do not invent hotspot statistics')
    rows = []
    for c in top:
        rows.append({'cell':int(c), 'center_mm':(centers[c]*1000).tolist(), 'radius_mm':float(np.linalg.norm(centers[c,:2])*1000), 'pressure_change_Pa':float(dp[c]), 'velocity_change_m_s':float(du[c]), 'adjacent_nonorthogonality_max_deg':float(nonorth[c]), 'adjacent_skewness_max':float(skew[c]), 'determinant':float(det[c]), 'nearest_boundary_face_centroid_distance_mm_proxy':{patch['name']:float(np.linalg.norm(fc[patch['startFace']:patch['startFace']+patch['nFaces']]-centers[c],axis=1).min()*1000) for patch in patches}})
    phi_text = (new_inputs/'960/phi').read_text()
    internal_phi = field_values(phi_text, 'internalField', ni, 1)
    if not np.isfinite(internal_phi).all():raise ValueError('Finite native face flux required')
    divergence = np.zeros(nc); np.add.at(divergence,owner[:ni],internal_phi); np.add.at(divergence,neighbour,-internal_phi)
    ports = {}; bcs = {}; patch_fluxes = {}
    for patch in patches:
        name=patch['name'];start=patch['startFace'];nf=patch['nFaces'];stop=start+nf
        flux=field_values(patch_block(phi_text,name),'value',nf,1);np.add.at(divergence,owner[start:stop],flux)
        if not np.isfinite(flux).all():raise ValueError('Finite native boundary flux required')
        patch_fluxes[name]=float(flux.sum())
        bcs[name]={}
        for field in ['p','U']:
            types=[re.search(r'\btype\s+(\w+)\s*;',patch_block(texts[t][field],name))[1] for t in [900,960]]
            if types[0]!=types[1]:raise ValueError('Native boundary types changed')
            bcs[name][field]=types[0]
        if name in ['inlet','outlet']:
            incoming=flux<0
            ports[name]={'net_flow_m3_s':float(flux.sum()), 'gross_incoming_m3_s':float(-flux[incoming].sum()), 'gross_outgoing_m3_s':float(flux[~incoming].sum()), 'incoming_area_fraction':float(area[start:stop][incoming].sum()/area[start:stop].sum()), 'incoming_face_fraction':float(incoming.mean()), 'face_count':nf, 'z_range_mm':[float(fc[start:stop,2].min()*1000),float(fc[start:stop,2].max()*1000)]}
    relative_div = divergence/volumes
    def corr(x,y):
        return None if np.std(x)==0 or np.std(y)==0 else float(np.corrcoef(x,y)[0,1])
    trace = {}; paired_rows = {}
    for label in ['control','absolute']:
        key='D1-runtime-symlink-repair/cases/'+label+'/log.foamRun';path=logs/key;record=log_index[key]
        if sha(path)!=record['sha256'] or path.stat().st_size!=record['bytes']:raise ValueError('Native log identity differs')
        used['D1/'+key]=record;rs=[];excluded=[]
        for block in re.split(r'(?m)^Time = ',path.read_text())[1:]:
            t=int(float(re.match(r'([0-9.]+)',block)[1]));solves=re.findall(r'Solving for p, Initial residual = ('+NUM+r'), Final residual = ('+NUM+r'), No Iterations (\d+)',block)
            ct=re.search(r'time step continuity errors : sum local = ('+NUM+'), global = ('+NUM+')',block)
            if len(solves)!=3 or not ct or not re.search(r'(?m)^ExecutionTime =',block):excluded.append(t);continue
            rs.append([t,*[float(v[0]) for v in solves],float(ct[1]),float(ct[2])])
        rs=np.array(rs);ratios=rs[:,2:4]/rs[:,1,None]
        if not np.isfinite(rs).all():raise ValueError('Finite native log samples required')
        paired=rs[(rs[:,0]>=901)&(rs[:,0]<=920)]
        if not np.array_equal(paired[:,0],np.arange(901,921)):raise ValueError('Prospective paired window incomplete')
        paired_rows[label]={'iterations':paired[:,0].astype(int).tolist(),'initial_p_first_mean':float(paired[:,1].mean()),'initial_p_third_mean':float(paired[:,3].mean()),'sum_local_continuity_mean':float(paired[:,4].mean()),'global_continuity_abs_max':float(np.abs(paired[:,5]).max())}
        trace[label]={'complete_iteration_count':len(rs),'excluded_incomplete_iterations':excluded,'initial_pressure_per_correction_mean':rs[:,1:4].mean(axis=0).tolist(),'initial_pressure_per_correction_max':rs[:,1:4].max(axis=0).tolist(),'last_over_first_correction_initial_ratio_mean':float(ratios[:,1].mean()),'sum_local_continuity_mean':float(rs[:,4].mean()),'sum_local_continuity_max':float(rs[:,4].max()),'global_continuity_abs_max':float(np.abs(rs[:,5]).max()),'correlation_initial_p_first_with_sum_local_continuity':corr(rs[:,1],rs[:,4]),'correlation_initial_p_first_with_initial_p_third':corr(rs[:,1],rs[:,3]),'iteration_labels_are_not_physical_time':True}
    result={'status':'preserved_D1_control960_spatial_and_coupling_diagnostic_only','new_solver_run':False,'actual_algebraic_residual_cells_identified':False,'physical_validation_established':False,'historical_fine_admission_restored':False,'script_sha256':sha(Path(__file__)),'dependency_sha256':{name:sha(Path(__file__).parent/name) for name in ['diagnose_and_merge_fv_cells.py','analyze_flow_balance.py']},'native_D1_archive_sha256':new_index['native_archive_sha256'],'used_private_inputs':used,'cells':nc,'reproduced_independent_mesh_metrics':reproduced,'checkpoint900_to960':{'pressure_delta_volume_RMS_Pa':float(np.sqrt(np.dot(volumes,dp*dp)/volumes.sum())),'velocity_delta_volume_RMS_m_s':float(np.sqrt(np.dot(volumes,du*du)/volumes.sum())),'all_cells':subset(np.ones(nc,dtype=bool)),'pressure_change_above1Pa_cells':subset(hot),'volume_fraction_dp_above1Pa_and_nonorth_above65deg':float(volumes[hot&(nonorth>65)].sum()/volumes[hot].sum()),'fraction_dp_above1Pa_cells_nonorth_above65deg':float((nonorth[hot]>65).mean()),'fraction_all_cells_nonorth_above65deg':float((nonorth>65).mean()),'correlation_abs_pressure_change_and_velocity_change':corr(np.abs(dp),du),'largest_pressure_change_cells':rows},'stored_MRF_relative_phi_continuity_at960':{'sum_abs_cell_flux_divergence_m3_s':float(np.abs(divergence).sum()),'global_net_flux_m3_s':float(divergence.sum()),'boundary_net_stored_relative_phi_m3_s':patch_fluxes,'discrete_global_sum_matches_boundary_sum':bool(abs(divergence.sum()-sum(patch_fluxes.values()))<1e-12),'cell_divergence_abs_s_inverse_quantiles':quant(np.abs(relative_div)),'correlation_abs_dp_with_abs_divergence_per_volume':corr(np.abs(dp),np.abs(relative_div)),'not_the_pressure_equation_residual':True},'port_flux_at960':ports,'unchanged_native_boundary_types_900_960':bcs,'complete_native_correction_log_statistics':trace,'matched_first20_correction_statistics':paired_rows,'matched_first20_local_continuity_control_over_absolute_ratio':paired_rows['control']['sum_local_continuity_mean']/paired_rows['absolute']['sum_local_continuity_mean'],'limits':['Pressure differences over60 steady iterations are not algebraic cell residuals, physical time signals or experimental uncertainty.','Local face-centroid distances are geometric proxies, not wall distances.','Statistics and correlations describe the same mesh only; association does not identify causation.','Relative stored MRF phi continuity is a discrete flux diagnostic, not absolute rotating-wall leakage.'],'mesh_metric_method_URL':'https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C','coupling_method_URL':'https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/applications/modules/incompressibleFluid/correctPressure.C'}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ['status','reproduced_independent_mesh_metrics','complete_native_correction_log_statistics','port_flux_at960']}))
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['old_inputs','new_inputs','logs','output']:ap.add_argument(name,type=Path)
    a=ap.parse_args();analyze(a.old_inputs,a.new_inputs,a.logs,a.output)
