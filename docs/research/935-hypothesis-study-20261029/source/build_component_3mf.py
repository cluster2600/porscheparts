"""Standard 3MF composite assembly; intentional inter-component unions stay explicit."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import xml.parsers.expat
import zipfile
import numpy as np
import igl
import igl.predicates
import trimesh
from prepare_exact_union import tube
from validate_build_final import edge_checks

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('head',type=Path);p.add_argument('head_report',type=Path);p.add_argument('hypotheses',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir()
    head_report=json.loads(a.head_report.read_text());assert head_report['geometry_export_gate_passed'] and sha(a.head)==head_report['input_sha256']
    data=np.load(a.head);head_v,head_f=data['vertices'],data['triangles'];h=json.loads(a.hypotheses.read_text())
    objects=[('Reference scan envelope',head_v,head_f)];axes=defaultdict(list);supports=[]
    for x,y,lo,hi in h['support_columns']:axes[x,y].append((lo,hi))
    for (x,y),spans in axes.items():
        profiles=[];profile=None;upper=None
        for lo,hi in sorted(spans):
            if profile is not None and lo<upper:
                assert upper-1<lo<upper and hi>upper+1
                radius=1.2-.7*(lo-(upper-1));profile=profile[:-1]+[(lo,radius),(lo,1.2),(hi-1,1.2),(hi,.5)];upper=hi
            else:
                if profile is not None:profiles.append(profile)
                profile=[(lo,1.2),(hi-1,1.2),(hi,.5)];upper=hi
        profiles.append(profile)
        for profile in profiles:
            v,f=tube(x,y,profile);objects.append((f'Provisional support {len(supports)+1}',v,f));supports.append((x,y,profile[0][0],profile[-1][0]))
    cube=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    cf=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=np.int64)
    plate=cube*np.asarray(h['base_plate_mm']);objects.append(('Provisional sacrificial base',plate,cf))
    x,y,z=h['coupon_centre_mm'];v,f=tube(x,y,[(z-.5,6),(z+20,6)]);objects.append(('Provisional coupon',v,f))
    # Independent axial intersections establish positive-volume contact with the head.
    mesh=trimesh.Trimesh(head_v,head_f,process=False)
    xy=np.asarray(list(axes));origins=np.column_stack([xy,np.zeros(len(xy))]);directions=np.tile([0.,0.,1.],(len(xy),1))
    loc,ray,_=mesh.ray.intersects_location(origins,directions,multiple_hits=True);intervals={}
    for i,key in enumerate(axes):
        heights=np.sort(loc[ray==i,2]);heights=heights[np.r_[True,np.diff(heights)>1e-5]]
        assert len(heights)>0 and len(heights)%2==0
        intervals[key]=list(zip(heights[::2],heights[1::2]))
    overlap=[]
    for x,y,lo,hi in supports:
        depth=max(min(hi,top)-max(lo,bottom) for bottom,top in intervals[x,y]);assert depth>1e-6;overlap.append(float(depth))
    assert any(lo<5<hi for x,y,lo,hi in supports)
    cx,cy,cz=h['coupon_centre_mm']
    assert 0<cz-.5<5<cz+20
    assert 6<cx<h['base_plate_mm'][0]-6 and 6<cy<h['base_plate_mm'][1]-6
    print('Every support contacts the head; head, base and coupon form one connected union',flush=True)
    meta=[]
    for i,(name,v,f) in enumerate(objects,1):
        assert edge_checks(f,len(v))==(0,0,0)
        assert np.all(np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>0)
        assert np.all(igl.is_vertex_manifold(f))
        if i>1:
            found,pairs,_=igl.predicates.find_self_intersections(v,f,False);assert not found and len(pairs)==0
        q=v[f]-v[0];volume=float(np.einsum('ij,ij->',q[:,0],np.cross(q[:,1],q[:,2]))/6);assert volume>0
        meta.append({'id':i,'name':name,'vertices':len(v),'triangles':len(f),'signed_volume_mm3':volume,'vertices_sha256':hashlib.sha256(np.asarray(v,dtype='<f8').tobytes()).hexdigest(),'triangles_sha256':hashlib.sha256(np.asarray(f,dtype='<i8').tobytes()).hexdigest()})
    path=a.output/'935-supported-composite-mm.3mf'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        archive.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        with archive.open('3D/3dmodel.model','w',force_zip64=True) as out:
            def write(s):out.write(s.encode())
            write('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">935 conditional composite with provisional fixtures</metadata><metadata name="Description">Monolithic scan study. Component overlaps require union under the 3MF core specification. Manufacturing and engine qualification are false.</metadata><resources>')
            for i,(name,v,f) in enumerate(objects,1):
                write(f'<object id="{i}" type="model" name="{name}"><mesh><vertices>')
                for start in range(0,len(v),10000):write(''.join(f'<vertex x="{x:.17g}" y="{y:.17g}" z="{z:.17g}"/>' for x,y,z in v[start:start+10000]))
                write('</vertices><triangles>')
                for start in range(0,len(f),10000):write(''.join(f'<triangle v1="{x}" v2="{y}" v3="{z}"/>' for x,y,z in f[start:start+10000]))
                write('</triangles></mesh></object>')
            parent=len(objects)+1;write(f'<object id="{parent}" type="model" name="935 conditional assembled study"><components>')
            for i in range(1,parent):write(f'<component objectid="{i}"/>')
            write(f'</components></object></resources><build><item objectid="{parent}"/></build></model>')
    # Independent streamed readback checks every coordinate, face and resource reference.
    decoded={};current=None;components=[];items=[];units=[]
    def element(name,attr):
        nonlocal current
        if name=='model':units.append(attr['unit'])
        elif name=='object':current=int(attr['id']);decoded[current]={'vertices':0,'triangles':0,'vh':hashlib.sha256(),'fh':hashlib.sha256()}
        elif name=='vertex':decoded[current]['vertices']+=1;decoded[current]['vh'].update(struct.pack('<ddd',*(float(attr[k]) for k in ['x','y','z'])))
        elif name=='triangle':decoded[current]['triangles']+=1;decoded[current]['fh'].update(struct.pack('<qqq',*(int(attr[k]) for k in ['v1','v2','v3'])))
        elif name=='component':components.append((current,int(attr['objectid'])))
        elif name=='item':items.append(int(attr['objectid']))
    parser=xml.parsers.expat.ParserCreate();parser.StartElementHandler=element
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        with archive.open('3D/3dmodel.model') as stream:
            for chunk in iter(lambda:stream.read(1048576),b''):parser.Parse(chunk,False)
            parser.Parse(b'',True)
    assert units==['millimeter'] and items==[parent] and components==[(parent,i) for i in range(1,parent)]
    for row in meta:
        r=decoded[row['id']];assert r['vertices']==row['vertices'] and r['triangles']==row['triangles'] and r['vh'].hexdigest()==row['vertices_sha256'] and r['fh'].hexdigest()==row['triangles_sha256']
    report={'representation':'3MF core composite; final union is required by section 4.2 of the specification','reference_head_input_sha256':sha(a.head),'three_mf_sha256':sha(path),'mesh_resources':len(objects),'support_resources':len(supports),'all_resource_geometry_checks_passed':True,'every_coordinate_and_index_roundtrip_exact':True,'component_graph_readback_passed':True,'all_supports_have_positive_axial_overlap_with_head':True,'minimum_axial_overlap_mm':min(overlap),'one_connected_union_contact_graph':True,'intended_component_intersections':True,'single_merged_triangle_mesh':False,'machine_specific_job':False,'manufacturing_qualified':False,'engine_qualified':False,'resources':meta}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='resources'}),flush=True)
if __name__=='__main__':main()
