"""Private isolated three-line SPOOLES object replacement; no FEA or installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'m64-g13/native-ccx'
OUTPUT=HERE/'native-ccx-hashfix-v1'
INVENTORY_SHA='82a729772dc14b1c5e80e31fc4038a95448a68ad1a19941f4684e7d75412923c'
PINS={'spooles/spooles.a':'e77983426bea09a00ec5f719f1888dfb9ee4a691717a1e9c9c7f17c4b4b30a65',
 'spooles/I2Ohash/src/util.c':'1121b2d3650fc103f6009188db5fe31ef7f579ab12682d306082a99469ed3a01',
 'arpack-build/libarpack.a':'2827f5659e3ea1418af7e83726ebfb54c49567d6543f3ed38b5d4e08a6717d4e',
 'CalculiX/ccx_2.21/src/ccx_2.21.o':'db226575d29a32a4b28fd83ca6c81dedba97e0a52626e51b2956be2a55ec84ed',
 'CalculiX/ccx_2.21/src/ccx_2.21.a':'a460acfb8812ade84157da6be73e4a9ab38963df65fd0c897c8daeb7f80140fd',
 'CalculiX/ccx_2.21/src/ccx_2.21':'9cd22c961a0ead334739802e369345745746aafd51a01cff5d2309274cf1548a'}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def publish(path,data):
    with path.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def originals():
    if sha(OLD/'build-inventory.json')!=INVENTORY_SHA:raise ValueError('old inventory changed')
    value=json.loads((OLD/'build-inventory.json').read_text())
    for name,digest in PINS.items():
        if sha(OLD/name)!=digest:raise ValueError('old object/source changed: '+name)
    for name,row in value['dynamic_libraries'].items():
        if str(Path(name).resolve())!=row['resolved_path'] or sha(name)!=row['sha256']:
            raise ValueError('dynamic library changed: '+name)
    return value


def members(path):
    names=subprocess.check_output(['/usr/bin/ar','-t',str(path)],text=True,timeout=10).splitlines()
    if len(names)!=len(set(names)):raise ValueError('duplicate archive members')
    return {n:hashlib.sha256(subprocess.check_output(['/usr/bin/ar','-p',str(path),n],timeout=10)).hexdigest() for n in names}


def command(argv,name,records):
    start=time.monotonic();code=None
    with (OUTPUT/(name+'.log')).open('x') as log:
        process=subprocess.Popen(argv,cwd=OUTPUT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=process.wait(timeout=120)
        finally:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait()
            row=dict(argv=argv,returncode=process.returncode,wall_seconds=time.monotonic()-start)
            records.append(row);publish(OUTPUT/(name+'.json'),row)
    if code!=0:raise ValueError('build command failed: '+name)


def run(args):
    original=originals();patch=HERE/'spooles-hash-fix-v1/util-corrected.c'
    if sha(patch)!=args.patch_sha256 or sha(args.witness)!=args.witness_sha256:
        raise ValueError('reviewed patch/witness changed')
    witness=json.loads(args.witness.read_text())
    if (witness.get('unit_fix_qualified') is not True
            or witness.get('original_sources_archive_and_CCX_unchanged') is not True
            or witness.get('corrected_util_sha256')!=args.patch_sha256
            or sha(args.witness.parent/witness['primary_receipt'])!=witness['primary_receipt_sha256']):
        raise ValueError('passed bound isolated overflow witness required')
    text=(OLD/'spooles/I2Ohash/src/util.c').read_text()
    old='loc  = (loc1*loc2) % hashtable->nlist ;'
    new='loc  = (int) (((long long) loc1*loc2) % hashtable->nlist) ;'
    if text.count(old)!=3 or patch.read_text()!=text.replace(old,new):
        raise ValueError('only the reviewed three integer products may change')
    OUTPUT.mkdir(exist_ok=False)
    shutil.copyfile(__file__,OUTPUT/Path(__file__).name)
    report=dict(classification='native_arm64_CCX221_isolated_SPOOLES_hashfix_build',complete=False,error=None,
        source_sha256=sha(__file__),original_inventory_sha256=INVENTORY_SHA,original_objects_sha256=PINS,
        patch_sha256=args.patch_sha256,witness_sha256=args.witness_sha256,commands=[],FEA_executed=False,
        manufacturing_authorized=False,engine_start_authorized=False)
    try:
        shutil.copytree(OLD/'spooles',OUTPUT/'spooles')
        shutil.copyfile(patch,OUTPUT/'spooles/I2Ohash/src/util.c')
        for name in ['arpack-build/libarpack.a','CalculiX/ccx_2.21/src/ccx_2.21.o',
                'CalculiX/ccx_2.21/src/ccx_2.21.a','CalculiX/ccx_2.21/src/Makefile',
                'CalculiX/ccx_2.21/src/CalculiX.h','native_smoke.py','bounded.py','calculix-ccx-3f7bd193.rb',
                'ccx_2.21.src.tar.bz2','spooles.2.2.tgz','arpack-ng-3.9.1.tar.gz']:
            target=OUTPUT/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,target)
        before=members(OLD/'spooles/spooles.a')
        command(['/usr/bin/clang','-O','-c','spooles/I2Ohash/src/util.c','-o','I2Ohash_util.o'],'compile',report['commands'])
        command(['/usr/bin/ar','-r','spooles/spooles.a','I2Ohash_util.o'],'archive',report['commands'])
        after=members(OUTPUT/'spooles/spooles.a')
        changed=[n for n in before if before[n]!=after.get(n)]
        if list(before)!=list(after) or changed!=['I2Ohash_util.o']:
            raise ValueError('archive changed outside the single approved member')
        report.update(archive_members_before=before,archive_members_after=after,changed_members=changed)
        command(['/opt/homebrew/opt/gcc/bin/gfortran','-Wall','-O2','-o','CalculiX/ccx_2.21/src/ccx_2.21',
            'CalculiX/ccx_2.21/src/ccx_2.21.o','CalculiX/ccx_2.21/src/ccx_2.21.a','spooles/spooles.a',
            'arpack-build/libarpack.a','/opt/homebrew/opt/openblas/lib/libopenblas.dylib','-fopenmp'],
            'link',report['commands'])
        binary=OUTPUT/'CalculiX/ccx_2.21/src/ccx_2.21'
        linked=subprocess.check_output(['/usr/bin/otool','-L',str(binary)],text=True,timeout=10)
        if linked.splitlines()[1:]!=original['metadata']['dynamic_linkage'].splitlines()[1:]:
            raise ValueError('dynamic linkage differs from qualified native runtime')
        originals()
        inventory=dict(classification=report['classification'],binary=dict(path=str(binary),sha256=sha(binary)),
            dynamic_libraries=original['dynamic_libraries'],parent_inventory_sha256=INVENTORY_SHA,
            dynamic_linkage=linked,source_sha256=report['source_sha256'],patch_sha256=args.patch_sha256,
            witness_sha256=args.witness_sha256,archive_sha256=sha(OUTPUT/'spooles/spooles.a'),
            no_CCX_recompile=True,no_ARPACK_rebuild=True,no_system_installation=True)
        publish(OUTPUT/'build-inventory.json',inventory)
        report.update(complete=True,binary_sha256=sha(binary),build_inventory_sha256=sha(OUTPUT/'build-inventory.json'),
            originals_verified_after=True)
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:publish(OUTPUT/'build.json',report)
    print(json.dumps({k:report[k] for k in ('complete','error')}))
    return 0 if report['complete'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch-sha256',required=True);parser.add_argument('--witness',required=True,type=Path)
    parser.add_argument('--witness-sha256',required=True)
    raise SystemExit(run(parser.parse_args()))
