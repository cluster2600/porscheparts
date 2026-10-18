"""Certify whole-triangle prism dominance; retain original coordinates and IDs."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('binary',type=Path);p.add_argument('--floor-z-mm',type=float,required=True)
    args=p.parse_args();out=args.output;assert args.floor_z_mm==0
    data=np.load(args.input,allow_pickle=False);v=data['vertices'];f=data['faces']
    assert v.dtype==np.float64 and np.issubdtype(f.dtype,np.integer) and v.ndim==f.ndim==2 and v.shape[1]==f.shape[1]==3
    assert len(v)>0 and len(f)>0 and np.isfinite(v).all() and f.min()>=0 and f.max()<len(v)
    integer=np.ascontiguousarray(f,dtype=np.int64);assert np.array_equal(f,integer)
    ids=data['source_face_ids'] if 'source_face_ids' in data else np.arange(len(f),dtype=np.int64)
    assert ids.shape==(len(f),) and np.issubdtype(ids.dtype,np.integer) and len(np.unique(ids))==len(ids)
    assert np.isfinite(ids).all()
    with (out/'input.mesh64').open('w') as stream:
        stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,integer,fmt='%d')
    command=[str(args.binary),str(out/'input.mesh64'),str(out/'native.json'),repr(args.floor_z_mm)]
    with (out/'native.log').open('w') as log:run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    report={'input_sha256':sha(args.input),'native_returncode':run.returncode,'floor_z_mm':args.floor_z_mm}
    if run.returncode!=0 or not (out/'native.json').is_file():
        report.update(status='rejected_native_failure',**{'pass':False});(out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');return 2
    native=json.loads((out/'native.json').read_text());kept=np.asarray(native['retained_input_face_indices'],dtype=np.int64)
    removed=np.asarray([c['input_face_index'] for c in native['certificates']],dtype=np.int64)
    assert native['pass'] and native['input_faces']==len(f) and native['input_vertices']==len(v)
    assert len(np.unique(kept))==len(kept) and len(np.unique(removed))==len(removed)
    assert sorted(np.r_[kept,removed].tolist())==list(range(len(f)))
    assert len(kept)>0 and (len(kept)<2 or np.all(np.diff(kept)>0))
    native['retained_source_face_ids']=ids[kept].tolist()
    for c in native['certificates']:c['source_face_id']=int(ids[c['input_face_index']])
    for patch in native['horizontal_patches']:patch['source_face_ids']=ids[patch['input_face_indices']].tolist()
    (out/'certificates.json').write_text(json.dumps(native,indent=2)+'\n')
    result=out/'retained-roofs.npz';np.savez_compressed(result,vertices=v,faces=integer[kept],source_face_ids=ids[kept])
    with np.load(result,allow_pickle=False) as check:
        coordinates_unchanged=check['vertices'].tobytes()==v.tobytes();indices_unchanged=np.array_equal(check['faces'],integer[kept]);assert coordinates_unchanged and indices_unchanged
    report.update(status='certified_set_union_reduction',**{'pass':True},native=native,input_faces=len(f),retained_faces=len(kept),removed_faces=len(removed),
       removed_source_face_ids=ids[removed].tolist(),result_sha256=sha(result),certificates_sha256=sha(out/'certificates.json'),
       coordinates_unchanged=coordinates_unchanged,retained_face_indices_unchanged=indices_unchanged,
       coordinates_bytes_sha256=hashlib.sha256(v.tobytes()).hexdigest(),
       scope='Exact geometric union-preserving dominance of closed positive vertical prisms at floor0. This is not equality of signed chains, multiplicities or summed volumes.')
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'retained_faces':len(kept),'removed_faces':len(removed)}));return 0
if __name__=='__main__':sys.exit(main())
