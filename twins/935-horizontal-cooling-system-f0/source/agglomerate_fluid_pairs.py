"""Apply exactly checked convex tetrahedral pairs as mixed polyhedral cells."""
import hashlib,importlib.util,json,re,shutil,sys,time
from pathlib import Path
import numpy as np
import reconnect_fluid_tetrahedra as base
from import_conforming_volume import integer_points,determinant

PARSER=Path(__file__).with_name('fluid-mesh-study-20261022')/'export-fluid-plc-005.py'
spec=importlib.util.spec_from_file_location('frozen_fluid_ascii',PARSER);ascii=importlib.util.module_from_spec(spec);spec.loader.exec_module(ascii)
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()

def array(path,columns,dtype=float,empty=False):
    if Path(path).stat().st_size>512*1024**2:raise ValueError('Bounded mesh file required')
    try:n,body=ascii.foam_list(path,maximum_count=10_000_000)
    except ValueError:
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',Path(path).read_text(),flags=re.S)
        if empty and re.fullmatch(r'\s*FoamFile\s*\{[^{}]*\bformat\s+ascii\s*;[^{}]*\}\s*0\s*\(\s*\)\s*',text,re.S):return np.empty((0,columns),dtype=dtype)
        raise
    value=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ',dtype=dtype)
    if value.size!=n*columns:raise ValueError('Complete native mesh array required')
    return value.reshape(n,columns)

def read_mesh(case):
    m=Path(case)/'constant/polyMesh';v=array(m/'points',3);f=array(m/'faces',4,np.int64)
    if not np.isfinite(v).all() or not np.all(f[:,0]==3) or f[:,1:].min()<0 or f[:,1:].max()>=len(v):raise ValueError('Finite indexed triangular faces required')
    o=array(m/'owner',1,np.int64).ravel();n=array(m/'neighbour',1,np.int64,empty=True).ravel()
    if len(o)!=len(f) or len(n)>len(o) or o.min()<0 or (len(n) and (n.min()<0 or np.any(o[:len(n)]>=n))):raise ValueError('Ordered valid face ownership required')
    count,body=ascii.foam_list(m/'boundary');blocks=list(re.finditer(r'([A-Za-z][A-Za-z0-9_]*)\s*\{([^{}]*)\}',body));patches=[];start=len(n);expected={'inlet':'patch','outlet':'patch','duct':'wall','rotor':'wall'}
    for x in blocks:
        name=x[1];size=int(re.search(r'\bnFaces\s+(\d+)\s*;',x[2])[1]);first=int(re.search(r'\bstartFace\s+(\d+)\s*;',x[2])[1]);kind=re.search(r'\btype\s+(\w+)\s*;',x[2])[1]
        if name not in expected or kind!=expected[name] or first!=start or size<=0:raise ValueError('Complete original named patch partition required')
        patches.append((name,kind,size,first));start+=size
    if count!=4 or len(patches)!=4 or len({p[0] for p in patches})!=4 or start!=len(f):raise ValueError('Four disjoint original patches required')
    return v,f[:,1:],o,n,patches

def tetrahedra(faces,owner,neighbour,count):
    labels=np.r_[owner,neighbour];counts=np.bincount(labels,minlength=count)
    if len(counts)!=count or np.any(counts!=4):raise ValueError('Exactly four faces per parent cell required')
    ordered=np.argsort(labels,kind='stable');f=np.concatenate([faces,faces[:len(neighbour)]],axis=0)[ordered].reshape(count,12);f.sort(axis=1);cells=f[:,::3].copy()
    if not np.array_equal(f,np.repeat(cells,3,axis=1)):raise ValueError('Four distinct parent tetrahedron vertices required')
    return cells,ordered.reshape(count,4)%len(faces)

def canonical_order(cells):
    return np.lexsort(np.sort(cells,axis=1).T[::-1])

