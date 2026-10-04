#!/usr/bin/env python3
"""Append fixed axial columns while preserving original core IDs and face maps."""
import hashlib,json,re
from pathlib import Path
import numpy as np
from diagnose_and_merge_fv_cells import read,body
from analyze_flow_balance import field_values,patch_block


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(a):return hashlib.sha256(np.asarray(a,dtype='<i8').tobytes()).hexdigest()


def listfile(path,cls,values,count=None):
    if count is None:count=len(values)
    with path.open('w') as f:
        f.write('FoamFile {version 2.0; format ascii; class '+cls+'; object '+path.name+';}\n'+str(count)+'\n(\n')
        for value in values:f.write(str(value)+'\n')
        f.write(')\n')


def append_arrays(points,faces,owner,neighbour,patches,layers,length):
    """Pure topology builder. Output maps are explicit; unchanged cell IDs mandatory."""
    ni=len(neighbour);nc=int(max(owner.max(),neighbour.max()))+1
    outlet=next(p for p in patches if p['name']=='outlet');start=outlet['startFace'];nf=outlet['nFaces'];end=start+nf;tri=faces[start:end]
    verts=np.unique(tri);nv=len(verts);local=np.full(len(points),-1,dtype=np.int64);local[verts]=np.arange(nv)
    if not np.allclose(points[verts,2],points[verts[0],2],atol=1e-12,rtol=0):raise ValueError('Planar outlet required')
    normals=.5*np.cross(points[tri[:,1]]-points[tri[:,0]],points[tri[:,2]]-points[tri[:,0]])
    if (normals[:,2]>=0).any():raise ValueError('Original outlet must be oriented toward-Z')
    pnew=np.concatenate([points,*[points[verts]+[0,0,-length*j/layers] for j in range(1,layers+1)]])
    ids=lambda a,j:a if j==0 else len(points)+(j-1)*nv+local[a]
    edge0=np.sort(np.stack((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]),axis=1),axis=2).reshape(-1,2)
    edges,inv,counts=np.unique(edge0,axis=0,return_inverse=True,return_counts=True)
    if not np.isin(counts,[1,2]).all():raise ValueError('Nonmanifold outlet')
    incident=[[] for _ in edges]
    for k,e in enumerate(inv):incident[e].append((k//3,k%3))
    # Build triangle or quad rows in a padded array, then sort internal owner/neighbour.
    internal_faces=[np.column_stack((faces[:ni],np.full(ni,-1)))];owners=[owner[:ni]];neigh=[neighbour]
    old_ids=[np.arange(ni)];columns=[np.full(ni,-1)];kinds=[np.full(ni,0)]
    for j in range(layers):
        internal_faces.append(np.column_stack((ids(tri,j),np.full(nf,-1))))
        owners.append(owner[start:end] if j==0 else nc+(j-1)*nf+np.arange(nf));neigh.append(nc+j*nf+np.arange(nf))
        old_ids.append(np.arange(start,end) if j==0 else np.full(nf,-1));columns.append(np.arange(nf));kinds.append(np.full(nf,1))
    side_internal=[];side_boundary=[]
    for edge,inc in zip(edges,incident):
        c,k=inc[0];a,b=tri[c,k],tri[c,(k+1)%3]
        for j in range(layers):
            quad=[int(ids(a,j)),int(ids(b,j)),int(ids(b,j+1)),int(ids(a,j+1))]
            own=nc+j*nf+c
            if len(inc)==2:
                other=nc+j*nf+inc[1][0]
                if own>other:own,other=other,own;quad.reverse()
                side_internal.append((quad,own,other,c))
            else:side_boundary.append((quad,own,c))
    if side_internal:
        internal_faces.append(np.asarray([x[0] for x in side_internal]));owners.append(np.array([x[1] for x in side_internal]));neigh.append(np.array([x[2] for x in side_internal]));old_ids.append(np.full(len(side_internal),-1));columns.append(np.array([x[3] for x in side_internal]));kinds.append(np.full(len(side_internal),2))
    f=np.concatenate(internal_faces);o=np.concatenate(owners);n=np.concatenate(neigh);old=np.concatenate(old_ids);col=np.concatenate(columns);kind=np.concatenate(kinds)
    order=np.lexsort((n,o));f=f[order];o=o[order];n=n[order];old=old[order];col=col[order];kind=kind[order]
    if (o>=n).any():raise ValueError('Upper triangular orientation required')
    newni=len(n);fparts=[f];oparts=[o];oldparts=[old];colparts=[col];kindparts=[kind];newpatches=[];nextface=newni
    for patch in patches:
        q=dict(patch);q['startFace']=nextface
        if q['name']=='outlet':
            rows=ids(tri,layers);own=nc+(layers-1)*nf+np.arange(nf);oldrow=np.full(nf,-1);column=np.arange(nf);typecode=3
        else:
            s=patch['startFace'];rows=faces[s:s+patch['nFaces']];own=owner[s:s+patch['nFaces']];oldrow=np.arange(s,s+patch['nFaces']);column=np.full(len(rows),-1);typecode=0
        fparts.append(np.column_stack((rows,np.full(len(rows),-1))));oparts.append(own);oldparts.append(oldrow);colparts.append(column);kindparts.append(np.full(len(rows),typecode));newpatches.append(q);nextface+=len(rows)
    sidefaces=np.asarray([x[0] for x in side_boundary]);fparts.append(sidefaces);oparts.append(np.array([x[1] for x in side_boundary]));oldparts.append(np.full(len(sidefaces),-1));colparts.append(np.array([x[2] for x in side_boundary]));kindparts.append(np.full(len(sidefaces),4));newpatches.append({'name':'bufferSides','type':'patch','startFace':nextface,'nFaces':len(sidefaces)})
    f=np.concatenate(fparts);o=np.concatenate(oparts);old=np.concatenate(oldparts);col=np.concatenate(colparts);kind=np.concatenate(kindparts)
    mapping=np.full(len(faces),-1,dtype=np.int64);mask=old>=0;mapping[old[mask]]=np.flatnonzero(mask)
    if (mapping<0).any() or not np.array_equal(f[mapping,:3],faces) or not np.array_equal(o[mapping],owner) or not np.array_equal(n[mapping[:ni]],neighbour):raise ValueError('Original face/cell connectivity changed')
    return {'points':pnew,'faces':f,'owner':o,'neighbour':n,'patches':newpatches,'old_to_new_faces':mapping,'old_face':old,'column':col,'kind':kind,'core_cells':nc,'outlet_faces':nf,'original_outlet_start':start,'layers':layers,'length':length,'side_edges':int((counts==1).sum())}


def write_mesh(case,m,original_points_text):
    mesh=case/'constant/polyMesh';mesh.mkdir(parents=True,exist_ok=True)
    # Original numeric coordinate lines retained exactly, with original point IDs.
    _,text=body_original(original_points_text);new=m['points'];header=original_points_text[:re.search(r'(?m)^\s*\d+\s*\n\(',original_points_text).start()]
    old_count=int(re.search(r'(?m)^\s*(\d+)\s*\n\(',original_points_text)[1]);appended=new[old_count:]
    (mesh/'points').write_text(header+str(len(new))+'\n(\n'+text.rstrip()+'\n'+''.join('('+ ' '.join(format(v,'.17g') for v in row)+')\n' for row in appended)+')\n')
    listfile(mesh/'faces','faceList',(str(3 if row[3]<0 else 4)+'('+ ' '.join(map(str,row[:3] if row[3]<0 else row))+')' for row in m['faces']),len(m['faces']))
    listfile(mesh/'owner','labelList',m['owner']);listfile(mesh/'neighbour','labelList',m['neighbour'])
    (mesh/'boundary').write_text('FoamFile {version 2.0; format ascii; class polyBoundaryMesh; object boundary;}\n'+str(len(m['patches']))+'\n(\n'+''.join(p['name']+'\n{type '+p['type']+'; nFaces '+str(p['nFaces'])+'; startFace '+str(p['startFace'])+';}\n' for p in m['patches'])+')\n')


def body_original(text):
    match=re.search(r'(?m)^\s*(\d+)\s*\n\(\s*\n',text);end=text.find('\n)',match.end())
    return int(match[1]),text[match.end():end]


def add_zones(case,original_zones,selections,outlet_face_ids):
    match=re.search(r'(?m)^\s*(\d+)\s*\n\(\s*\n',original_zones);end=original_zones.rfind(')')
    inside=original_zones[match.end():end].rstrip();count=int(match[1]);extra=''
    for name in ['commonPressureBand','commonOutletOwners','commonTipWake']:
        values=selections[name];extra+='\n'+name+' {type cellZone; cellLabels List<label>\n'+str(len(values))+'\n(\n'+'\n'.join(map(str,values))+'\n);}\n'
    mesh=case/'constant/polyMesh';(mesh/'cellZones').write_text(original_zones[:match.start()]+str(count+3)+'\n(\n'+inside+extra+')\n')
    (mesh/'faceZones').write_text('FoamFile {version 2.0; format ascii; class faceZoneList; object faceZones;}\n1\n(\ncommonOutletFlux {type faceZone; faceLabels List<label>\n'+str(len(outlet_face_ids))+'\n(\n'+'\n'.join(map(str,outlet_face_ids))+'\n); flipMap List<bool>\n'+str(len(outlet_face_ids))+'\n(\n'+'\n'.join(['false']*len(outlet_face_ids))+'\n);}\n)\n')


def replace_internal(text,values,components):
    match=re.search(r'internalField\s+nonuniform\s+List<(?:scalar|vector)>\s+\d+\s*\(.*?\)\s*;',text,re.S)
    if not match:raise ValueError('Nonuniform native internal field required')
    if components==1:rows=(format(float(x),'.17g') for x in values)
    else:rows=('('+ ' '.join(format(float(x),'.17g') for x in row)+')' for row in values)
    return text[:match.start()]+'internalField nonuniform List<'+('scalar' if components==1 else 'vector')+'>\n'+str(len(values))+'\n(\n'+'\n'.join(rows)+'\n);'+text[match.end():]


def initialize_fields(source,case,m):
    nc=m['core_cells'];nf=m['outlet_faces'];ni=len(m['neighbour']);oldni=len(body(source/'constant/polyMesh/neighbour')[1].split());s=m['original_outlet_start'];maps=m['old_to_new_faces'];seed=source/'960';out=case/'960';out.mkdir(exist_ok=True);records={}
    for name in ['U','p','k','omega','nut','phi','Uf']:
        text=(seed/name).read_text();components=3 if name in ['U','Uf'] else 1;isvol=name not in ['phi','Uf']
        before=field_values(text,'internalField',nc if isvol else oldni,components);ob=field_values(patch_block(text,'outlet'),'value',nf,components)
        if name in ['k','omega','nut'] and (before<0).any():raise ValueError('Negative turbulence seed')
        if isvol:
            values=np.concatenate([before,np.tile(ob,(m['layers'],1)) if components==3 else np.tile(ob,m['layers'])])
        else:
            shape=(ni,components) if components==3 else (ni,);values=np.zeros(shape);mapped=m['old_face'][:ni]>=0;old=m['old_face'][:ni];core=mapped&(old<oldni);values[core]=before[old[core]]
            new=m['kind'][:ni]==1;values[new]=ob[m['column'][:ni][new]]
            if name=='Uf':
                sides=m['kind'][:ni]==2;values[sides]=ob[m['column'][:ni][sides]]
        newtext=replace_internal(text,values,components);idx=newtext.rfind('}')
        bc={'U':'type slip;','p':'type zeroGradient;','k':'type zeroGradient;','omega':'type zeroGradient;','nut':'type calculated; value uniform0;','phi':'type calculated; value uniform0;','Uf':'type calculated; value uniform (0 0 0);'}[name].replace('uniform0','uniform 0')
        newtext=newtext[:idx]+'\nbufferSides { '+bc+' }\n'+newtext[idx:]
        (out/name).write_text(newtext)
        check=field_values(newtext,'internalField',len(values),components)
        if isvol:valid=np.array_equal(check[:nc],before)
        else:valid=np.array_equal(check[maps[:oldni]],before) and np.array_equal(check[maps[s:s+nf]],ob)
        if not valid or not np.isfinite(check).all():raise ValueError('Seed correspondence failure '+name)
        records[name]={'source_sha256':sha(seed/name),'initialized_sha256':sha(out/name),'core_values_identical':True,'common_plane_phi_identical':name=='phi' or None,'count':len(check)}
    return records


def prepare_pair(source,output,capsule,selections_file):
    """Verify original identities; create current and extended cases without solving."""
    import shutil,time
    from test_outlet_prisms import volumes
    started=time.monotonic();protocol=json.loads((capsule/'configs/protocol.json').read_text());index=json.loads((capsule/'configs/source-manifest.json').read_text())
    for name,record in index.items():
        f=source/name
        if not f.is_file() or f.stat().st_size!=record['bytes'] or sha(f)!=record['sha256']:raise ValueError('Native source identity '+name)
    if sha(selections_file)!=json.loads((capsule/'configs/diagnostic.json').read_text())['private_selections_sha256']:raise ValueError('Private common selections identity')
    selections=np.load(selections_file,allow_pickle=False);points,faces,owner,neighbour,patches=read(source);nc=453496
    if int(max(owner.max(),neighbour.max()))+1!=nc:raise ValueError('Fixed original453496-cell mesh required')
    m=append_arrays(points,faces,owner,neighbour,patches,50,.275)
    if m['outlet_faces']!=4542 or len(m['owner'])==0 or m['side_edges']!=156 or int(max(m['owner'].max(),m['neighbour'].max()))+1!=680596:raise ValueError('Prepared exact topology required')
    v=volumes(m['points'],m['faces'],m['owner'],m['neighbour'])
    if (v<=0).any() or not np.allclose(v[:nc],selections['cellVolumes'],rtol=1e-8,atol=1e-18):raise ValueError('Positive added cells and unchanged core volumes required')
    outlet_ids=selections['commonOutletFaceIds'];mapped=m['old_to_new_faces'][outlet_ids]
    if not np.array_equal(faces[outlet_ids],selections['commonOutletVertexIds']) or not np.array_equal(owner[outlet_ids],selections['commonOutletOwnerCellIds']):raise ValueError('Native common face map identity')
    common={name:{'cells':len(selections[name]),'global_cell_ids_little_i8_sha256':digest(selections[name]),'volume_m3':float(v[selections[name]].sum())} for name in ['commonPressureBand','commonOutletOwners','commonTipWake']}
    for name,record in common.items():
        expected=protocol['common_observables']['fixed_cell_zones'][name]
        if record['cells']!=expected['cells'] or record['global_cell_ids_little_i8_sha256']!=expected['global_cell_ids_little_i8_sha256']:raise ValueError('Common cell IDs changed')
    _,proc_body=body(source/'constant/polyMesh/cellProc');proc=np.fromstring(proc_body,sep=' ',dtype=np.int64)
    if len(proc)!=nc or set(proc)!={0,1,2,3}:raise ValueError('Original4-rank assignment required')
    system=capsule/'configs/system';originalzones=(source/'constant/polyMesh/cellZones').read_text();seedrecords={}
    for label,extended in [('current',False),('extended',True)]:
        case=output/label;case.mkdir(parents=True,exist_ok=False);shutil.copytree(source/'constant',case/'constant',ignore=shutil.ignore_patterns('sets'))
        shutil.copytree(system,case/'system');shutil.copytree(source/'960',case/'960')
        cellproc=np.concatenate([proc,np.tile(proc[owner[outlet_ids]],50)]) if extended else proc
        listfile(case/'constant/manualCellProc','labelList',cellproc)
        (case/'system/decomposeParDict').write_text('FoamFile {version 2.0; format ascii; class dictionary; object decomposeParDict;}\nnumberOfSubdomains 4; method manual; manualCoeffs {dataFile "manualCellProc";}\n')
        control=(case/'system/controlDict').read_text().replace('endTime 960','endTime 1020').replace('writeInterval 60; purgeWrite 1;','writeInterval 20; purgeWrite 0;')
        brace=control.rfind('}');control=control[:brace]+(capsule/'configs/functionObjects.dict').read_text()+control[brace:];(case/'system/controlDict').write_text(control)
        if extended:
            write_mesh(case,m,(source/'constant/polyMesh/points').read_text());seedrecords[label]=initialize_fields(source,case,m);add_zones(case,originalzones,selections,mapped)
            np.savez_compressed(case/'private-maps.npz',old_to_new_faces=m['old_to_new_faces'],cellProc=cellproc)
        else:
            add_zones(case,originalzones,selections,outlet_ids);seedrecords[label]={name:{'source_sha256':sha(source/'960'/name),'initialized_sha256':sha(case/'960'/name),'core_values_identical':True} for name in ['U','p','k','omega','nut','phi','Uf']}
        flowprotocol=json.loads((capsule/'configs/original-protocol.json').read_text());flowprotocol.update(protocol_id='D2-V2-'+label+'-960-to1020',iterations=1020,initial_fields_sha256={str(p.relative_to(case)):sha(p) for p in sorted((case/'960').iterdir()) if p.is_file()},expected_actual_solver_iterations=list(range(961,1021)),planned_total_target=1020,planned_phase_end_iterations=[1020],checkpoint_write_interval_iterations=20,physical_validation_established=False)
        (case/'reference-protocol.json').write_text(json.dumps(flowprotocol,indent=2)+'\n')
        # Physical constants and exact fvScheme/fvSolution identities remain untouched.
        if sha(case/'system/fvSolution')!=protocol['numerics']['fvSolution_sha256'] or sha(case/'system/fvSchemes')!=protocol['numerics']['fvSchemes_sha256']:raise ValueError('Frozen physics numerics changed')
    np.savez_compressed(output/'common-selections-private.npz',**{name:selections[name] for name in selections.files})
    report={'status':'exact275mm50layer_append_prepared_requires_independent_gates','script_sha256':sha(Path(__file__)),'original_core_cells':nc,'extended_cells':len(v),'extension_m':.275,'layers':50,'added_cells':227100,'minimum_added_volume_m3':float(v[nc:].min()),'added_volume_m3':float(v[nc:].sum()),'expected_added_volume_m3':json.loads((capsule/'configs/diagnostic.json').read_text())['native_outlet']['area_m2']*.275,'maximum_core_volume_abs_difference_m3':float(np.abs(v[:nc]-selections['cellVolumes']).max()),'original_points_numerically_identical':np.array_equal(m['points'][:len(points)],points),'original_faces_vertex_ids_and_owners_identical':True,'original_internal_neighbours_identical':True,'original_cell_ids_preserved':True,'core_MPI_assignment_preserved':True,'original_MRF_zone_and_membership_preserved':True,'common_face_count':len(mapped),'common_faces_orientation_preserved':True,'common_cell_zones':common,'initial_fields':seedrecords,'mesh_sha256':{label:{name:sha(output/label/'constant/polyMesh'/name) for name in ['points','faces','owner','neighbour','boundary','cellZones','faceZones']} for label in ['current','extended']},'private_face_map_sha256':sha(output/'extended/private-maps.npz'),'wall_seconds':time.monotonic()-started,'flow_solver_launched':False,'physical_validation_established':False}
    if not np.isclose(report['added_volume_m3'],report['expected_added_volume_m3'],rtol=1e-12):raise ValueError('Analytical added prism volume disagrees')
    (output/'mesh-preparation.json').write_text(json.dumps(report,indent=2)+'\n');return report
