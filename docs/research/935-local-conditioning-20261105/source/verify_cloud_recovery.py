"""Verify every recovered file and bind omitted duplicate inputs to the Mac originals."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("archive","collection-receipt","inputs-archive","candidate","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();receipt=json.loads(a.collection_receipt.read_text())
    assert receipt['stage']=='complete' and sha(a.archive)==receipt['archive_sha256']
    a.output.mkdir(mode=0o700,exist_ok=False)
    with tarfile.open(a.archive) as source:
        members=source.getmembers()
        assert all(x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in members)
        assert len({x.name for x in members})==len(members),"Duplicate archive path refused"
        assert sum(x.size for x in members)<shutil.disk_usage(a.output).free-1024**3
        source.extractall(a.output,filter='data')
    manifest=json.loads((a.output/"recovery-manifest.json").read_text())
    declared={row['path'] for row in manifest['files']}
    actual={str(path.relative_to(a.output)) for path in a.output.rglob('*') if path.is_file()}
    assert actual==declared|{'recovery-manifest.json'}
    for row in manifest['files']:
        f=a.output/row['path'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
    originals={'inputs.tar':a.inputs_archive,'candidate.npz':a.candidate}
    assert {row['path'] for row in manifest['omitted_duplicate_inputs']}==set(originals)
    for row in manifest['omitted_duplicate_inputs']:
        f=originals[row['path']];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
    inputs=json.loads((a.output/'input-manifest.json').read_text())
    for row in inputs['files']:
        f=originals.get(row['path'],a.output/row['path'])
        assert sha(f)==row['sha256']
    worker_manifest=json.loads((a.output/'result-manifest.json').read_text())
    for row in worker_manifest['files']:
        f=originals.get(row['path'],a.output/row['path'])
        assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
    assert manifest['worker_terminal']==json.loads((a.output/'terminal-state.json').read_text())
    result={'archive_sha256':sha(a.archive),'source_sha256':sha(Path(__file__)),
            'worker_manifest_entries_verified':len(worker_manifest['files']),
            'recovered_files_verified':len(manifest['files']),'all_recovered_bytes_match':True,
            'all_original_input_hashes_match':True,'omitted_inputs_verified_on_mac':len(originals),
            'head_mesh_recovered':(a.output/'head/solid.npz').exists(),
            'worker_terminal':manifest['worker_terminal']['terminal'],
            'physics_admitted':False,'manufacturing_qualified':False}
    with a.output.with_name(a.output.name+'-verification.json').open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
