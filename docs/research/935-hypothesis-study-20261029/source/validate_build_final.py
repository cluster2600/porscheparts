"""Independent triangle/topology checks and streamed millimetre 3MF export."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import struct
import time
import zipfile
import xml.parsers.expat
import igl
import igl.predicates
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def load_stl(path):
    with path.open('rb') as source:source.seek(80);count=struct.unpack('<I',source.read(4))[0]
    assert path.stat().st_size==84+count*50
    dtype=np.dtype([('normal','<f4',(3,)),('triangle','<f4',(3,3)),('attribute','<u2')])
    data=np.memmap(path,dtype=dtype,mode='r',offset=84,shape=(count,))
    triangles=np.asarray(data['triangle']).copy();assert np.isfinite(triangles).all()
    vertices,indices=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
    return vertices.astype(np.float64),indices.reshape(-1,3)

def classify_shells(v,f,vertex_labels):
    face_labels=vertex_labels[f[:,0]];rows=[]
    for label in np.unique(face_labels):
        faces=f[face_labels==label];origin=v[faces[0,0]]
        total=0.
        for begin in range(0,len(faces),300000):
            q=v[faces[begin:begin+300000]]-origin
            total+=np.einsum('ij,ij->',q[:,0],np.cross(q[:,1],q[:,2]))/6
        rows.append({'label':int(label),'triangles':len(faces),'signed_volume_mm3':float(total),'representative_face':faces[0].tolist()})
    positive=[r for r in rows if r['signed_volume_mm3']>0];negative=[r for r in rows if r['signed_volume_mm3']<0]
    contained=False;winding=[]
    if len(positive)==1 and len(positive)+len(negative)==len(rows):
        if negative:
            points=np.array([v[r['representative_face']].mean(axis=0) for r in negative])
            winding=np.atleast_1d(igl.winding_number(v,f[face_labels==positive[0]['label']],points)).tolist()
            contained=all(abs(w-1)<1e-5 for w in winding)
        else:contained=True
    return {'positive_shells':len(positive),'negative_cavity_shells':len(negative),'cavity_winding_inside_outer_shell':winding,'one_material_body':contained,'signed_shell_volumes_mm3':[r['signed_volume_mm3'] for r in rows]}

def shell_controls():
    cube=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=np.int64)
    labels=np.r_[np.zeros(8,dtype=int),np.ones(8,dtype=int)]
    hollow=classify_shells(np.vstack([cube*2,cube+.5]),np.vstack([faces,faces[:,::-1]+8]),labels)
    assert hollow['one_material_body'] and abs(sum(hollow['signed_shell_volumes_mm3'])-7)<1e-10
    separate=classify_shells(np.vstack([cube*2,cube+3]),np.vstack([faces,faces+8]),labels)
    assert not separate['one_material_body']
    outside=classify_shells(np.vstack([cube*2,cube+3]),np.vstack([faces,faces[:,::-1]+8]),labels)
    assert not outside['one_material_body']

def write_3mf(path,v,f):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        with z.open('3D/3dmodel.model','w',force_zip64=True) as stream:
            stream.write(b'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">935 conditional study - NOT ENGINE QUALIFIED</metadata><resources><object id="1" type="model"><mesh><vertices>')
            for block in range(0,len(v),10000):
                stream.write(''.join(f'<vertex x="{q[0]:.17g}" y="{q[1]:.17g}" z="{q[2]:.17g}"/>' for q in v[block:block+10000]).encode())
            stream.write(b'</vertices><triangles>')
            for block in range(0,len(f),10000):
                stream.write(''.join(f'<triangle v1="{q[0]}" v2="{q[1]}" v3="{q[2]}"/>' for q in f[block:block+10000]).encode())
            stream.write(b'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
    vertex_hash=hashlib.sha256();face_hash=hashlib.sha256();counts=[0,0];units=[]
    def element(name,attributes):
        if name=='model':units.append(attributes['unit'])
        elif name=='vertex':
            vertex_hash.update(struct.pack('<ddd',*(float(attributes[k]) for k in ['x','y','z'])));counts[0]+=1
        elif name=='triangle':
            face_hash.update(struct.pack('<qqq',*(int(attributes[k]) for k in ['v1','v2','v3'])));counts[1]+=1
    parser=xml.parsers.expat.ParserCreate();parser.StartElementHandler=element
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        with z.open('3D/3dmodel.model') as source:
            for block in iter(lambda:source.read(1024*1024),b''):parser.Parse(block,False)
            parser.Parse(b'',True)
    assert units==['millimeter'] and counts==[len(v),len(f)]
    assert vertex_hash.hexdigest()==hashlib.sha256(np.asarray(v,dtype='<f8').tobytes()).hexdigest()
    assert face_hash.hexdigest()==hashlib.sha256(np.asarray(f,dtype='<i8').tobytes()).hexdigest()

def edge_checks(f,nvertices):
    directed=f[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
    low=np.min(directed,axis=1);high=np.max(directed,axis=1)
    codes=2*(low*nvertices+high)+(directed[:,0]<directed[:,1])
    del directed,low,high
    codes.sort();keys=codes//2
    boundaries=np.r_[0,np.flatnonzero(keys[1:]!=keys[:-1])+1,len(keys)]
    counts=np.diff(boundaries)
    opened=int((counts==1).sum());nonmanifold=int((counts>2).sum())
    mismatches=int(np.count_nonzero(codes[1::2]-codes[::2]!=1)) if np.all(counts==2) else None
    return opened,nonmanifold,mismatches

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir()
    begin=time.monotonic()
    if a.input.suffix=='.npz':
        data=np.load(a.input);v=data['vertices'].astype(float);f=data['triangles'].astype(np.int64)
        assert np.isfinite(v).all() and f.min()>=0 and f.max()<len(v)
    else:v,f=load_stl(a.input)
    print('Indexed mesh',len(v),len(f),flush=True)
    cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    degenerate=int((~np.any(cross!=0,axis=1)).sum());volume=float(np.einsum('ij,ij->',v[f[:,0]],cross)/6)
    del cross;gc.collect()
    tetra=np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]],dtype=np.int64)
    assert edge_checks(tetra,4)==(0,0,0)
    tetra[0]=tetra[0,::-1];assert edge_checks(tetra,4)==(0,0,3)
    opened,nonmanifold,winding_errors=edge_checks(f,len(v))
    gc.collect();print('Edge checks',opened,nonmanifold,degenerate,winding_errors,flush=True)
    graph=coo_matrix((np.ones(2*len(f),dtype=bool),(f[:,[0,1]].ravel(),f[:,[1,2]].ravel())),shape=(len(v),len(v))).tocsr()
    n,labels=connected_components(graph,directed=False);sizes=np.bincount(labels[f[:,0]])
    del graph;gc.collect();print('Components',n,flush=True)
    report={'input_sha256':digest(a.input),'vertices':len(v),'triangles':len(f),'zero_area_triangles':degenerate,'open_edges':opened,'nonmanifold_edges':nonmanifold,'connected_components':int(n),'component_face_counts_descending':np.sort(sizes)[::-1][:20].tolist(),'signed_volume_mm3':volume,'bounds_mm':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],'manufacturing_qualified':False,'engine_qualified':False}
    report['inconsistently_oriented_edges']=winding_errors
    report['edge_orientation_controls_passed']=True
    np.savez_compressed(a.output/'indexed.npz',vertices=v,triangles=f)
    if not(degenerate or opened or nonmanifold):
        shell_controls();report['shell_classification_controls_passed']=True
        report['vertex_manifold']=bool(np.all(igl.is_vertex_manifold(f)))
        control_v=np.array([[-1,-1,0],[1,-1,0],[0,1,0],[0,-.5,-1],[0,-.5,1],[0,.5,0]],float);control_f=np.array([[0,1,2],[3,4,5]],dtype=np.int64)
        positive=igl.predicates.find_self_intersections(control_v,control_f,False)
        control_v[3:]+=10;negative=igl.predicates.find_self_intersections(control_v,control_f,False)
        assert bool(positive[0]) and not bool(negative[0])
        found,pairs,coplanar=igl.predicates.find_self_intersections(np.ascontiguousarray(v),np.ascontiguousarray(f),False)
        assert bool(found)==bool(len(pairs))
        np.save(a.output/'intersection-pairs.npy',pairs)
        report['intersection_pairs']=len(pairs);report['intersection_controls_passed']=True
        if len(pairs)==0:report['solid_shell_classification']=classify_shells(v,f,labels)
    report['geometry_export_gate_passed']=not(degenerate or opened or nonmanifold) and winding_errors==0 and volume>0 and report.get('intersection_pairs')==0 and report.get('vertex_manifold',False) and report.get('solid_shell_classification',{}).get('one_material_body',False)
    if report['geometry_export_gate_passed']:
        write_3mf(a.output/'935-conditional-study-mm.3mf',v,f)
        report['three_mf_sha256']=digest(a.output/'935-conditional-study-mm.3mf')
        report['three_mf_all_coordinates_and_indices_roundtrip_exact']=True
    report['elapsed_seconds']=time.monotonic()-begin
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