def partition(vertices,cells,pairs):
    if pairs.ndim!=2 or pairs.shape[1]!=2 or pairs.dtype.kind not in 'iu' or not 0<len(pairs)<=4096 or pairs.min()<0 or pairs.max()>=len(cells) or len(np.unique(pairs))!=pairs.size:raise ValueError('Bounded disjoint parent pairs required')
    witnesses=[]
    for pair in pairs:
        c=cells[pair];shared=np.intersect1d(c[0],c[1])
        if len(shared)!=3 or base.convex_flip(vertices,c,shared) is None:raise ValueError('Exact convex positive parent cavity required')
        ids=np.unique(c);points,_=integer_points(vertices[ids]);lookup=dict(zip(ids,points));anchor=points[0]
        signed=lambda face:determinant(anchor,*(lookup[int(i)] for i in face))
        oriented=c[:,base.FACE_NODES].reshape(-1,3);keys=np.sort(oriented,axis=1);_,first,multiplicity=np.unique(keys,axis=0,return_index=True,return_counts=True);outer_oriented=oriented[first[multiplicity==1]]
        cones=[signed(face) for face in outer_oriented];parent=sum(determinant(*(lookup[int(i)] for i in tet)) for tet in c)
        if min(cones)<0 or sum(cones)!=parent or parent<=0:raise ValueError('Exact outward convex-cell volume partition required')
        witnesses.append(str(parent))
    return witnesses


def merged_quality(vertices,cells,outside,centres,volumes):
 p=vertices[cells];v=np.einsum('ij,ij->i',p[:,1]-p[:,0],np.cross(p[:,2]-p[:,0],p[:,3]-p[:,0]))/6
 assert np.all(v>0)
 volume=float(v.sum());centre=np.average(p.mean(axis=1),axis=0,weights=v);tensor=np.zeros((3,3));area_sum=0.;internal=0;angles=[];weights=[];ratios=[]
 for face in base.outer_faces(cells):
  neighbour=outside[tuple(face)]
  if neighbour<0:continue
  xyz=vertices[face];fc=xyz.mean(axis=0);area=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])/2;mag=np.linalg.norm(area)
  tensor+=np.outer(area,area);area_sum+=mag;internal+=1;other=centres[neighbour];delta=other-centre
  angles.append(np.degrees(np.arccos(np.clip(abs(area@delta)/(mag*np.linalg.norm(delta)),0,1))))
  d1=abs(area@(fc-centre));d2=abs(area@(other-fc));weights.append(min(d1,d2)/(d1+d2));ratios.append(min(volume,volumes[neighbour])/max(volume,volumes[neighbour]))
 average=area_sum/internal if internal else 1.;det=abs(np.linalg.det(tensor/average**2))
 violations=[np.maximum((np.array(angles)-70)/20,0),np.maximum(1-np.array(weights)/.05,0),np.maximum(1-np.array(weights)/.02,0),np.maximum(1-np.array(ratios)/.01,0),np.array([max(1-det/.001,0)])]
 return np.array([np.count_nonzero(x) for x in violations]),np.array([float(x@x) for x in violations])


def write_list(path,kind,body,count):
    with Path(path).open('x') as f:
        f.write(f'FoamFile\n{{version 2.0;format ascii;class {kind};location "constant/polyMesh";object {Path(path).name};}}\n{count}\n(\n');f.write(body);f.write(')\n')


