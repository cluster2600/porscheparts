"""Read every synthetic cube boundary polygon and check its analytic planes/volume."""
from fractions import Fraction
import json,re,sys
from pathlib import Path
import numpy as np
from import_conforming_volume import helper,integer_points,determinant
from prepare_conforming_surface import sha

def check(case,parser):
    case,parser=Path(case),Path(parser);output=case/'geometry-readback.json'
    if output.exists() or output.is_symlink():raise ValueError('Fresh cube readback required')
    assert sha(parser)=='f50f4cd315c757d9d2c291640f49bfd1a6107a1de851685f8c407e47c33883cb'
    ascii=helper(parser,'frozen_cube_ascii');instance='0' if (case/'0/polyMesh/faces').is_file() else 'constant';mesh=case/instance/'polyMesh';n,body=ascii.foam_list(mesh/'points');v=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3);assert len(v)==n and np.isfinite(v).all()
    count,body=ascii.foam_list(mesh/'faces');rows=list(re.finditer(r'(\d+)\s*\(([^()]*)\)',body));assert len(rows)==count and not re.sub(r'\d+\s*\([^()]*\)','',body).strip();faces=[]
    for row in rows:
        f=np.fromstring(row[2],sep=' ',dtype=np.int64);assert len(f)==int(row[1]) and 3<=len(f)<=64 and f.min()>=0 and f.max()<len(v);faces.append(f)
    count,body=ascii.foam_list(mesh/'boundary');blocks=list(re.finditer(r'([A-Za-z][A-Za-z0-9_]*)\s*\{([^{}]*)\}',body));assert count==4 and len(blocks)==4
    names=set();triangles=[];max_error=0.;starts=[]
    for block in blocks:
        name=block[1];assert name in ['inlet','outlet','duct','rotor'] and name not in names;names.add(name);size=int(re.search(r'\bnFaces\s+(\d+)\s*;',block[2])[1]);start=int(re.search(r'\bstartFace\s+(\d+)\s*;',block[2])[1]);starts.extend(range(start,start+size))
        planes={'inlet':[(2,.5)],'outlet':[(2,-.5)],'rotor':[(0,.5)],'duct':[(0,-.5),(1,-.5),(1,.5)]}[name]
        for f in faces[start:start+size]:
            error=min(float(np.max(np.abs(v[f,axis]-value))) for axis,value in planes);max_error=max(max_error,error);assert error<1e-12
            triangles.extend([[int(f[0]),int(f[i]),int(f[i+1])] for i in range(1,len(f)-1)])
    assert starts==list(range(starts[0],len(faces)))
    triangles=np.asarray(triangles);edges=triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2);unique,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True);balance=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1.,-1.));assert np.all(counts==2) and np.all(balance==0)
    used=np.unique(triangles);assert len(used)-len(unique)+len(triangles)==2
    integers,scale=integer_points(v);zero=(0,0,0);total=sum(determinant(zero,*(integers[int(i)] for i in f)) for f in triangles);volume=Fraction(total,6*scale**3);assert abs(volume-1)<Fraction(1,10**12)
    log=(case/'log.checkMesh.allGeometry').read_text();assert 'Mesh OK.' in log and 'Failed' not in log;native=float(re.search(r'Total volume = ([+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)',log)[1]);assert abs(native-1)<1e-12 and abs(float(volume)-native)<1e-12
    count,body=ascii.foam_list(mesh/'owner');owner=np.fromstring(body,sep=' ',dtype=np.int64);count,body=ascii.foam_list(mesh/'neighbour');neighbour=np.fromstring(body,sep=' ',dtype=np.int64);cells=max(int(owner.max()),int(neighbour.max()))+1;assert cells==int(re.search(r'^\s*cells:\s+(\d+)',log,re.M)[1]) and len(faces)==int(re.search(r'^\s*faces:\s+(\d+)',log,re.M)[1])
    result={'status':'synthetic_cube_all_boundary_planes_closed_topology_and_exact_serialized_volume_checked','source_sha256':sha(__file__),'mesh_instance':instance,'cells':cells,'parser_sha256':sha(parser),'vertices':len(v),'faces':len(faces),'boundary_fan_triangles':len(triangles),'Euler_characteristic':2,'maximum_plane_error_m':max_error,'exact_serialized_boundary_volume_m3':str(volume),'volume_absolute_error_from_analytic_unit_cube':float(abs(volume-1)),'comparison_numeric_bound':1e-12,'native_full_quality_passed':True,'native_mesh_sha256':{name:sha(mesh/name) for name in ['points','faces','owner','neighbour','boundary']},'synthetic_control_only':True,'CFD_accepted':False,'manufacturing_authorized':False}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result

if __name__=='__main__':check(*sys.argv[1:])
