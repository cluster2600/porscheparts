"""Independent triangle-solid union and exact-coordinate 3MF roundtrip study."""
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
import zipfile
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    spec=importlib.util.spec_from_file_location('_mesh_union_helpers',Path(__file__).with_name('point_radius_trial.py'))
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    require,write,sha=h.require,h.write,h.sha
    require(not out.exists(),'Fresh output required');out.mkdir(parents=True)
    report=dict(status='incomplete',candidate_adopted=False,
                scope='Triangle-solid operator only; the failed native BREP retention gates remain unchanged',
                thread_scope='One worker process; OCCT and BLAS use one thread. Manifold internal thread count is not attested.')
    start=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second inner limit')))
    signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    try:
        p=json.loads((root/'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-law-API-observer-preparation-001/plan.json').read_text())
        sys.path.insert(0,str(root/p['native_site']))
        import numpy as np
        import manifold3d as m
        from importlib import metadata as package_metadata
        from build123d import import_brep,export_stl
        from OCP.OSD import OSD_ThreadPool
        OSD_ThreadPool.DefaultPool_s().Init(1)
        report['versions']={name:package_metadata.version(name) for name in ['manifold3d','numpy','build123d']}
        baseline=root/'parts/993-eng-carrier-0001/source/design-20261016/corner-slide-candidate-20261018/candidate-surface.stl'
        require(sha(baseline)=='b4026f66dc77b8022e82c358553e8e93ce0cbc2ea0fd31da19ac39a9f891a803','Current STL differs')
        report['inputs']={str(baseline.relative_to(root)):sha(baseline)}

        def from_stl(path):
            raw=path.read_bytes();count=int.from_bytes(raw[80:84],'little')
            require(len(raw)==84+50*count,'Only the retained binary STL layout is accepted')
            dtype=np.dtype([('normal','<f4',(3,)),('xyz','<f4',(3,3)),('attribute','<u2')])
            triangles=np.frombuffer(raw,offset=84,count=count,dtype=dtype)['xyz'].astype(np.float64)
            vertices,inverse=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
            faces=inverse.reshape(-1,3).astype(np.uint64)
            mesh=m.Mesh64(np.ascontiguousarray(vertices),np.ascontiguousarray(faces))
            solid=m.Manifold(mesh)
            row=dict(path=str(path.relative_to(root)),sha256=sha(path),STL_triangles=count,exact_coordinate_unique_vertices=len(vertices),status=str(solid.status()),native_triangles=solid.num_tri(),volume_mm3=solid.volume(),vertex_weld_tolerance_used=False)
            require(solid.status()==m.Error.NoError and not solid.is_empty(),'Input is not an oriented Manifold: '+str(row))
            return solid,row

        parent,parent_row=from_stl(baseline);report['parent']=parent_row;tools=[];report['patches']=[]
        for i in range(2):
            path=root/f'work/carrier-resume-20261020/nurbs-root-patch-001/output/patch-{i}.brep'
            report['inputs'][str(path.relative_to(root))]=sha(path)
            exported=out/f'patch-{i}.stl'
            export_stl(import_brep(path),exported,tolerance=.06,angular_tolerance=.1,ascii_format=False)
            tool,row=from_stl(exported);tools.append(tool);report['patches'].append(row)
            write(out/'progress.json',report)
        candidate=m.Manifold.batch_boolean([parent,*tools],m.OpType.Add)
        require(candidate.status()==m.Error.NoError and not candidate.is_empty(),'Mesh union failed')
        removed=m.Manifold.batch_boolean([parent,candidate],m.OpType.Subtract)
        added=m.Manifold.batch_boolean([candidate,parent],m.OpType.Subtract)
        report['candidate']=dict(status=str(candidate.status()),triangles=candidate.num_tri(),vertices=candidate.num_vert(),volume_mm3=candidate.volume(),mass_kg=candidate.volume()*4420e-9,removed_status=str(removed.status()),removed_empty=removed.is_empty(),removed_triangles=removed.num_tri(),removed_volume_mm3=removed.volume(),added_status=str(added.status()),added_empty=added.is_empty(),added_volume_mm3=added.volume())
        write(out/'progress.json',report)
        mesh=candidate.to_mesh64();vertices=np.asarray(mesh.vert_properties)[:,:3];faces=np.asarray(mesh.tri_verts)
        np.savez_compressed(out/'candidate-mesh64.npz',vertices=vertices,triangles=faces)
        namespace='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        ET.register_namespace('',namespace)
        model=ET.Element('{'+namespace+'}model',unit='millimeter',attrib={'{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
        resources=ET.SubElement(model,'{'+namespace+'}resources');obj=ET.SubElement(resources,'{'+namespace+'}object',id='1',type='model',name='Unqualified 993 carrier NURBS mesh-union study')
        xml_mesh=ET.SubElement(obj,'{'+namespace+'}mesh');xml_vertices=ET.SubElement(xml_mesh,'{'+namespace+'}vertices')
        for x,y,z in vertices:ET.SubElement(xml_vertices,'{'+namespace+'}vertex',x=repr(float(x)),y=repr(float(y)),z=repr(float(z)))
        xml_triangles=ET.SubElement(xml_mesh,'{'+namespace+'}triangles')
        for a,b,c in faces:ET.SubElement(xml_triangles,'{'+namespace+'}triangle',v1=str(int(a)),v2=str(int(b)),v3=str(int(c)))
        build=ET.SubElement(model,'{'+namespace+'}build');ET.SubElement(build,'{'+namespace+'}item',objectid='1')
        archive=out/'candidate-study.3mf'
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
            z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/></Relationships>')
            z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
        del model,resources,obj,xml_mesh,xml_vertices,xml_triangles,build
        with zipfile.ZipFile(archive) as z:parsed=ET.fromstring(z.read('3D/3dmodel.model'))
        restored_v=np.asarray([[float(row.get(c)) for c in ['x','y','z']]for row in parsed.findall('.//{'+namespace+'}vertex')],dtype=np.float64)
        restored_f=np.asarray([[int(row.get(c)) for c in ['v1','v2','v3']]for row in parsed.findall('.//{'+namespace+'}triangle')],dtype=np.uint64)
        require(vertices.tobytes()==restored_v.tobytes() and np.array_equal(faces,restored_f),'3MF coordinates or faces changed')
        restored=m.Manifold(m.Mesh64(restored_v,restored_f))
        restored_removed=m.Manifold.batch_boolean([parent,restored],m.OpType.Subtract)
        report['roundtrip']=dict(vertex_binary64_bytes_equal=True,triangle_indices_equal=True,status=str(restored.status()),original_minus_restored_empty=restored_removed.is_empty(),original_minus_restored_status=str(restored_removed.status()),archive_sha256=sha(archive))
        report['checks']=dict(candidate_NoError=candidate.status()==m.Error.NoError,triangle_solid_material_retention=removed.status()==m.Error.NoError and removed.is_empty(),positive_addition=added.status()==m.Error.NoError and not added.is_empty() and added.volume()>0,mass_below_1_30_kg=0<report['candidate']['mass_kg']<=1.3,restored_NoError=restored.status()==m.Error.NoError,restored_material_retention=restored_removed.status()==m.Error.NoError and restored_removed.is_empty())
        report['status']='triangle_solid_and_3MF_screens_passed' if all(report['checks'].values()) else 'triangle_solid_or_3MF_screen_refused'
        report['pending']=['independent whole-surface topology/intersection audit','protected study interfaces','fresh volume mesh and mechanics','complete additive process preparation']
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;write(out/'assessment.json',report)
    print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out/'assessment.json'))))
    return 0 if report['status'] in ['triangle_solid_and_3MF_screens_passed','triangle_solid_or_3MF_screen_refused'] else 1


if __name__=='__main__':raise SystemExit(main())
