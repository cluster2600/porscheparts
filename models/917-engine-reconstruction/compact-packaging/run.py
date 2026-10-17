#!/usr/bin/env python3
"""Native longitudinal housings and compact pipes around hash-protected inherited parts."""
import argparse
from collections import Counter
import copy
import json
import os
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
from engine_layout import module
from reconstruct import check_output,save,sha256
import numpy as np
import trimesh
design=module('compact_design',HERE/'design.py')
audit=module('frozen_detail_audit',HERE.parent/'mechanical-detail/detail_audit.py')


def source_hashes():
    paths=[HERE/n for n in ('Bank.cs','Bank.csproj','design.py','run.py','verify.py','render.py')]
    paths += [HERE.parent/'mechanical-detail'/n for n in ('design.py','detail_audit.py','check_connections.py')]
    paths += [study.ROOT/'parts/picogk-catalog/common/Sdf.cs']
    return {str(p.relative_to(study.ROOT)):sha256(p) for p in paths}


def audit_level(native,old=None):
    if old is None:return audit.audit_native(native)
    current=json.loads((native/'receipt.json').read_text())
    previous=json.loads((old/'receipt.json').read_text())['parts']
    witnesses=json.loads((old/'independent-audit.json').read_text());cached={}
    for name,row in current['parts'].items():
        for ext in ('stl','vdb'):
            if sha256(native/(name+'.'+ext))!=row[ext+'_sha256']:raise ValueError('New native file changed')
        if name in previous and witnesses[name]['passed'] and row['stl_sha256']==previous[name]['stl_sha256']:
            cached[name]=witnesses[name]
    meshes={};audits={}
    for reused,names in [(True,set(cached)),(False,set(current['parts'])-set(cached))]:
        if not names:continue
        folder=native/('_audit_cache' if reused else '_audit_fresh');folder.mkdir()
        save(folder/'receipt.json',{**current,'parts':{n:current['parts'][n] for n in names}})
        for n in names:
            for ext in ('stl','vdb'):os.link(native/(n+'.'+ext),folder/(n+'.'+ext))
        if reused:
            save(folder/'independent-audit.json',{n:cached[n] for n in names});m,a=audit.verified_cache(folder)
            for row in a.values():row['audit_reused_from']={'scope':'byte_identical_STL_topology_only_current_VDB_hash_checked','receipt_sha256':sha256(old/'receipt.json'),'witness_sha256':sha256(old/'independent-audit.json')}
        else:m,a=audit.audit_native(folder)
        meshes.update(m);audits.update(a);shutil.rmtree(folder)
    save(native/'independent-audit.json',audits);return meshes,audits


