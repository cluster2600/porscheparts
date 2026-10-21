"""Run one immutable, bounded MOOSE command in the pinned rootless public image."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
DIGEST='sha256:47fc6c5bff5e86869e7c467f999e9585ece13af9ffd1f580fef5369728a93452'
def run(rootfs,directory,label,args,deadline=720):
    ROOTFS=Path(rootfs).resolve()
    source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    binary=ROOTFS/"opt/moose/bin/moose-opt"
    binary_hash=hashlib.sha256(binary.read_bytes()).hexdigest()
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    image=json.loads((ROOTFS.parent/'receipt.json').read_text());assert image['image']=='idaholab/moose@'+DIGEST and image['completed']
    log=directory/(label+'.log');receipt=directory/(label+'-execution.json');assert not log.exists() and not receipt.exists()
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.i')}
    command=['bwrap','--unshare-user','--uid','0','--gid','0','--ro-bind',str(ROOTFS),'/','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--bind',str(directory),'/tmp/work','--unshare-net','--unshare-pid','--die-with-parent','--chdir','/tmp/work']
    for key,value in {'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','OMPI_ALLOW_RUN_AS_ROOT':'1','OMPI_ALLOW_RUN_AS_ROOT_CONFIRM':'1','OMPI_MCA_btl_vader_single_copy_mechanism':'none'}.items():command+=['--setenv',key,value]
    command+=['/bin/bash','-c','. /environment; exec moose-opt "$@"','moose-opt']+args
    cap=['systemd-run','--user','--scope','--quiet','-p','MemoryMax=8G','-p','MemorySwapMax=0','-p','CPUQuota=200%','-p','TasksMax=256','-p','RuntimeMaxSec='+str(deadline+15),'timeout','--kill-after=10s',str(deadline)]
    t=time.monotonic()
    with log.open('xb') as out:r=subprocess.run(cap+command,stdout=out,stderr=subprocess.STDOUT)
    result={'returncode':r.returncode,'wall_seconds':time.monotonic()-t,'deadline_seconds':deadline,'timed_out':r.returncode in(124,137),'image_digest':DIGEST,'memory_max':'8G','memory_swap_max':0,'cpu_quota':'200%','network':'none','arguments':args,'input_i_sha256':before,'input_i_unchanged':before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.i')},'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'runner_sha256':source_hash,'binary_sha256':binary_hash,'source_and_binary_unchanged':source_hash==hashlib.sha256(Path(__file__).read_bytes()).hexdigest() and binary_hash==hashlib.sha256(binary.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rootfs',type=Path);p.add_argument('directory',type=Path);p.add_argument('label');p.add_argument('--deadline',type=int,default=720);p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args();args=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments;r=run(a.rootfs,a.directory,a.label,args,a.deadline);raise SystemExit(r['returncode'])
