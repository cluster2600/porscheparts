#!/usr/bin/env python3
"""Actual matched960 field differences and reverse outlet flux, no new solve."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from analyze_flow_balance import field_values,patch_block
from diagnose_and_merge_fv_cells import read


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def compare(control,candidate,output):
    control_index=json.loads((control/'input-manifest.json').read_text())['members']
    index=json.loads((candidate/'native-evidence-manifest.json').read_text())['members'];case=candidate/'cases/consistent'
    source=json.loads((case/'config-verification.json').read_text())['native_source_files']
    fields={};used={}
    for label,root in [('control',control),('consistent',case)]:
        fields[label]={}
        for name in ['p','U','phi']:
            file=root/'960'/name;key=('D1-runtime-symlink-repair/cases/control/' if label=='control' else 'cases/consistent/')+'960/'+name
            record=(control_index if label=='control' else index)[key]
            if sha(file)!=record['sha256'] or file.stat().st_size!=record['bytes']:raise ValueError('Matched native field identity differs')
            fields[label][name]=file.read_text();used[label+'/'+name]=record
    for name in ['points','faces','owner','neighbour','boundary']:
        p=case/'constant/polyMesh'/name;record=source['constant/polyMesh/'+name]
        if sha(p)!=record['sha256'] or p.stat().st_size!=record['bytes']:raise ValueError('Native same mesh identity differs')
        used['mesh/'+name]=record
    points,faces,owner,neighbour,patches=read(case);nc=int(max(owner.max(),neighbour.max()))+1;ni=len(neighbour)
    tri=points[faces];fc=tri.mean(axis=1);sf=.5*np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);vol=np.zeros(nc);vf=np.einsum('ij,ij->i',fc,sf)/3
    np.add.at(vol,owner,vf);np.add.at(vol,neighbour,-vf[:ni])
    if nc!=453496 or vol.min()<=0:raise ValueError('Positive same-mesh volumes required')
    p={k:1.2*field_values(v['p'],'internalField',nc,1) for k,v in fields.items()};u={k:field_values(v['U'],'internalField',nc,3) for k,v in fields.items()}
    if not all(np.isfinite(v).all() for v in [*p.values(),*u.values()]):raise ValueError('Complete finite matched fields required')
    dp=p['consistent']-p['control'];du=np.linalg.norm(u['consistent']-u['control'],axis=1);ports={}
    for label in fields:
        outlet=next(patch for patch in patches if patch['name']=='outlet');start=outlet['startFace'];nf=outlet['nFaces'];area=np.linalg.norm(sf[start:start+nf],axis=1)
        flux=field_values(patch_block(fields[label]['phi'],'outlet'),'value',nf,1)
        if not np.isfinite(flux).all():raise ValueError('Finite native outlet flux required')
        incoming=flux<0;net=float(flux.sum());reverse=float(-flux[incoming].sum())
        ports[label]={'net_flow_m3_s':net,'gross_reverse_flow_m3_s':reverse,'gross_reverse_to_net_ratio':reverse/net,'reverse_area_fraction':float(area[incoming].sum()/area.sum()),'reverse_face_count':int(incoming.sum()),'total_outlet_faces':nf}
    report={'status':'matched960_native_field_difference_and_persistent_outlet_reflux_only','new_solver_run':False,'same_mesh_cells':nc,'density_kg_m3_assumed':1.2,'pressure_difference_volume_RMS_Pa':float(np.sqrt(np.dot(vol,dp*dp)/vol.sum())),'pressure_difference_abs_max_Pa':float(np.abs(dp).max()),'pressure_difference_abs_cell_count_p99_Pa':float(np.quantile(np.abs(dp),.99)),'velocity_difference_volume_RMS_m_s':float(np.sqrt(np.dot(vol,du*du)/vol.sum())),'velocity_difference_max_m_s':float(du.max()),'outlet':ports,'used_native_inputs':used,'script_sha256':sha(Path(__file__)),'dependency_sha256':{name:sha(Path(__file__).parent/name) for name in ['analyze_flow_balance.py','diagnose_and_merge_fv_cells.py']},'actual_algebraic_residual_cells_identified':False,'physical_validation_established':False,'installed_cooling_improvement_established':False,'field_differences_are_not_experimental_error_bars':True}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['pressure_difference_volume_RMS_Pa','pressure_difference_abs_max_Pa','velocity_difference_volume_RMS_m_s','outlet']}));return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['control','candidate','output']:ap.add_argument(name,type=Path)
    a=ap.parse_args();compare(a.control,a.candidate,a.output)
