#!/usr/bin/env python3
"""Light preserved-field diagnostics and hypothetical column sizing; no mesh/solve."""
import argparse,hashlib,json,re
from pathlib import Path
import numpy as np
from analyze_flow_balance import field_values,patch_block
from diagnose_and_merge_fv_cells import read


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def diagnose(control,candidate,historical,output,private_selections):
    indexes={'control':json.loads((control/'input-manifest.json').read_text())['members'],'consistent':json.loads((candidate/'native-evidence-manifest.json').read_text())['members'],'historical':json.loads((historical/'input-manifest.json').read_text())['members']}
    case=candidate/'cases/consistent';source=json.loads((case/'config-verification.json').read_text())['native_source_files'];used={};texts={}
    def verified(p,key,record):
        if sha(p)!=record['sha256'] or p.stat().st_size!=record['bytes']:raise ValueError('Preserved input identity differs '+key)
        used[key]=record;return p.read_text()
    for label,root,prefix in [('control',control,'D1-runtime-symlink-repair/cases/control/'),('consistent',case,'cases/consistent/')]:
        texts[label]={name:verified(root/'960'/name,label+'/'+name,indexes[label][prefix+'960/'+name]) for name in ['p','U','phi']}
    old=historical/'cfd-V2-fine-pressure015-900/900/p'
    p900_text=verified(old,'historical/p900',indexes['historical']['cfd-V2-fine-pressure015-900/900/p'])
    for name in ['points','faces','owner','neighbour','boundary','cellZones']:
        verified(case/'constant/polyMesh'/name,'mesh/'+name,source['constant/polyMesh/'+name])
    points,faces,owner,neighbour,patches=read(case);nc=int(max(owner.max(),neighbour.max()))+1;ni=len(neighbour)
    tri=points[faces];fc=tri.mean(axis=1);sf=.5*np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(sf,axis=1)
    centers=np.zeros((nc,3));nfaces=np.zeros(nc);volumes=np.zeros(nc);vf=np.einsum('ij,ij->i',fc,sf)/3
    np.add.at(centers,owner,fc);np.add.at(centers,neighbour,fc[:ni]);np.add.at(nfaces,owner,1);np.add.at(nfaces,neighbour,1);centers/=nfaces[:,None]
    np.add.at(volumes,owner,vf);np.add.at(volumes,neighbour,-vf[:ni])
    if nc!=453496 or volumes.min()<=0 or not np.all(nfaces==4):raise ValueError('Original positive tetrahedral core required')
    p={k:1.2*field_values(v['p'],'internalField',nc,1) for k,v in texts.items()};u={k:field_values(v['U'],'internalField',nc,3) for k,v in texts.items()};p900=1.2*field_values(p900_text,'internalField',nc,1)
    if not all(np.isfinite(v).all() for v in [*p.values(),*u.values(),p900]):raise ValueError('Finite native fields required')
    dp=p['consistent']-p['control'];du=np.linalg.norm(u['consistent']-u['control'],axis=1)
    zone=patch_block((case/'constant/polyMesh/cellZones').read_text(),'rotorZone');zm=re.search(r'cellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)\s*;',zone,re.S);labels=np.array(list(map(int,zm[2].split())),dtype=np.int64)
    if len(labels)!=int(zm[1]):raise ValueError('Native MRF label count')
    is_mrf=np.zeros(nc,dtype=bool);is_mrf[labels]=True
    outlet=next(patch for patch in patches if patch['name']=='outlet');start=outlet['startFace'];nf=outlet['nFaces'];end=start+nf;otri=tri[start:end];oarea=area[start:end];ofc=fc[start:end];oradius=np.linalg.norm(ofc[:,:2],axis=1)
    phi={k:field_values(patch_block(v['phi'],'outlet'),'value',nf,1) for k,v in texts.items()};ub={k:field_values(patch_block(v['U'],'outlet'),'value',nf,3) for k,v in texts.items()}
    radial=np.column_stack((ofc[:,:2]/oradius[:,None],np.zeros(nf)));R=float(np.linalg.norm(points[np.unique(faces[start:end]),:2],axis=1).max());D=.275
    radial_rows=[]
    for low,high in zip([0,.25,.5,.6,.75],[.25,.5,.6,.75,1.000001]):
        m=(oradius>=low*R)&(oradius<high*R);flux=phi['consistent'][m];ar=oarea[m];ur=np.einsum('ij,ij->i',ub['consistent'][m],radial[m])
        radial_rows.append({'radius_ratio_band':[low,min(high,1.)],'faces':int(m.sum()),'area_fraction':float(ar.sum()/oarea.sum()),'gross_reverse_flow_m3_s':float(-flux[flux<0].sum()),'net_flow_m3_s':float(flux.sum()),'area_mean_radial_velocity_m_s':float(np.dot(ar,ur)/ar.sum()) if ar.sum() else None,'area_mean_axial_velocity_m_s':float(np.dot(ar,ub['consistent'][m,2])/ar.sum()) if ar.sum() else None})
    edges=np.sort(np.stack((faces[start:end][:,[0,1]],faces[start:end][:,[1,2]],faces[start:end][:,[2,0]]),axis=1),axis=2);unique,inverse,counts=np.unique(edges.reshape(-1,2),axis=0,return_inverse=True,return_counts=True);boundary=(counts[inverse].reshape(nf,3)==1);boundary_count=boundary.sum(axis=1)
    if not np.all(np.isin(counts,[1,2])):raise ValueError('Outlet triangulation edges must have1 or2 incidents')
    edge_vectors=np.roll(otri,-1,axis=1)-otri;edge_lengths=np.linalg.norm(edge_vectors,axis=2)
    screens=[]
    for layers in [40,50,60,80,100]:
        dz=D/layers;side=np.cross(edge_vectors,np.array([0.,0.,-dz]));side[boundary]=0;nsides=3-boundary_count;side_sum=np.linalg.norm(side,axis=2).sum(axis=1);dyad=np.einsum('fai,faj->fij',side,side)
        states={}
        for name,ncaps in [('first_or_interior',2),('last_with_outlet_boundary',1)]:
            avg=(side_sum+ncaps*oarea)/(nsides+ncaps);tensor=dyad.copy();tensor[:,2,2]+=ncaps*oarea**2;det=np.abs(np.linalg.det(tensor/avg[:,None,None]**2))
            states[name]={'minimum_internal_face_determinant_proxy':float(det.min()),'columns_below_original0p001':int((det<.001).sum()),'p01_determinant':float(np.quantile(det,.01))}
        screens.append({'layers':layers,'uniform_dz_mm':dz*1000,'unmerged_appended_prism_cells':nf*layers,'unmerged_total_cells':nc+nf*layers,'states':states,'hypothetical_only_not_an_independent_mesh_gate':True})
    indices=np.argsort(np.abs(dp))[-10:][::-1];hot=[]
    for c in indices:
        hot.append({'cell':int(c),'center_mm':(centers[c]*1000).tolist(),'radius_mm':float(np.linalg.norm(centers[c,:2])*1000),'volume_mm3':float(volumes[c]*1e9),'p900_Pa':float(p900[c]),'control960_p_Pa':float(p['control'][c]),'consistent960_p_Pa':float(p['consistent'][c]),'consistent_minus_control_Pa':float(dp[c]),'control_minus900_Pa':float(p['control'][c]-p900[c]),'consistent_minus900_Pa':float(p['consistent'][c]-p900[c]),'velocity_difference_m_s':float(du[c]),'nearest_boundary_face_centroid_distance_mm_proxy':{patch['name']:float(np.linalg.norm(fc[patch['startFace']:patch['startFace']+patch['nFaces']]-centers[c],axis=1).min()*1000) for patch in patches}})
    localization=[];total_energy=float(np.dot(volumes,dp*dp))
    for limit in [1,10,100]:
        m=np.abs(dp)>limit;localization.append({'abs_pressure_difference_threshold_Pa':limit,'cells':int(m.sum()),'volume_fraction':float(volumes[m].sum()/volumes.sum()),'fraction_of_volume_weighted_squared_pressure_difference':float(np.dot(volumes[m],dp[m]**2)/total_energy)})
    zcuts=[-49.500001,-45,-40,-35,-30,-25,-20,-15,-10,0,40,77.000001];axial=[]
    for lower,upper in zip(zcuts,zcuts[1:]):
        m=(centers[:,2]*1000>=lower)&(centers[:,2]*1000<upper);vs=volumes[m].sum()
        axial.append({'z_band_mm':[lower,upper],'cells':int(m.sum()),'volume_fraction':float(vs/volumes.sum()),'pressure_difference_volume_RMS_Pa':float(np.sqrt(np.dot(volumes[m],dp[m]**2)/vs)) if vs else None,'maximum_abs_pressure_difference_Pa':float(np.abs(dp[m]).max()) if m.any() else None,'velocity_difference_volume_RMS_m_s':float(np.sqrt(np.dot(volumes[m],du[m]**2)/vs)) if vs else None})
    band=np.flatnonzero((centers[:,2]>=-.038)&(centers[:,2]<-.034));near=np.unique(owner[start:end]);tip=np.flatnonzero((np.linalg.norm(centers[:,:2],axis=1)>=.12)&(centers[:,2]>=-.022)&(centers[:,2]<-.01));zones={}
    for name,ids in [('commonPressureBand',band),('commonOutletOwners',near),('commonTipWake',tip)]:
        v=volumes[ids];zones[name]={'cells':len(ids),'volume_m3':float(v.sum()),'global_cell_ids_little_i8_sha256':hashlib.sha256(ids.astype('<i8').tobytes()).hexdigest(),'snapshot900_volume_mean_p_Pa':float(np.dot(v,p900[ids])/v.sum()),'control960_volume_mean_p_Pa':float(np.dot(v,p['control'][ids])/v.sum()),'consistent960_volume_mean_p_Pa':float(np.dot(v,p['consistent'][ids])/v.sum()),'control_vs_consistent_pressure_volume_RMS_Pa':float(np.sqrt(np.dot(v,dp[ids]**2)/v.sum())),'contains_MRF_cells':bool(is_mrf[ids].any()),'pressure_is_absolute_static_scalar_in_both_cases':True}
    private_selections.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(private_selections,commonPressureBand=band,commonOutletOwners=near,commonTipWake=tip,commonOutletFaceIds=np.arange(start,end,dtype=np.int64),commonOutletOwnerCellIds=owner[start:end],commonOutletVertexIds=faces[start:end],cellVolumes=volumes)
    result={'status':'outlet_sensitivity_preparation_from_preserved_fields_only','new_solver_run':False,'new_mesh_generated':False,'physical_validation_established':False,'script_sha256':sha(Path(__file__)),'dependency_sha256':{name:sha(Path(__file__).parent/name) for name in ['analyze_flow_balance.py','diagnose_and_merge_fv_cells.py']},'used_native_inputs':used,'assumed_rotor_diameter_mm':D*1000,'native_outlet':{'z_mm':float(ofc[:,2].mean()*1000),'radius_max_mm':R*1000,'faces':nf,'area_m2':float(oarea.sum()),'minimum_triangle_area_mm2':float(oarea.min()*1e6),'triangle_area_p01_mm2':float(np.quantile(oarea,.01)*1e6),'minimum_edge_mm':float(edge_lengths.min()*1000),'boundary_edges':int((counts==1).sum()),'triangles_with_two_boundary_edges':int((boundary_count==2).sum()),'owner_cells_inside_MRF':int(is_mrf[owner[start:end]].sum()),'radial_flux_and_velocity_bands':radial_rows},'MRF_cell_center_z_range_mm':[float(centers[labels,2].min()*1000),float(centers[labels,2].max()*1000)],'local317Pa_difference':{'pressure_volume_RMS_Pa':float(np.sqrt(total_energy/volumes.sum())),'absolute_cell_count_p99_Pa':float(np.quantile(np.abs(dp),.99)),'largest_pressure_difference_cells':hot,'threshold_localization':localization,'axial_localization':axial,'not_an_algebraic_residual_or_a_physical_frequency':True,'different_numerical_coupling_only_no_domain_difference_in_this_pair':True},'common_zones':zones,'hypothetical_uniform_prism_column_screen':screens,'private_selections_sha256':sha(private_selections),'private_selections_not_published':True,'extension_distance_is_not_yet_proven_sufficient':True,'limits':['No existing fields below the current exit; true recirculation closure length or a physically minimal outlet distance cannot be inferred.','Column determinant screening is algebraic geometry only, not meshing, checkMesh or flow validation.','Native cell-based pressure zones preserve the same statistic and avoid comparing a fixed outlet pressure with an internal interpolated pressure.']}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','native_outlet','MRF_cell_center_z_range_mm','common_zones','hypothetical_uniform_prism_column_screen']}));return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['control','candidate','historical','output','private_selections']:ap.add_argument(name,type=Path)
    a=ap.parse_args();diagnose(a.control,a.candidate,a.historical,a.output,a.private_selections)
