"""One 3MF build item retaining the entire parent mesh as an unchanged component."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    spec=importlib.util.spec_from_file_location('_component_helpers',Path(__file__).with_name('point_radius_trial.py'))
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    require,write,sha=h.require,h.write,h.sha
    require(not out.exists(),'Fresh output required');out.mkdir(parents=True)
    start=time.monotonic();report=dict(status='incomplete',candidate_adopted=False,components=[],
        scope='Additive component assembly, not acceptance of the refused BREP or Manifold Boolean results',
        assembly_semantics='Positive source solids in one 3MF components object; downstream consumers must unite their final shape')
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second inner limit')))
    signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    try:
        p=json.loads((root/'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-law-API-observer-preparation-001/plan.json').read_text())
        sys.path.insert(0,str(root/p['native_site']))
        import numpy as np
        import manifold3d as m
        import lib3mf
        from importlib import metadata
        report['versions']={name:metadata.version(name) for name in ['lib3mf','manifold3d','numpy']}

        def read_stl(path):
            raw=path.read_bytes();require(len(raw)>=84,'Truncated binary STL')
            count=int.from_bytes(raw[80:84],'little');require(len(raw)==84+50*count,'Binary STL length differs')
            dtype=np.dtype([('normal','<f4',(3,)),('xyz','<f4',(3,3)),('attribute','<u2')])
            triangles=np.frombuffer(raw,offset=84,count=count,dtype=dtype)['xyz'].copy()
            require(np.isfinite(triangles).all(),'Nonfinite source vertex')
            vertices,inverse=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
            faces=inverse.reshape(-1,3).astype(np.uint32)
            return np.ascontiguousarray(vertices,dtype='<f4'),np.ascontiguousarray(faces,dtype='<u4'),hashlib.sha256(triangles.tobytes()).hexdigest()

        paths=[root/'parts/993-eng-carrier-0001/source/design-20261016/corner-slide-candidate-20261018/candidate-surface.stl',*[root/f'work/carrier-resume-20261020/manifold-root-patch-001/output/patch-{i}.stl' for i in range(2)]]
        require(sha(paths[0])=='b4026f66dc77b8022e82c358553e8e93ce0cbc2ea0fd31da19ac39a9f891a803','Current parent STL differs')
        wrapper=lib3mf.get_wrapper();model=wrapper.CreateModel();model.SetUnit(lib3mf.ModelUnit.MilliMeter)
        identity=lib3mf.Transform()
        for i in range(3):identity.Fields[i][i]=1.
        solids=[];sources=[];mesh_objects=[]
        for i,path in enumerate(paths):
            vertices,faces,face_hash=read_stl(path)
            solid=m.Manifold(m.Mesh64(vertices.astype(np.float64),faces.astype(np.uint64)))
            require(solid.status()==m.Error.NoError and not solid.is_empty() and solid.volume()>0,'Source component is not a positive oriented triangle solid')
            mesh=model.AddMeshObject();mesh.SetName('Retained current24af parent' if i==0 else f'Explicit NURBS reinforcement {i}')
            positions=(lib3mf.Position*len(vertices)).from_buffer_copy(vertices.tobytes())
            triangles=(lib3mf.Triangle*len(faces)).from_buffer_copy(faces.tobytes())
            mesh.SetGeometry(positions,triangles)
            require(mesh.IsValid(),'SDK rejected source mesh')
            row=dict(index=i,source=str(path.relative_to(root)),source_sha256=sha(path),source_triangle_coordinate_sha256=face_hash,
                     vertices=len(vertices),triangles=len(faces),vertex_bytes_sha256=hashlib.sha256(vertices.tobytes()).hexdigest(),face_index_bytes_sha256=hashlib.sha256(faces.tobytes()).hexdigest(),
                     lib3mf_resource_id=mesh.GetResourceID(),lib3mf_valid=mesh.IsValid(),triangle_solid_status=str(solid.status()),volume_mm3=solid.volume())
            report['components'].append(row);solids.append(solid);sources.append((vertices,faces));mesh_objects.append(mesh)
            write(out/'progress.json',report)
        assembly=model.AddComponentsObject();assembly.SetName('Unqualified 993 carrier additive assembly study')
        for mesh in mesh_objects:assembly.AddComponent(mesh,identity)
        require(assembly.IsValid() and assembly.GetComponentCount()==3,'SDK components graph differs')
        model.AddBuildItem(assembly,identity)
        archive=out/'carrier-additive-assembly-study.3mf';model.QueryWriter('3mf').WriteToFile(str(archive))
        restored=wrapper.CreateModel();reader=restored.QueryReader('3mf');reader.SetStrictModeActive(True);reader.ReadFromFile(str(archive))
        report['reader_warnings']=[reader.GetWarning(i) for i in range(reader.GetWarningCount())]
        report['roundtrip']=[]
        for row,(vertices,faces) in zip(report['components'],sources):
            mesh=restored.GetMeshObjectByID(row['lib3mf_resource_id'])
            rv=np.asarray([[v.Coordinates[i] for i in range(3)]for v in mesh.GetVertices()],dtype='<f4')
            rf=np.asarray([[t.Indices[i] for i in range(3)]for t in mesh.GetTriangleIndices()],dtype='<u4')
            triangle_hash=hashlib.sha256(rv[rf].tobytes()).hexdigest()
            result=dict(index=row['index'],mesh_valid=mesh.IsValid(),vertices_equal=vertices.tobytes()==rv.tobytes(),triangles_equal=faces.tobytes()==rf.tobytes(),source_triangle_coordinates_equal=triangle_hash==row['source_triangle_coordinate_sha256'])
            report['roundtrip'].append(result)
        items=restored.GetBuildItems();report['build_items']=items.Count();require(items.MoveNext(),'No build item')
        root_object=items.GetCurrent().GetObjectResource();report['restored_components_count']=restored.GetComponentsObjectByID(root_object.GetResourceID()).GetComponentCount()
        report['positive_overlap_checks']=[]
        for i,patch in enumerate(solids[1:]):
            overlap=m.Manifold.batch_boolean([solids[0],patch],m.OpType.Intersect)
            report['positive_overlap_checks'].append(dict(patch_index=i,operator_status=str(overlap.status()),volume_mm3=overlap.volume(),positive_volume=overlap.volume()>0))
        report['mass_upper_bound_kg']=sum(s.volume() for s in solids)*4420e-9
        report['checks']=dict(one_build_item=report['build_items']==1,three_components=report['restored_components_count']==3,strict_reader_without_warnings=not report['reader_warnings'],all_component_geometry_bytes_preserved=all(all(row[k]for k in ['mesh_valid','vertices_equal','triangles_equal','source_triangle_coordinates_equal'])for row in report['roundtrip']),positive_patch_overlap=all(row['operator_status']=='Error.NoError' and row['positive_volume']for row in report['positive_overlap_checks']),mass_upper_bound_below_1_30_kg=0<report['mass_upper_bound_kg']<=1.3)
        report['archive_sha256']=sha(archive)
        report['status']='component_3MF_identity_and_mass_screens_passed' if all(report['checks'].values()) else 'component_3MF_screen_refused'
        report['pending']=['independent full component self-intersection audit','complete protected-interface checks','slicer union of every component and layer','volume meshing and mechanical verification','complete process preparation']
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;write(out/'assessment.json',report)
    print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out/'assessment.json'))))
    return 0 if report['status'] in ['component_3MF_identity_and_mass_screens_passed','component_3MF_screen_refused'] else 1


if __name__=='__main__':raise SystemExit(main())
