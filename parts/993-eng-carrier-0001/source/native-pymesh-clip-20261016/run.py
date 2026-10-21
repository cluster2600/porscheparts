"""One exact CSG tree with part clipped to a strictly enclosing chain bbox."""
import argparse,hashlib,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parent
IMAGE='sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e'
ARCHIVE_SHA='536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56'
NATIVE_REL='usr/local/lib/python3.6/site-packages/pymesh/lib/PyMesh.cpython-36m-x86_64-linux-gnu.so'
NATIVE_SHA='17cd2bb3a74539b1f913501f49a362f65cb395a62ab65bc5a6e8815ccc585d8a'
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
WORKER=r'''
"""One in-memory PyMesh CSGTree; mesh conversion occurs only at the root."""
import hashlib,json,time,inspect
from pathlib import Path
import numpy as np,pymesh,PyMesh
out=Path('/tmp/output')
inputs={'chain':Path('/tmp/input/a.npz'),'mask':Path('/tmp/input-b/b.npz'),'part':Path('/tmp/input-c/c.npz')}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
leaves=[]
original_vertices={}
for name,path in inputs.items():
    data=np.load(str(path))
    assert data['vertices'].dtype==np.float64 and np.isfinite(data['vertices']).all()
    original_vertices[name]=data['vertices']
    leaves.append(pymesh.form_mesh(data['vertices'],data['faces']))
chain_v=original_vertices['chain'];chain_f=np.asarray(leaves[0].faces,dtype=np.int64)
edges=np.vstack([chain_f[:,[0,1]],chain_f[:,[1,2]],chain_f[:,[2,0]]])
unique,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
orientation=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1,-1),minlength=len(unique))
assert len(chain_v)>0 and np.all(counts==2) and np.all(orientation==0), 'Chain must be indexed closed and consistently oriented'
minimum=chain_v.min(axis=0);maximum=chain_v.max(axis=0)
lower=np.nextafter(minimum,np.full(3,-np.inf));upper=np.nextafter(maximum,np.full(3,np.inf))
assert np.isfinite(lower).all() and np.isfinite(upper).all() and np.all(lower<minimum) and np.all(upper>maximum)
assert np.all(chain_v>lower) and np.all(chain_v<upper)
x0,y0,z0=lower;x1,y1,z1=upper
box_vertices=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]],dtype=np.float64)
box_faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=np.int64)
box=pymesh.form_mesh(box_vertices,box_faces);assert box.volume>0
np.savez_compressed(str(out/'clip-bbox.npz'),vertices=box_vertices,faces=box_faces)
tree_definition={'intersection':[{'difference':[{'mesh':leaves[0]},{'intersection':[{'mesh':leaves[2]},{'mesh':box}]}]},{'mesh':leaves[1]}]}
start=time.monotonic();tree=pymesh.CSGTree(tree_definition)
# This is the first/only tree.mesh, tree.vertices or get_vertices call.
result=tree.mesh
arrays={'vertices':result.vertices,'faces':result.faces}
for name in ['source_face','source']:
    assert result.has_attribute(name);arrays[name]=result.get_attribute(name)
np.savez_compressed(str(out/'result.npz'),**arrays)
report={'status':'executed','algorithm':'intersection(difference(chain,intersection(part,strict_bbox(chain))),mask) in one native CSGTree',
        'seconds':time.monotonic()-start,'volume_mm3':result.volume,'leaf_role_order':['chain','part','clip_bbox','mask'],'leaf_face_counts':[leaves[0].num_faces,leaves[2].num_faces,box.num_faces,leaves[1].num_faces],
        'clip_bbox':{'source_chain_bounds_mm':[minimum.tolist(),maximum.tolist()],'strict_bounds_mm':[lower.tolist(),upper.tolist()],
          'construction':'np.nextafter of each of the six original IEEE bounds toward exterior infinity; no arbitrary padding',
          'all_chain_vertices_strictly_inside':True,'chain_indexed_closed_oriented':True,'box_closed_oriented_template_faces':box_faces.tolist(),
          'bbox_npz_sha256':sha(out/'clip-bbox.npz'),'proof':'A closed chain and all its triangles lie within its convex bounding box. Since A is contained in B, A minus (C intersect B) equals A minus C.'},
        'faces':result.num_faces,'vertices':result.num_vertices,'attributes':['source_face','source'],
        'intermediate_double_exports':0,'pymesh_version':pymesh.__version__,
        'module_sha256':sha(pymesh.__file__),'native_sha256':sha(PyMesh.__file__),
        'python_CSGTree_source_sha256':hashlib.sha256(inspect.getsource(pymesh.CSGTree).encode()).hexdigest(),
        'input_sha256':{name:sha(path) for name,path in inputs.items()},
        'result_sha256':sha(out/'result.npz'),'final_output_type':'float64; final conversion still needs independent topology/exact-contact audit',
        'primary_sources':['https://github.com/PyMesh/PyMesh/blob/main/tools/Boolean/IGL/IGLCSGTree.cpp',
                           'https://github.com/libigl/libigl/blob/main/include/igl/copyleft/cgal/CSGTree.h'],
        'source_scope':'Primary upstream C++ holds Epeck vertices and passes child V() directly; installed Python API matches. Exact installed C++ commit is unavailable from image metadata.'}
(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('chain',type=Path);p.add_argument('mask',type=Path);p.add_argument('part',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--timeout-seconds',type=int,choices=[600,1200],required=True)
    args=p.parse_args();assert all(p.is_file() for p in [args.chain,args.mask,args.part]);assert not args.output.exists()
    out=args.output.resolve();assert out.parent==ROOT/'jobs','Fresh direct child of owned jobs/ required'
    sha=file_sha
    installation=ROOT/'installation-receipt.json';initial_installation=sha(installation)
    runtime=json.loads(installation.read_text());assert runtime['export_archive_sha256']==ARCHIVE_SHA and runtime['image_id']==IMAGE
    RUNTIME=Path(runtime['rootfs_path'])
    assert sha(RUNTIME/NATIVE_REL)==NATIVE_SHA,'Pinned native runtime mismatch'
    assert sha(__file__)==runtime['source_files_sha256']['run.py']
    assert all(sha(RUNTIME/path)==value for path,value in runtime['runtime_files_sha256'].items())
    assert all(str((RUNTIME/path).readlink())==value for path,value in runtime['rootfs_symlinks'].items())
    out.mkdir();initial_runner=sha(__file__);initial_a=sha(args.chain);initial_b=sha(args.mask);initial_c=sha(args.part)
    (out/'runner.py').write_bytes(Path(__file__).read_bytes());(out/'worker.py').write_text(WORKER)
    (out/'installation-receipt.json').write_bytes(installation.read_bytes())
    initial_worker=sha(out/'worker.py');unit='carrier-csg-v5-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,
             '-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec='+str(args.timeout_seconds+10),
             '/usr/bin/timeout','--kill-after=10s',str(args.timeout_seconds),'/usr/bin/bwrap',
             '--ro-bind',str(RUNTIME),'/', '--unshare-net','--unshare-pid','--unshare-ipc',
             '--die-with-parent','--new-session','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
             '--dir','/tmp/input','--ro-bind',str(args.chain.resolve()),'/tmp/input/a.npz',
             '--bind',str(out),'/tmp/output','--chdir','/tmp/output','--clearenv',
             '--setenv','PATH','/usr/local/bin:/usr/bin:/bin','--setenv','OMP_NUM_THREADS','1',
             '--setenv','OPENBLAS_NUM_THREADS','1','--setenv','PYTHONDONTWRITEBYTECODE','1']
    command+=['--dir','/tmp/input-b','--ro-bind',str(args.mask.resolve()),'/tmp/input-b/b.npz',
              '--dir','/tmp/input-c','--ro-bind',str(args.part.resolve()),'/tmp/input-c/c.npz']
    command+=['/usr/local/bin/python','/tmp/output/worker.py']
    receipt={'image_id':IMAGE,'rootfs_archive_sha256':ARCHIVE_SHA,'native_sha256':NATIVE_SHA,
             'command':command,'unit':unit+'.scope','chain_sha256':initial_a,'mask_sha256':initial_b,'part_sha256':initial_c,
             'wrapper_sha256':initial_runner,'worker_sha256':initial_worker,'timeout_seconds':args.timeout_seconds,
             'installation_receipt_sha256':initial_installation,'runtime_files_sha256':runtime['runtime_files_sha256']}
    (out/'execution-plan.json').write_text(json.dumps(receipt,indent=2)+'\n')
    start=time.monotonic();process=None
    try:
        with (out/'stdout.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            code=process.wait(timeout=args.timeout_seconds+30)
        receipt.update(status='executed' if code==0 else 'failed',returncode=code)
    except subprocess.TimeoutExpired:
        receipt.update(status='timed_out',returncode=None)
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
        if process is not None and process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
        check=subprocess.run(['systemctl','--user','is-active',unit+'.scope'],capture_output=True,text=True,timeout=10)
        receipt['owned_scope_inactive']=check.returncode!=0
        receipt['sources_and_inputs_unchanged']=(sha(__file__)==initial_runner and sha(out/'runner.py')==initial_runner
             and sha(out/'worker.py')==initial_worker and sha(args.chain)==initial_a and
             sha(args.mask)==initial_b and sha(args.part)==initial_c and sha(installation)==initial_installation
             and sha(out/'installation-receipt.json')==initial_installation
             and all(sha(RUNTIME/path)==value for path,value in runtime['runtime_files_sha256'].items())
             and all(str((RUNTIME/path).readlink())==value for path,value in runtime['rootfs_symlinks'].items()))
        if not receipt['sources_and_inputs_unchanged']:receipt['status']='failed_identity_changed'
        receipt['elapsed_seconds']=time.monotonic()-start
        (out/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['status']=='executed' and receipt['owned_scope_inactive'] else 1

if __name__=='__main__':sys.exit(main())
