"""Verify and restore this fixed native64 evidence capsule; stdlib only."""
import argparse
import gzip
import hashlib
import json
import lzma
from pathlib import Path, PurePosixPath
import time

HERE=Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def relative(value):
    p=PurePosixPath(value)
    if not value or not p.parts or p.is_absolute()or any(v in ('','.','..')for v in p.parts)or p.as_posix()!=value:
        raise ValueError('Only exact relative capsule paths are allowed')
    return Path(*p.parts)


def manifest(expected):
    raw=(HERE/'manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Reviewed capsule manifest differs')
    report=json.loads(raw)
    if report['schema']!='wholepart-native64-portable-capsule-1':raise ValueError('Different capsule schema')
    if any(sha(HERE/relative(p))!=h for p,h in report['utility_sha256'].items()):raise ValueError('Capsule utility changed')
    seen=set()
    for row in report['payloads']:
        target=relative(row['restored']);source=relative(row['stored'])
        suffix={'none':'','gzip-mtime0':'.gz','xz-no-timestamp':'.xz'}.get(row['compression'])
        expected_stored='payloads/'+target.as_posix()+(suffix or '')
        if (suffix is None or source.as_posix()!=expected_stored or
                target.as_posix()in seen or (HERE/source).is_symlink()or sha(HERE/source)!=row['stored_sha256']or
                (HERE/source).stat().st_size!=row['stored_bytes']):raise ValueError('Capsule payload identity/path differs')
        seen.add(target.as_posix())
    return report


def transfer(row,destination=None):
    source=HERE/relative(row['stored']);opener={'gzip-mtime0':gzip.open,'xz-no-timestamp':lzma.open,'none':open}[row['compression']]
    digest=hashlib.sha256();size=0
    out=destination.open('xb')if destination is not None else None
    try:
        with opener(source,'rb')as stream:
            while data:=stream.read(1024*1024):
                size+=len(data)
                if size>row['original_bytes']:raise ValueError('Expanded payload exceeds its exact original size')
                digest.update(data)
                if out is not None:out.write(data)
    finally:
        if out is not None:out.close()
    if size!=row['original_bytes']or digest.hexdigest()!=row['original_sha256']:
        raise ValueError('Decompressed original stream differs')


def verify(expected):
    report=manifest(expected)
    for row in report['payloads']:transfer(row)
    return report


def restore(output,expected):
    started=time.monotonic();output=Path(output).absolute()
    if output.exists()or output.is_symlink()or any(p.is_symlink()for p in output.parents):
        raise FileExistsError('A fresh restoration root without symlinks is required')
    report=verify(expected);output=output.resolve();output.mkdir(exist_ok=False)
    for row in report['payloads']:
        target=output/relative(row['restored']);target.parent.mkdir(parents=True,exist_ok=True);transfer(row,target)
    verify(expected)
    receipt=dict(status='actual_native_outputs_restored_byte_identical_no_new_solver_run',capsule_manifest_sha256=expected,
        files=len(report['payloads']),original_bytes=sum(r['original_bytes']for r in report['payloads']),
        all_decompressed_sha256_verified=True,new_solver_run=False,global_admission=False,seconds=time.monotonic()-started)
    with(output/'restoration.json').open('x')as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','restore']);p.add_argument('output',nargs='?',type=Path)
    p.add_argument('--manifest-sha256',required=True);a=p.parse_args()
    if(a.mode=='restore')!=(a.output is not None):p.error('Only restore requires one fresh output root')
    r=restore(a.output,a.manifest_sha256)if a.mode=='restore'else verify(a.manifest_sha256)
    print(json.dumps(dict(status=r['status'],files=r.get('files',len(r.get('payloads',[]))),new_solver_run=False)))
