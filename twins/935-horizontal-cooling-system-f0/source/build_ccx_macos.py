#!/usr/bin/env python3
"""Isolated CCX 2.23 build with its author's official large-deck SPOOLES fix."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

ARCHIVES={
    'ccx_2.23.src.tar.bz2':'9c88385c10fb04f5dc6c4e98027a51bebdd8aee3920e05190d6c1dd08357d6e7',
    'spooles.2.2.tgz':'a84559a0e987a1e423055ef4fdf3035d55b65bbe4bf915efaa1a35bef7f8c5dd',
    'ccx_2.23.SPOOLEScorrection.tar.bz2':'15528f09312dc7605c0600358f5e6de12945449f249dfcfca7417eed6c220b93'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def change(path,old,new,count=1):
    text=path.read_text()
    if text.count(old)!=count:raise ValueError('Expected upstream build text differs: '+path.name)
    path.with_name(path.name+'.original').write_text(text);path.write_text(text.replace(old,new))


def build(archives,output):
    archives,output=Path(archives),Path(output)
    if platform.system()!='Darwin' or output.exists() or not output.parent.is_dir():raise ValueError('Fresh macOS build required')
    for name,value in ARCHIVES.items():
        if sha(archives/name)!=value:raise ValueError('Pinned upstream archive differs: '+name)
    output.mkdir(mode=0o700)
    with tarfile.open(archives/'ccx_2.23.src.tar.bz2') as tar:tar.extractall(output,filter='data')
    base=output/'CalculiX';spooles=base/'spooles';spooles.mkdir()
    with tarfile.open(archives/'spooles.2.2.tgz') as tar:tar.extractall(spooles,filter='data')
    change(spooles/'Make.inc','/usr/lang-4.0/bin/cc','/usr/bin/clang')
    change(spooles/'Tree/src/makeGlobalLib','drawTree.c','tree.c')
    change(spooles/'ETree/src/transform.c','IVinit(nfront, NULL)','IVinit(nfront, 0)',count=3)
    target=spooles/'I2Ohash/src/util.c';shutil.copyfile(target,target.with_name('util.c.unpatched'))
    with tarfile.open(archives/'ccx_2.23.SPOOLEScorrection.tar.bz2') as tar:
        source=tar.extractfile('./CalculiX/ccx_2.23/SPOOLES.2.2/I2Ohash/src/util.c').read()
    target.write_bytes(source)
    ccx=base/'ccx_2.23/src'
    change(ccx/'Makefile','ccx_2.23: $(OCCXMAIN) ccx_2.23.a  $(LIBS)','ccx_2.23: $(OCCXMAIN) ccx_2.23.a')
    change(ccx/'readnewmesh.c','return NULL;\n\n}','return;\n\n}')
    libs=subprocess.check_output(['pkg-config','--libs','arpack'],text=True).strip()+' -framework Accelerate'
    commands=[['make','-C',str(spooles),'lib'],['make','-C',str(spooles/'MT/src'),'makeLib'],
              ['make','-j8','-C',str(ccx),'ccx_2.23','CC=/usr/bin/clang','FC=/opt/homebrew/bin/gfortran',
               'CFLAGS=-O2 -I../../spooles -DARCH=Linux -DSPOOLES -DARPACK -DMATRIXSTORAGE -DUSE_MT=1',
               'FFLAGS=-O2 -fopenmp -cpp','LIBS=../../spooles/spooles.a '+libs]]
    report=dict(status='building',archives_sha256=ARCHIVES,source_sha256=sha(__file__),
                official_fix_url='https://www.dhondt.de/ccx_2.23.SPOOLEScorrection.tar.bz2',
                unpatched_util_sha256=sha(target.with_name('util.c.unpatched')),patched_util_sha256=sha(target),commands=commands,
                architecture=platform.machine(),qualified=False,manufacturing_authorized=False)
    (output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    for i,command in enumerate(commands):
        with (output/f'build-{i}.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    exe=ccx/'ccx_2.23';report.update(status='built_not_qualified',binary_sha256=sha(exe),binary_relative_path=str(exe.relative_to(output)))
    (output/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archives',type=Path);p.add_argument('new_output',type=Path)
    a=p.parse_args();build(a.archives,a.new_output)
