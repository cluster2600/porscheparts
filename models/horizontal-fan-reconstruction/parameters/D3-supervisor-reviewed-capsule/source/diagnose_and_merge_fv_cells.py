#!/usr/bin/env python3
"""Diagnose the exact rejected cells and conservatively merge convex neighbors.

This private finite-volume experiment changes cell topology only. Points and all
physical boundary triangles are retained. It still requires independent QA.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def body(path):
    text=path.read_text();match=re.search(r'(?m)^\s*(\d+)\s*\n\(\s*\n',text)
    if not match:raise ValueError('Expected ASCII OpenFOAM list '+str(path))
    count=int(match[1]);end=text.find('\n)',match.end())
    if end<0:raise ValueError('Unclosed list '+str(path))
    return count,text[match.end():end]


def read(case):
    import numpy as np
    root=case/'constant/polyMesh';n,data=body(root/'points')
    points=np.array([[float(x) for x in line.strip('() ').split()] for line in data.splitlines() if line.strip()])
    if points.shape!=(n,3):raise ValueError('Invalid points')
    n,data=body(root/'faces');faces=[]
    for line in data.splitlines():
        if line.strip():
            m=re.fullmatch(r'\s*(\d+)\(([^()]*)\)\s*',line)
            row=list(map(int,m[2].split()))
            if int(m[1])!=len(row) or len(row)!=3:raise ValueError('Original triangular faces required')
            faces.append(row)
    if len(faces)!=n:raise ValueError('Invalid face count')
    n,data=body(root/'owner');owner=np.array(list(map(int,data.split())),dtype=int)
    if len(owner)!=n or n!=len(faces):raise ValueError('Invalid owner')
    n,data=body(root/'neighbour');neighbor=np.array(list(map(int,data.split())),dtype=int)
    if len(neighbor)!=n:raise ValueError('Invalid neighbors')
    patches=[]
    for match in re.finditer(r'(\w+)\s*\{([^{}]*)\}',(root/'boundary').read_text()):
        text=match[2];nf=re.search(r'\bnFaces\s+(\d+)',text);start=re.search(r'\bstartFace\s+(\d+)',text);typ=re.search(r'\btype\s+(\w+)',text)
        if nf and start:patches.append({'name':match[1],'nFaces':int(nf[1]),'startFace':int(start[1]),'type':typ[1]})
    if {p['name'] for p in patches}!={'rotor','shroud','inlet','outlet'}:raise ValueError('Unexpected patches')
    return points,np.array(faces,dtype=int),owner,neighbor,patches


def experiment(source,output,*,diagnose_only=False):
    import numpy as np
    points,faces,owner,neighbor,patches=read(source);ni=len(neighbor);nc=int(max(owner.max(),neighbor.max()))+1
    cf=[[] for _ in range(nc)]
    for i,c in enumerate(owner):cf[int(c)].append(i)
    for i,c in enumerate(neighbor):cf[int(c)].append(i)
    tri=points[faces];area=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*.5
    centers=[];volumes=[];cell_nodes=[]
    for ids in cf:
        nodes=sorted({int(n) for face in ids for n in faces[face]})
        if len(nodes)!=4 or len(ids)!=4:raise ValueError('Input must contain only tetrahedra')
        xyz=points[nodes];centers.append(xyz.mean(axis=0));cell_nodes.append(nodes)
        volumes.append(abs(float(np.linalg.det((xyz[1:]-xyz[0]).T)))/6)
    centers=np.asarray(centers);volumes=np.asarray(volumes)
    def determinant(ids):
        vectors=area[[i for i in ids if i<ni]]
        if not len(vectors):return 0.
        normalized=vectors/np.linalg.norm(vectors,axis=1).mean()
        return abs(float(np.linalg.det(normalized.T@normalized)))
    det=np.array([determinant(ids) for ids in cf]);bad=np.flatnonzero(det<.001)
    expected_count,setbody=body(source/'constant/polyMesh/sets/underdeterminedCells');expected=set(map(int,setbody.split()))
    if len(expected)!=expected_count or set(bad)!=expected:raise ValueError('Independent OpenFOAM rejected-cell set does not match diagnostic')
    patch_by_face={i:p['name'] for p in patches for i in range(p['startFace'],p['startFace']+p['nFaces'])}
    rows=[]
    for c in bad:
        rows.append({'cell':int(c),'center_mm':(centers[c]*1000).tolist(),'radial_position_mm':float(np.linalg.norm(centers[c,:2])*1000),
                     'determinant_reproduced':float(det[c]),'boundary_faces':[{'face':i,'patch':patch_by_face[i]} for i in cf[c] if i>=ni],
                     'volume_mm3':float(volumes[c]*1e9),'vertices_mm':(points[cell_nodes[c]]*1000).tolist()})
    output.mkdir(parents=True,exist_ok=False)
    report={'status':'exact_rejected_cells_diagnosed','source_case':source.name,'cell_count_before':nc,
            'bad_cells':rows,'minimum_determinant_reproduced':float(det.min()),'threshold_unchanged':.001,
            'method_reference':'OpenFOAM-13 primitiveMeshCheck.C cellDeterminant: internal-face area dyadic tensor normalized by average internal-face area',
            'method_url':'https://github.com/OpenFOAM/OpenFOAM-13/blob/master/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C',
            'source_mesh_sha256':{name:hashlib.sha256((source/'constant/polyMesh'/name).read_bytes()).hexdigest() for name in ['points','faces','owner','neighbour','boundary']},
            'flow_solver_launched':False,'physical_validation_established':False}
    if diagnose_only:
        (output/'localized-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
    taken=set();merges=[];failed=[];attempts=[]
    def outer_faces(group):
        return sorted(f for c in group for f in cf[c]
                      if f>=ni or not (int(owner[f]) in group and int(neighbor[f]) in group))
    def convex_closure(group):
        group=set(group)
        while True:
            ids=outer_faces(group)
            nodes=sorted({n for c in group for n in cell_nodes[c]});xyz=points[nodes]
            additions=set()
            for f in ids:
                outward=area[f] if int(owner[f]) in group else -area[f]
                if float(((xyz-tri[f].mean(axis=0))@outward).max())>np.linalg.norm(outward)*1e-10:
                    if f>=ni:return None,'boundary_nonconvex'
                    additions.add(int(neighbor[f] if int(owner[f]) in group else owner[f]))
            if not additions:return group,None
            if additions & taken:return None,'used_neighbor'
            group.update(additions)
            if len(group)>16:return None,'closure_exceeds_16_cells'
    boundary_nodes=set(faces[ni:].ravel())
    for c in sorted(bad,key=lambda i:(sum(n not in boundary_nodes for n in cell_nodes[i]),det[i])):
        if int(c) in taken:continue
        candidates=[]
        for face in cf[c]:
            if face>=ni:continue
            nbr=int(neighbor[face] if owner[face]==c else owner[face])
            if nbr in taken:continue
            group,reason=convex_closure({int(c),nbr})
            if group is None:
                attempts.append({'cell':int(c),'neighbor':nbr,'rejected':reason});continue
            ids=outer_faces(group);value=determinant(ids)
            if value<.005:
                attempts.append({'cell':int(c),'neighbor':nbr,'rejected':'determinant_margin','determinant':value});continue
            union_volume=float(volumes[list(group)].sum())
            center=(volumes[list(group),None]*centers[list(group)]).sum(axis=0)/union_volume
            weights=[];ratios=[];angles=[]
            for f in ids:
                if f>=ni:continue
                other=int(neighbor[f] if int(owner[f]) in group else owner[f])
                fc=tri[f].mean(axis=0);d=centers[other]-center
                down=abs(float(area[f]@(fc-center)));dnei=abs(float(area[f]@(centers[other]-fc)))
                weights.append(min(down,dnei)/(down+dnei))
                ratios.append(min(union_volume,volumes[other])/max(union_volume,volumes[other]))
                outward=area[f] if int(owner[f]) in group else -area[f]
                cosine=float(outward@d)/(np.linalg.norm(outward)*np.linalg.norm(d))
                angles.append(float(np.degrees(np.arccos(np.clip(cosine,-1,1)))))
            if min(weights)<.055 or min(ratios)<.015 or max(angles)>80:
                attempts.append({'cell':int(c),'neighbor':nbr,'rejected':'adjacent_face_margin','weight':min(weights),'volume_ratio':min(ratios),'nonorthogonality':max(angles),'group':sorted(group)});continue
            candidates.append((-len(group & expected),len(group),-value,group,center,union_volume,min(weights),min(ratios),max(angles)))
        if not candidates:failed.append(int(c));continue
        best=min(candidates,key=lambda row:row[:3]);_,_,negvalue,group,center,volume,weight,ratio,angle=best
        taken.update(group)
        removed=sorted({f for cell in group for f in cf[cell] if f<ni and int(owner[f]) in group and int(neighbor[f]) in group})
        merges.append({'bad_cell':int(c),'member_cells':sorted(group),'removed_internal_faces':removed,
                  'predicted_union_determinant':-negvalue,'predicted_min_adjacent_weight':weight,'predicted_min_adjacent_volume_ratio':ratio,
                  'predicted_max_adjacent_nonorthogonality_deg':angle,'convex_union_checked':True,'center_m':center.tolist(),'volume_m3':float(volume)})
    # A rejected seed may subsequently be included in another admissible cavity.
    failed=[c for c in failed if c not in taken]
    report.update({'candidate_rejections':attempts,'merges':merges,'unresolved_bad_cells':failed,'geometry_policy':'No point or boundary triangle changed; disjoint convex local unions with at most 16 original tetrahedra',
                   'acceptance':'Independent standard/extended OpenFOAM checks still required; no threshold change'})
    (output/'localized-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
    if failed:raise ValueError('No admissible local convex union for '+str(failed))
    representative=np.arange(nc)
    for pair in merges:
        group=pair['member_cells'];representative[group]=min(group)
    unique=sorted(set(representative));mapping={old:new for new,old in enumerate(unique)}
    labels=np.array([mapping[int(x)] for x in representative]);removed={f for m in merges for f in m['removed_internal_faces']}
    internal=[]
    for f in range(ni):
        if f in removed:continue
        own,nei=int(labels[owner[f]]),int(labels[neighbor[f]]);nodes=list(map(int,faces[f]))
        if own==nei:raise ValueError('Unaccounted collapsed internal face')
        if own>nei:own,nei=nei,own;nodes.reverse()
        internal.append((own,nei,nodes))
    internal.sort(key=lambda item:(item[0],item[1]))
    mesh=output/'constant/polyMesh';shutil.copytree(source/'constant/polyMesh',mesh,ignore=shutil.ignore_patterns('sets','cellZones','faceZones','pointZones'))
    # Preserve all boundary faces in the original patch order and exact point IDs.
    all_faces=[row[2] for row in internal]+faces[ni:].tolist()
    all_owner=[row[0] for row in internal]+[int(labels[c]) for c in owner[ni:]]
    def write_list(name,cls,values):
        (mesh/name).write_text('FoamFile {version 2.0; format ascii; class '+cls+'; object '+name+';}\n'+str(len(values))+'\n(\n'+'\n'.join(values)+'\n)\n')
    write_list('faces','faceList',[str(len(row))+'('+ ' '.join(map(str,row))+')' for row in all_faces])
    write_list('owner','labelList',[str(n) for n in all_owner]);write_list('neighbour','labelList',[str(row[1]) for row in internal])
    text='FoamFile {version 2.0; format ascii; class polyBoundaryMesh; object boundary;}\n'+str(len(patches))+'\n(\n'
    for p in patches:
        text+=p['name']+'\n{type '+p['type']+'; nFaces '+str(p['nFaces'])+'; startFace '+str(p['startFace']-len(removed))+';}\n'
    (mesh/'boundary').write_text(text+')\n')
    cells=' '.join(map(str,range(len(unique))))
    (mesh/'cellZones').write_text('FoamFile {version 2.0; format ascii; class regIOobject; object cellZones;}\n1\n(\nFLUID {type cellZone; cellLabels List<label>\n'+str(len(unique))+'\n('+cells+');}\n)\n')
    for folder in ['0','system','constant']:
        if folder=='constant':
            for p in (source/folder).iterdir():
                if p.is_file():shutil.copyfile(p,output/folder/p.name)
        else:shutil.copytree(source/folder,output/folder,dirs_exist_ok=True)
    shutil.copyfile(source/'preparation.json',output/'preparation.json')
    postpoints,postfaces,_,_,postpatches=read(output)
    if not np.array_equal(postpoints,points) or not np.array_equal(postfaces[len(internal):],faces[ni:]):raise ValueError('Boundary geometry changed')
    report.update({'status':'targeted_convex_unions_require_independent_QA','cell_count_after':len(unique),
                   'point_file_byte_identical':(mesh/'points').read_bytes()==(source/'constant/polyMesh/points').read_bytes(),
                   'all_boundary_face_point_ids_and_order_identical':True,'all_patch_face_counts_identical':[(p['name'],p['nFaces']) for p in postpatches]==[(p['name'],p['nFaces']) for p in patches],
                   'CAD_and_physical_surface_geometry_changed':False,'surface_geometry_deviation_m':0,
                   'output_mesh_sha256':{name:hashlib.sha256((mesh/name).read_bytes()).hexdigest() for name in ['points','faces','owner','neighbour','boundary','cellZones']}})
    (output/'localized-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['bad_cells','source_mesh_sha256','output_mesh_sha256']}));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--diagnose-only',action='store_true')
    a=p.parse_args();experiment(a.source,a.output,diagnose_only=a.diagnose_only)
