"""One native exact CSG tree: intersection(difference(chain,part),mask)."""
import argparse,hashlib,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path

ROOT=Path('/home/lolman/carrier-pymesh-exact-20261016')
IMAGE='sha256:ecf699d33793efe612b66c36b2a7d3954085af55999cc3f631748fcf1671eb4e'
ARCHIVE_SHA='536dc79c0bddeeffe2d86b85441179774cc515ce1d8f130eb62c06c1f72eba56'
NATIVE_REL='usr/local/lib/python3.6/site-packages/pymesh/lib/PyMesh.cpython-36m-x86_64-linux-gnu.so'
NATIVE_SHA='17cd2bb3a74539b1f913501f49a362f65cb395a62ab65bc5a6e8815ccc585d8a'
WORKER=r'''
"""One in-memory PyMesh CSGTree; mesh conversion occurs only at the root."""
import hashlib,json,time,inspect
from pathlib import Path
import numpy as np,pymesh,PyMesh
out=Path('/tmp/output')
inputs={'chain':Path('/tmp/input/a.npz'),'mask':Path('/tmp/input-b/b.npz'),'part':Path('/tmp/input-c/c.npz')}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
leaves=[]
for name,path in inputs.items():
    data=np.load(str(path))
    leaves.append(pymesh.form_mesh(data['vertices'],data['faces']))
tree_definition={'intersection':[{'difference':[{'mesh':leaves[0]},{'mesh':leaves[2]}]},{'mesh':leaves[1]}]}
start=time.monotonic();tree=pymesh.CSGTree(tree_definition)
# This is the first/only tree.mesh, tree.vertices or get_vertices call.
result=tree.mesh
arrays={'vertices':result.vertices,'faces':result.faces}
for name in ['source_face','source']:
    assert result.has_attribute(name);arrays[name]=result.get_attribute(name)
np.savez_compressed(str(out/'result.npz'),**arrays)
report={'status':'executed','algorithm':'intersection(difference(chain,part),mask) in one native CSGTree',
        'seconds':time.monotonic()-start,'volume_mm3':result.volume,'leaf_role_order':['chain','part','mask'],'leaf_face_counts':[leaves[i].num_faces for i in [0,2,1]],
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
    args=p.parse_args();assert all(p.is_file() for p in [args.chain,args.mask,args.part]);assert not args.output.exists()
    out=args.output.resolve();assert out.parent==ROOT/'jobs','Fresh direct child of owned jobs/ required'
    sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
    assert sha(ROOT/'rootfs'/NATIVE_REL)==NATIVE_SHA,'Pinned native runtime mismatch'
    out.mkdir();initial_runner=sha(__file__);initial_a=sha(args.chain);initial_b=sha(args.mask);initial_c=sha(args.part)
    (out/'runner.py').write_bytes(Path(__file__).read_bytes());(out/'worker.py').write_text(WORKER)
    initial_worker=sha(out/'worker.py');unit='carrier-csg-v4-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,
             '-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610',
             '/usr/bin/timeout','--kill-after=10s','600','/usr/bin/bwrap',
             '--ro-bind',str(ROOT/'rootfs'),'/', '--unshare-net','--unshare-pid','--unshare-ipc',
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
             'wrapper_sha256':initial_runner,'worker_sha256':initial_worker,'timeout_seconds':600}
    (out/'execution-plan.json').write_text(json.dumps(receipt,indent=2)+'\n')
    start=time.monotonic();process=None
    try:
        with (out/'stdout.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            code=process.wait(timeout=630)
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
             sha(args.mask)==initial_b and sha(args.part)==initial_c)
        if not receipt['sources_and_inputs_unchanged']:receipt['status']='failed_identity_changed'
        receipt['elapsed_seconds']=time.monotonic()-start
        (out/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['status']=='executed' and receipt['owned_scope_inactive'] else 1

if __name__=='__main__':sys.exit(main())
