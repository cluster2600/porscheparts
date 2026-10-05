#!/usr/bin/env python3
"""Reproduce the exact already executed D1C code/config capsule; never solve."""
import argparse,hashlib,json,shutil
from pathlib import Path


def prepare(study,output):
    frozen=json.loads((study/'parameters/D1C-executed-capsule-manifest.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    for name,record in frozen['files'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe capsule member')
        source=study/name if path.parts[0]=='source' else study/'parameters/D1C-executed-configurations'/Path(*path.parts[1:])
        if source.stat().st_size!=record['bytes'] or hashlib.sha256(source.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Executed capsule source identity differs')
        dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    shutil.copyfile(study/'parameters/D1C-executed-capsule-manifest.json',output/'capsule-manifest.json')
    print('Executed single-case capsule reproduced; launching requires a new coordinated resource window')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('study',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();prepare(a.study,a.output)
