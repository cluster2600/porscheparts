"""Triangulate the actual ASCII CFD boundary using face-centre fans, in SI."""
import hashlib,json,re,sys
from pathlib import Path
import numpy as np
from run_reconstruction import fresh,save
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def foam_list(path,maximum_count=2_000_000):
 if type(maximum_count) is not int or not 1<=maximum_count<=10_000_000:raise ValueError("Bounded list capacity required")
 text=Path(path).read_text();text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
 match=re.fullmatch(r'\s*FoamFile\s*\{([^{}]*)\}\s*(\d+)\s*\((.*)\)\s*',text,re.S)
 if not match or not re.search(r'\bformat\s+ascii\s*;',match[1]) or not 0<int(match[2])<=maximum_count:raise ValueError('Bounded ASCII OpenFOAM list required')
 return int(match[2]),match[3]

def winding(vertices,triangles,point):
 t=vertices[triangles]-point;a,b,c=t[:,0],t[:,1],t[:,2];la,lb,lc=(np.linalg.norm(x,axis=1) for x in (a,b,c))
 numerator=np.einsum('ij,ij->i',a,np.cross(b,c));denominator=la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
 return float(np.arctan2(numerator,denominator).sum()/(2*np.pi))

def prepare(snapshot,output):
 snapshot=Path(snapshot);root=snapshot/'constant/polyMesh';expected=json.loads((snapshot/'snapshot.json').read_text());info=json.loads((snapshot/'snapshot-info.json').read_text());reference_volume=info['native_volume_m3']
 if not 0<reference_volume<1 or info['source_length_unit']!='m':raise ValueError('Explicit native SI volume reference required')
 for name in ['points','faces','boundary']:
  if sha(root/name)!=expected['constant/polyMesh/'+name]:raise ValueError('Frozen CFD mesh input changed')
 count,body=foam_list(root/'points');v=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
 if v.shape!=(count,3) or not np.isfinite(v).all():raise ValueError('Complete finite points required')
 face_count,body=foam_list(root/'faces');matches=list(re.finditer(r'(\d+)\s*\(([^()]*)\)',body))
 if len(matches)!=face_count or re.sub(r'\d+\s*\([^()]*\)','',body).strip():raise ValueError('Complete face list required')
 count,body=foam_list(root/'boundary');blocks=list(re.finditer(r'([A-Za-z][A-Za-z0-9_]*)\s*\{([^{}]*)\}',body));patches={}
 for m in blocks:
  patches[m[1]]={'faces':int(re.search(r'\bnFaces\s+(\d+)\s*;',m[2])[1]),'start':int(re.search(r'\bstartFace\s+(\d+)\s*;',m[2])[1])}
 markers={'inlet':1,'outlet':2,'duct':3,'rotor':4}
 if count!=4 or set(patches)!=set(markers):raise ValueError('Four original named patches required')
 first=min(x['start'] for x in patches.values());indices=sorted(i for p in patches.values() for i in range(p['start'],p['start']+p['faces']))
 if indices!=list(range(first,face_count)):raise ValueError('Complete disjoint boundary coverage required')
 points=list(v);tri=[];tags=[];parents=[];minimum_alignment=1.
 for name,p in patches.items():
  for facei in range(p['start'],p['start']+p['faces']):
   match=matches[facei];f=np.fromstring(match[2],sep=' ',dtype=np.int64)
   if not 3<=len(f)<=64 or len(f)!=int(match[1]) or f.min()<0 or f.max()>=len(v) or len(np.unique(f))!=len(f):raise ValueError('Valid bounded polygon required')
   if len(f)==3:pieces=[f.tolist()]
   else:
    x=v[f];average=x.mean(axis=0);next_x=np.roll(x,-1,axis=0);cross=np.cross(next_x-x,average-x);weights=np.linalg.norm(cross,axis=1)
    if np.min(weights)<=0:raise ValueError('Non-degenerate face fan required')
    centre=(weights[:,None]*(x+next_x+average)).sum(axis=0)/(3*weights.sum());area=cross.sum(axis=0)/2
    normals=np.cross(x-centre,next_x-centre);alignment=(normals@area)/(np.linalg.norm(normals,axis=1)*np.linalg.norm(area));minimum_alignment=min(minimum_alignment,float(alignment.min()))
    ci=len(points);points.append(centre);pieces=[[ci,int(f[j]),int(f[(j+1)%len(f)])] for j in range(len(f))]
   tri.extend(pieces);tags.extend([markers[name]]*len(pieces));parents.extend([facei]*len(pieces))
 vertices=np.array(points);triangles=np.array(tri,dtype=np.int64);tags=np.array(tags,dtype=np.int32);used=np.unique(triangles);mapping=np.full(len(vertices),-1,dtype=np.int64);mapping[used]=np.arange(len(used));vertices=vertices[used];triangles=mapping[triangles]
 t=vertices[triangles];volume=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
 if abs(volume/reference_volume-1)>1e-9:raise ValueError('Face-fan fluid volume differs from native Gauss volume')
 rotor=triangles[tags==4];rt=vertices[rotor];normal=np.cross(rt[:,1]-rt[:,0],rt[:,2]-rt[:,0]);areas=np.linalg.norm(normal,axis=1);hole=None
 for i in np.argsort(areas)[-20:][::-1]:
  candidate=rt[i].mean(axis=0)+normal[i]/areas[i]*min(.0001,np.sqrt(areas[i])*.02)
  if abs(abs(winding(vertices,rotor,candidate))-1)<1e-8 and abs(winding(vertices,triangles,candidate))<1e-8:hole=candidate;break
 if hole is None or abs(winding(vertices,triangles,np.array([-.17,.17,.18]))-1)>1e-8:raise ValueError('Independent fluid/solid winding classification required')
 out=fresh(output);np.savez_compressed(out/'boundary.npz',vertices=vertices,triangles=triangles,markers=tags,parent_polygon=np.array(parents),hole=hole)
 with (out/'fluid.smesh').open('x') as s:
  s.write(f'{len(vertices)} 3 0 0\n');np.savetxt(s,np.column_stack([np.arange(len(vertices)),vertices]),fmt=['%d','%.17g','%.17g','%.17g']);s.write(f'{len(triangles)} 1\n');np.savetxt(s,np.column_stack([np.full(len(triangles),3),triangles,tags]),fmt='%d');s.write('1\n0 '+' '.join(f'{x:.17g}' for x in hole)+'\n0\n')
 with (out/'boundary.obj').open('x') as s:
  np.savetxt(s,vertices,fmt='v %.17g %.17g %.17g');np.savetxt(s,triangles+1,fmt='f %d %d %d')
 save(out/'receipt.json',{'status':'CFD_boundary_face_fans_pending_exact_intersection_audit','source_sha256':sha(__file__),'source_snapshot_sha256':sha(snapshot/'snapshot.json'),'source_info_sha256':sha(snapshot/'snapshot-info.json'),'source_mesh_sha256':{n:sha(root/n) for n in ['points','faces','boundary']},'source_fluid_cells':info['native_cells'],'source_boundary_polygons':len(indices),'boundary_vertices':len(vertices),'triangles':len(triangles),'patch_markers':markers,'triangles_per_patch':{n:int((tags==i).sum()) for n,i in markers.items()},'minimum_face_fan_alignment':minimum_alignment,'volume_m3':volume,'volume_relative_difference_from_native':abs(volume/reference_volume-1),'solid_hole_winding':winding(vertices,rotor,hole),'fluid_hole_winding':winding(vertices,triangles,hole),'nonplanar_polygons_explicitly_fanned':True,'PicoGK_design_master_changed':False,'scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False,'output_sha256':{n:sha(out/n) for n in ['boundary.npz','boundary.obj','fluid.smesh']}})
 print(out)
if __name__=='__main__':prepare(sys.argv[1],sys.argv[2])
