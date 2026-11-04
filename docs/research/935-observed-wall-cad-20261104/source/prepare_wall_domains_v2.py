"""Audit frozen observed wall regions and prepare only supported CAD domains."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def save(path,data):
    with path.open('x') as stream: json.dump(data,stream,indent=2,allow_nan=False);stream.write('\n')


def components(f):
    parent=np.arange(len(f));seen={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,triangle in enumerate(f):
        for a,b in zip(triangle,np.roll(triangle,1)):
            key=tuple(sorted((int(a),int(b))))
            if key in seen:parent[find(i)]=find(seen[key])
            else:seen[key]=i
    return np.asarray([find(i) for i in range(len(f))])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('paper','baseline','arrays','inspector','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing preparation directory refused.')
    contract_path=args.paper/'registered-contract.json';part_path=args.paper/'registered-partitions.json'
    if sha(contract_path)!='49fc806e1f9d6f129892d1cdd15505b4ed304a68ee84f37bcbf1fd1c8461f779' or sha(part_path)!='bca11c2633ed6fae331b9bd47d420f07f170b6f34d4ba232d68c87f37f1aa824':
        raise SystemExit('Frozen section-pair contract or partition mismatch.')
    contract=json.loads(contract_path.read_text());partitions=json.loads(part_path.read_text())['partitions']
    for name in ['receipt.json','refined-features/features.json']:
        expected=contract['baseline_receipt_sha256'] if name=='receipt.json' else contract['baseline_inputs'][name]
        if sha(args.baseline/name)!=expected:raise SystemExit('Baseline input mismatch: '+name)
    with np.load(args.arrays,allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
    for name,array,dtype in [('vertices',v,'<f8'),('triangles',f,'<i8')]:
        if hashlib.sha256(np.asarray(array,dtype=dtype).tobytes()).hexdigest()!=contract['source_array_hashes'][name]:raise SystemExit('Original decoded arrays mismatch.')
    args.output.mkdir(parents=True)
    gates={'max_source_vertex_projection_mm':.4,'reversed_uv_faces':0,'zero_uv_area_faces':0,'maximum_relative_projected_overlap':1e-8}
    save(args.output/'plan.json',{'source_arrays_sha256':sha(args.arrays),'contract_sha256':sha(contract_path),'partitions_sha256':sha(part_path),
        'baseline_features_sha256':sha(args.baseline/'refined-features/features.json'),'inspector_sha256':sha(args.inspector),'gates':gates,
        'policy':'Use the frozen baseline circle axes/radii for all three regions; no refit or selection based on new residual scores. Keep all acquired faces as exact references.',
        'units':'mm, owner-confirmed project scale; not independent physical calibration','source_sha256':sha(Path(__file__))})
    features=json.loads((args.baseline/'refined-features/features.json').read_text())['fits']
    records=[];private=[]
    for index in range(1,4):
        ident=f'stud_passage_{index}_wall_candidate';part=next(x for x in partitions if x['id']==ident);partition=args.paper/part['file']
        if sha(partition)!=part['sha256']:raise SystemExit('Source partition mismatch.')
        with np.load(partition,allow_pickle=False) as a:face_ids=a['selected_source_face_ids'];train=a['training_source_vertex_ids'];evaluation=a['evaluation_source_vertex_ids']
        used,inverse=np.unique(f[face_ids],return_inverse=True);vertices=v[used];triangles=inverse.reshape((-1,3))
        if np.intersect1d(train,evaluation).size:raise SystemExit('Training/evaluation overlap.')
        np.savez_compressed(args.output/(ident+'-reference.npz'),vertices=vertices,triangles=triangles,source_face_ids=face_ids,source_vertex_ids=used)
        off=args.output/(ident+'.off')
        with off.open('x') as stream:
            stream.write(f'OFF\n{len(vertices)} {len(triangles)} 0\n');np.savetxt(stream,vertices,fmt='%.17g');np.savetxt(stream,np.column_stack((np.full(len(triangles),3),triangles)),fmt='%d')
        native=subprocess.run([str(args.inspector),str(off)],capture_output=True,text=True,timeout=60)
        geometry=json.loads(native.stdout) if native.stdout.strip() else {'reader_failed':True}
        save(args.output/(ident+'-native.json'),geometry)
        item=next(x for x in features if x['id']==f'stud_passage_{index}_C_91')
        n=np.asarray(item['axis_xyz'],float);n/=np.linalg.norm(n);origin=np.asarray(item['center_xyz_mm']);radius=item['diameter_mm']/2
        ref=np.eye(3)[np.argmin(abs(n))];x=np.cross(n,ref);x/=np.linalg.norm(x);y=np.cross(n,x)
        delta=vertices-origin;radial=np.abs(np.linalg.norm(np.cross(delta,n),axis=1)-radius)
        global_angle=np.mod(np.arctan2(delta@y,delta@x),2*np.pi);theta=global_angle[triangles];lifts=np.rint((theta[:,0,None]-theta)/(2*np.pi)).astype(np.int64);u=theta+2*np.pi*lifts;z=(delta@n)[triangles]
        area=(u[:,1]-u[:,0])*(z[:,2]-z[:,0])-(u[:,2]-u[:,0])*(z[:,1]-z[:,0]);nonzero=np.abs(area)>1e-14
        direction=float(np.sign(np.median(area[nonzero]))) if nonzero.any() else 0
        folds=int((area*direction<0).sum());groups=components(triangles);domains=[];summed=0;union_area=0
        window=box(0,float(z.min()-1),2*np.pi,float(z.max()+1))
        for group in np.unique(groups):
            pieces=[]
            for row in np.flatnonzero(groups==group):
                for shift in [-1,0,1]:
                    uu=theta[row]+2*np.pi*(lifts[row]+shift)
                    if uu.max()<=0 or uu.min()>=2*np.pi:continue
                    polygon=Polygon(np.column_stack((uu,z[row])))
                    cut=polygon if uu.min()>=0 and uu.max()<=2*np.pi else polygon.intersection(window)
                    if not cut.is_empty and cut.area>0:pieces.append(cut)
            total=unary_union(pieces);summed+=sum(p.area for p in pieces);union_area+=total.area
            if not total.is_valid:raise SystemExit('Invalid projected union; no automatic repair.')
            polygons=[total] if total.geom_type=='Polygon' else list(total.geoms)
            for polygon in polygons:
                if polygon.geom_type!='Polygon':raise SystemExit('Non-area projected domain.')
                domains.append({'outer':list(polygon.exterior.coords),'holes':[list(r.coords) for r in polygon.interiors]})
        overlap=max(0.,summed-union_area)/summed if summed else 1.
        checks={'native_source_valid':geometry.get('valid_polygon_mesh') is True and geometry.get('intersection_pairs')==0 and geometry.get('degenerate_faces')==0,
            'bounded_projection':float(radial.max())<=.4,'no_uv_fold':folds==0,'no_uv_degeneracy':bool(nonzero.all()),'no_projected_overlap':overlap<=1e-8}
        record={'id':ident,'source_faces':len(face_ids),'source_vertices':len(used),'source_components':len(np.unique(groups)),
            'projection_p95_mm':float(np.quantile(radial,.95)),'projection_max_mm':float(radial.max()),'reversed_uv_faces':folds,'zero_uv_area_faces':int((~nonzero).sum()),
            'projected_overlap_fraction':overlap,'trim_domains':len(domains),'expected_cylinder_area_mm2':union_area*radius,'checks':checks,
            'analytic_candidate_admitted':all(checks.values()),'reference_geometry_exact':True,'physical_acceptance':False}
        records.append(record)
        private.append({'id':ident,'origin':origin.tolist(),'axis':n.tolist(),'x_direction':x.tolist(),'radius':radius,'source_orientation':direction,'domains':domains,'admitted':all(checks.values())})
    save(args.output/'cad-domains.json',private);save(args.output/'admissibility.json',{'regions':records,'gates':gates,'baseline_changed':False,'hidden_geometry_added':False,'manufacturing_authorized':False})
    print(json.dumps({'regions':records}))


if __name__=='__main__':main()
