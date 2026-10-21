"""Losslessly index every binary-STL triangle; no repair or filtering."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--stl',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    source=Path(__file__).with_name('certified_patch_collapse.py');spec=importlib.util.spec_from_file_location('_unmodified_stl_indexer',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);v,f=module.load_stl(a.stl,np)
    mesh=a.output/'surface.mesh64'
    with mesh.open('w')as stream:stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v.astype(np.float64),fmt='%.17g');np.savetxt(stream,f,fmt='%d')
    (a.output/'assessment.json').write_text(json.dumps(dict(status='all_binary_STL_triangles_indexed_without_geometry_changes',vertices=len(v),triangles=len(f),source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.stl,source,Path(__file__)]},output_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(),surface_audit_pending=True),indent=2)+'\n')
    print(json.dumps(dict(vertices=len(v),triangles=len(f))))

if __name__=='__main__':main()