def run(parent,native,proposal,out):
    started=time.monotonic();parent,native,proposal,out=map(Path,[parent,native,proposal,out])
    if out.exists():raise ValueError('Fresh private output required')
    proof=json.loads((parent/'assessment.json').read_text());receipt=json.loads((proposal/'receipt.json').read_text());execution=json.loads((native/'execution.json').read_text())
    if proof['volume_npz_sha256']!=sha(parent/'volume.npz') or not proof['exact_PLC_volume_equal'] or not proof['complete_boundary_coordinate_triangle_marker_bijection'] or proof['exact_cell_orientation']['negative'] or proof['exact_cell_orientation']['zero']:raise ValueError('Complete exact positive parent audit required')
    if receipt['parent_audit_sha256']!=sha(parent/'assessment.json') or receipt['proposal_sha256']!=sha(proposal/'pairs.npz') or execution['volume_audit_sha256']!=sha(parent/'assessment.json'):raise ValueError('Parent and proposal provenance mismatch')
    for name in ['constant/polyMesh/'+n for n in ['points','faces','owner','neighbour','boundary']]+['system/meshQualityDict']:
        if sha(native/name)!=execution['result_sha256'][name]:raise ValueError('Native parent mesh changed')
    z=np.load(parent/'volume.npz');vertices=z['vertices'];cells=z['tetrahedra'];pairs=np.load(proposal/'pairs.npz')['pairs']
    if not 0<len(vertices)<=1_000_000 or not 0<len(cells)<=2_000_000:raise ValueError('Bounded tetrahedral parent required')
    witnesses=partition(vertices,cells,pairs)
    v,f,o,n,patches=read_mesh(native);ni=len(n);nc=len(cells)
    if not np.array_equal(v,vertices):raise ValueError('All parent native coordinates must match the audit')
    native_cells,native_faces=tetrahedra(f,o,n,nc);a=canonical_order(cells);b=canonical_order(native_cells)
    if not np.array_equal(np.sort(cells[a],axis=1),native_cells[b]):raise ValueError('Complete native tetrahedral connectivity mismatch')
    parent_to_native=np.empty(nc,dtype=np.int64);parent_to_native[a]=b
    markers={'inlet':1,'outlet':2,'duct':3,'rotor':4};tags=np.concatenate([np.full(size,markers[name]) for name,_,size,_ in patches]);actual=np.column_stack([np.sort(f[ni:],axis=1),tags]);expected=np.column_stack([np.sort(z['boundary'],axis=1),z['markers']]);order=lambda x:np.lexsort(x.T[::-1])
    if not np.array_equal(actual[order(actual)],expected[order(expected)]):raise ValueError('Complete parent boundary/marker bijection mismatch')
    xyz=vertices[cells];centres=xyz.mean(axis=1);volumes=np.einsum('ij,ij->i',xyz[:,1]-xyz[:,0],np.cross(xyz[:,2]-xyz[:,0],xyz[:,3]-xyz[:,0]))/6
    native_to_parent=np.empty(nc,dtype=np.int64);native_to_parent[parent_to_native]=np.arange(nc);metric_proofs=[];reserved=set()
    for pair in pairs:
        local_faces=np.unique(native_faces[parent_to_native[pair]]);outside={};region=set(map(int,pair))
        for fid in local_faces:
            neighbours=[int(native_to_parent[o[fid]])]
            if fid<ni:neighbours.append(int(native_to_parent[n[fid]]))
            other=set(neighbours)-set(map(int,pair));region.update(other)
            if len(other)==0 and len(neighbours)==2:continue
            outside[tuple(sorted(map(int,f[fid])))]=other.pop() if other else -1
        if reserved.intersection(region):raise ValueError('Disjoint affected cell neighbourhoods required')
        before=base.patch_quality(vertices,cells[pair],outside,centres,volumes);after=merged_quality(vertices,cells[pair],outside,centres,volumes)
        if not base.improves(before,after):raise ValueError('Independent local finite-volume improvement required')
        reserved.update(region);metric_proofs.append({'before_counts':before[0].tolist(),'after_counts':after[0].tolist(),'before_severity':before[1].tolist(),'after_severity':after[1].tolist()})
    root=np.arange(nc);mapped_pairs=parent_to_native[pairs];root[mapped_pairs.max(axis=1)]=mapped_pairs.min(axis=1);_,old_to_new=np.unique(root,return_inverse=True);parent_to_new=old_to_new[parent_to_native]
    own=old_to_new[o];neigh=old_to_new[n];keep=own[:ni]!=neigh
    if np.count_nonzero(~keep)!=len(pairs):raise ValueError('Exactly one shared internal face per pair required')
    source=np.r_[np.flatnonzero(keep),np.arange(ni,len(f))];reverse=np.zeros(len(source),dtype=bool);reverse[:keep.sum()]=own[:ni][keep]>neigh[keep]
    faces=f[source].copy();faces[reverse]=faces[reverse,::-1];new_o=own[source].copy();new_n=neigh[keep].copy();swap=reverse[:len(new_n)];new_o[:len(new_n)][swap],new_n[swap]=new_n[swap].copy(),new_o[:len(new_n)][swap].copy()
    sorting=np.r_[np.lexsort((new_n,new_o[:len(new_n)])),np.arange(len(new_n),len(faces))];faces=faces[sorting];new_o=new_o[sorting];new_n=new_n[sorting[:len(new_n)]];source=source[sorting];reverse=reverse[sorting]
    if not np.array_equal(faces[len(new_n):],f[ni:]) or np.any(reverse[len(new_n):]) or len(np.unique(parent_to_new))!=nc-len(pairs):raise ValueError('Complete cell partition and unchanged boundary required')
    out.mkdir(mode=0o700);mesh=out/'constant/polyMesh';mesh.mkdir(parents=True);shutil.copyfile(native/'constant/polyMesh/points',mesh/'points');shutil.copytree(native/'system',out/'system')
    for name,values,kind,fmt in [('faces',faces,'faceList','3(%d %d %d)'),('owner',new_o,'labelList','%d'),('neighbour',new_n,'labelList','%d')]:
        with (mesh/name).open('x') as stream:
            stream.write(f'FoamFile\n{{version 2.0;format ascii;class {kind};location "constant/polyMesh";object {name};}}\n{len(values)}\n(\n');np.savetxt(stream,values,fmt=fmt);stream.write(')\n')
    blocks=''.join(f'{name}\n{{type {kind};nFaces {size};startFace {first-ni+len(new_n)};}}\n' for name,kind,size,first in patches);write_list(mesh/'boundary','polyBoundaryMesh',blocks,4)
    np.savez_compressed(out/'agglomeration.npz',pairs=pairs,parent_to_native=parent_to_native,parent_to_new=parent_to_new,face_parent=source,face_reversed=reverse)
    r={'status':'mixed_mesh_pending_independent_and_native_audits','source_sha256':sha(__file__),'helper_sha256':{'reconnect_fluid_tetrahedra.py':sha(base.__file__),'import_conforming_volume.py':sha(sys.modules['import_conforming_volume'].__file__)},'local_metric_proofs':metric_proofs,'parser_sha256':sha(PARSER),'parent_audit_sha256':sha(parent/'assessment.json'),'parent_native_execution_sha256':sha(native/'execution.json'),'proposal_receipt_sha256':sha(proposal/'receipt.json'),'agglomeration_sha256':sha(out/'agglomeration.npz'),'vertices':len(v),'parent_tetrahedra':nc,'cells':nc-len(pairs),'merged_polyhedral_cells':len(pairs),'boundary_triangles':len(f)-ni,'native_parent_cell_order_matches_audit':bool(np.array_equal(parent_to_native,np.arange(nc))),'exact_convex_cell_volume_witnesses':witnesses,'points_file_byte_identical':sha(mesh/'points')==sha(native/'constant/polyMesh/points'),'original_quality_dictionary_unchanged':sha(out/'system/meshQualityDict')==sha(native/'system/meshQualityDict'),'mesh_file_sha256':{name:sha(mesh/name) for name in ['points','faces','owner','neighbour','boundary']},'CFD_accepted':False,'manufacturing_authorized':False,'elapsed_s':time.monotonic()-started}
    (out/'agglomeration.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)


if __name__=='__main__':run(*sys.argv[1:])
