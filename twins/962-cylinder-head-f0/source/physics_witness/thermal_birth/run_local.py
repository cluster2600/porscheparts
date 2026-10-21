"""Reproduce this exact three-level witness in an existing read-only Linux runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from assess import assess, sha
from assess_refinement import assess as assess_refinement


def reproduce(rootfs, output):
    source=Path(__file__).resolve().parent
    rootfs=Path(rootfs).resolve()
    output=Path(output).resolve()
    card=json.loads((source/'card.json').read_text())
    binary=rootfs/'opt/moose/bin/moose-opt'
    if sha(binary)!=card['native_binary_sha256']:
        raise ValueError('Runtime binary differs from the pinned distribution')
    output.mkdir(parents=True,exist_ok=False)
    levels={str(i):'[Executioner]\n  dt = '+str(dt)+'\n[]\n' for i,dt in enumerate(card['time_steps_s'])}
    frozen={'schema_version':'1.0.0','frozen_before_native_runs':True,'created_unix':time.time(),
            'classification':card['classification'],'card_sha256':sha(source/'card.json'),
            'input_sha256':{'thermal-birth.i':sha(source/'thermal-birth.i')},
            'assessor_sha256':sha(source/'assess.py'),'card':card,'time_level_inputs':levels,
            'level_input_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in levels.items()}}
    contract=output/'frozen-contract.json'
    with contract.open('x') as stream:json.dump(frozen,stream,indent=2);stream.write('\n')
    assessments=[]
    for level in range(len(levels)):
        directory=output/f'level-{level}-001'
        directory.mkdir()
        for name in ('card.json','thermal-birth.i'):shutil.copyfile(source/name,directory/name)
        shutil.copyfile(contract,directory/'frozen-contract.json')
        with (directory/'time-level.i').open('x') as stream:stream.write(levels[str(level)])
        inputs={p.name:sha(p) for p in directory.iterdir()}
        command=['bwrap','--unshare-user','--uid','0','--gid','0','--ro-bind',str(rootfs),'/',
                 '--dev','/dev','--proc','/proc','--tmpfs','/tmp','--bind',str(directory),'/tmp/work',
                 '--unshare-net','--unshare-pid','--die-with-parent','--chdir','/tmp/work']
        for key,value in {'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','OMPI_ALLOW_RUN_AS_ROOT':'1',
                          'OMPI_ALLOW_RUN_AS_ROOT_CONFIRM':'1','OMPI_MCA_btl_vader_single_copy_mechanism':'none'}.items():
            command+=['--setenv',key,value]
        command+=['/bin/bash','-c','. /environment; exec moose-opt -i thermal-birth.i time-level.i']
        cap=['systemd-run','--user','--scope','--quiet','-p','MemoryMax=2G','-p','MemorySwapMax=0',
             '-p','CPUQuota=200%','-p','TasksMax=128','-p','RuntimeMaxSec=115',
             'timeout','--signal=TERM','--kill-after=5s','100']
        print(f'Starting thermal-birth level {level}, 100-second native deadline.',flush=True)
        started=time.time();clock=time.monotonic()
        with (directory/'native.log').open('xb') as stream:
            native=subprocess.run(cap+command,stdout=stream,stderr=subprocess.STDOUT)
        receipt={'level':level,'returncode':native.returncode,'started_unix':started,
                 'wall_seconds':time.monotonic()-clock,'deadline_seconds':100,'native_argv':cap+command,
                 'network':'none','rootfs':'read_only','binary_sha256':sha(binary),
                 'binary_unchanged':sha(binary)==card['native_binary_sha256'],
                 'inputs_unchanged':all(sha(directory/name)==digest for name,digest in inputs.items()),
                 'input_sha256':inputs,
                 'artifact_sha256':{p.name:sha(p) for p in sorted(directory.iterdir()) if p.is_file()}}
        with (directory/'native-execution.json').open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
        if native.returncode:
            raise RuntimeError(f'Native level {level} failed; immutable inputs/log retained')
        result=assess(directory,contract)
        path=output/f'level-{level}-assessment.json'
        with path.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
        assessments.append(path)
        if not result['passed']:
            raise RuntimeError(f'Native level {level} rejected by independent field/energy checks')
        print(json.dumps({'level':level,'passed':result['passed'],'checks':result['checks_count']}),flush=True)
    result=assess_refinement(contract,assessments)
    with (output/'refinement-assessment.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    if not result['passed']:
        raise RuntimeError('Frozen time-refinement criteria failed')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--rootfs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=reproduce(args.rootfs,args.output)
    print(json.dumps({'passed':result['passed'],'successive_error_ratios':result['successive_error_ratios']}))