def run(previous,output,dotnet,audit_from=None):
    output=check_output(output);output.mkdir(parents=True,mode=0o700);executed=source_hashes();save(output/'execution-sources.json',executed)
    for name in executed:
        target=output/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(study.ROOT/name,target)
    lock=json.loads((previous/'delivery-manifest.json').read_text())['files']
    def prior(name):
        p=previous/name
        if sha256(p)!=lock[name]:raise ValueError('Prior delivery changed: '+name)
        return p
    old=json.loads(prior('assembly.json').read_text());cfg=json.loads(prior('config.json').read_text())
    banks=design.bank_config(old['instances'],cfg['cam_local_y_mm'],cfg['cam_local_z_mm'])
    recipe=[]
    for bank in (-1,1):
        p=design.charge_path(bank)
        recipe.append({'id':'charge_pipe_'+('negative' if bank<0 else 'positive'),'points':p,'outer_radii':[18,18]+[25]*(len(p)-2),'inner_radii':[15.5,15.5]+[22.5]*(len(p)-2)})
    save(output/'route.json',{'classification':'hypothetical_pipe_routes_no_physical_release','manufacturing_authorized':False,'parts':recipe})
    study.command([dotnet,'build',HERE/'Bank.csproj','-c','Release','-o',output/'bank-app','-p:BaseIntermediateOutputPath='+str(output/'bank-obj')+'/'],output/'bank-build.log')
    levels={};fine={}
    for grid in (1,.5):
        field=prior(f'housing-clearance-vdb-{grid:g}/drive_housing.vdb')
        config={'classification':'917_longitudinal_bank_geometry_hypothesis','banks':banks,'wall_mm':3,'gear_envelopes':cfg['gear_envelopes'],'charge_parts':recipe,
                'drive_housing_vdb':{'path':str(field),'sha256':sha256(field)},'manufacturing_authorized':False,'engine_start_authorized':False}
        path=output/f'bank-{grid:g}.json';save(path,config)
        study.command([dotnet,output/'bank-app/Bank.dll',path,sha256(path),grid,output/f'bank-native-{grid:g}'],output/f'bank-native-{grid:g}.log')
        bank_meshes,bank_audit=audit_level(output/f'bank-native-{grid:g}',audit_from/f'bank-native-{grid:g}' if audit_from else None)
        if not all(r['passed'] for r in bank_audit.values()):raise ValueError('Native bank or pipe topology rejected')
        levels[str(grid)]={'bank':{n:r for n,r in bank_audit.items() if not n.startswith('charge_pipe_')},'pipes':{n:r for n,r in bank_audit.items() if n.startswith('charge_pipe_')}}
        if grid==.5:fine=bank_meshes
    dense=copy.deepcopy(config);dense['wall_mm']=5;path=output/'bank-dense.json';save(path,dense)
    study.command([dotnet,output/'bank-app/Bank.dll',path,sha256(path),'.5',output/'bank-dense-native'],output/'bank-dense-native.log')
    dense_meshes,dense_audits=audit_level(output/'bank-dense-native',audit_from/'bank-dense-native' if audit_from else None)
    if not all(r['passed'] for r in dense_audits.values()):raise ValueError('Dense wall countertrial topology rejected')
    wall_control={n:{'candidate_volume_mm3':float(m.volume),'dense_volume_mm3':float(dense_meshes[n].volume),'volume_reduction_fraction':1-float(m.volume)/float(dense_meshes[n].volume)} for n,m in fine.items() if n.startswith('bank_valve_cover_')}
    if any(r['volume_reduction_fraction']<=0 for r in wall_control.values()):raise ValueError('Wall candidate did not reduce geometric volume')
    rows=[copy.deepcopy(r) for r in old['instances'] if r['family']!='valve_cover']
    for bank in banks:
        suffix='negative' if bank['bank']<0 else 'positive'
        for family in ('bank_valve_cover_','bank_adapter_'):rows.append({'family':family+suffix,'bank':bank['bank'],'matrix_mm':np.eye(4).tolist(),'placement_basis':'native_global_candidate_coordinates'})
        for x in bank['bolt_x_mm']:
            for y in (-bank['bolt_y_mm'],bank['bolt_y_mm']):
                # Candidate head-seat gap leaves room for an unqualified washer; it is not preload evidence.
                local=np.eye(4);local[:3,:3]=[[0,0,-1],[0,1,0],[1,0,0]];local[:3,3]=[x,y,bank['bolt_head_z_mm']]
                rows.append({'family':'drive_cover_bolt','bank':bank['bank'],'matrix_mm':(np.asarray(bank['pose'])@local).tolist(),'placement_basis':'candidate_bank_cover_fastener_no_preload'})
    for i,r in enumerate(rows):r['instance_id']=f'part_{i:04d}'
    counts=Counter(r['family'] for r in rows);pieces=output/'pieces';pieces.mkdir();meshes={}
    for name in counts:
        p=pieces/(name+'.stl')
        if name in fine:meshes[name]=fine[name];meshes[name].export(p)
        else:shutil.copy2(prior('pieces/'+name+'.stl'),p);meshes[name]=trimesh.load_mesh(p,process=True)
    def protected(rs):return sorted(json.dumps({k:r[k] for k in ('family','matrix_mm','bank','cycle') if k in r},sort_keys=True) for r in rs if r['family']=='individual_head' or r['family'].startswith(('head_component_','turbo_')))
    if protected(rows)!=protected(old['instances']):raise ValueError('Protected head, valve or turbo pose changed')
    parts={n:{**old['parts'].get(n,{'id':n,'actual_alloy':None,'manufacturing_process':None}),'quantity':q} for n,q in counts.items()}
    save(output/'assembly.json',{'classification':'917_longitudinal_bank_cold_hypothesis_no_release','units':'mm_hypothetical','parts':parts,'instances':rows})
    verification=module('compact_verify',HERE/'verify.py').run(output,meshes,rows,fine)
    connections=module('frozen_connections',HERE.parent/'mechanical-detail/check_connections.py').run(output)
    scene=study.prior.export_scene(output,meshes,rows)
    if executed!=source_hashes():raise ValueError('Executed sources changed')
    report={'classification':'917_longitudinal_bank_geometry_no_physical_release','source_hashes':executed,'native_audits':levels,
            'verification':verification,'connection_checks':connections,'glb_roundtrip':scene,'banks':banks,'wall_control':wall_control,'dense_audits':dense_audits,
            'definitions':len(parts),'assembly_occurrences':len(rows),'protected_pose_records_unchanged':True,
            'inherited_prototype_hashes':{n:lock['pieces/'+n+'.stl'] for n in counts if n not in fine},
            'prior_manifest_sha256':sha256(previous/'delivery-manifest.json'),'actual_alloy':None,'measured_interfaces':None,
            'full_assembly_interference_checked':False,'thermal_or_fatigue_validated':False,'professional_review':None,
            'manufacturing_authorized':False,'engine_start_authorized':False}
    save(output/'report.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--previous',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--dotnet',required=True);p.add_argument('--audit-from',type=Path);a=p.parse_args()
    old=a.audit_from.resolve() if a.audit_from else None
    if old:old.relative_to(study.ROOT/'work')
    r=run(a.previous.resolve(),a.output.resolve(),a.dotnet,old);print(json.dumps({k:r[k] for k in ('definitions','assembly_occurrences','manufacturing_authorized')}))
